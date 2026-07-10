import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today
from frappe.utils.file_manager import save_file


class TestLeaseDocument(IntegrationTestCase):
    def setUp(self):
        department = frappe.get_doc(
            {"doctype": "Lease Department", "department_name": frappe.generate_hash(length=10)}
        ).insert()
        property_doc = frappe.get_doc(
            {
                "doctype": "Property",
                "property_name": f"Document Property {frappe.generate_hash(length=8)}",
                "property_type": "Office",
            }
        ).insert()
        landlord = frappe.get_doc(
            {
                "doctype": "Landlord",
                "legal_name": f"Document Landlord {frappe.generate_hash(length=8)}",
            }
        ).insert()
        self.lease = frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_title": "Document Test Lease",
                "property": property_doc.name,
                "landlord": landlord.name,
                "lease_type": "Commercial",
                "responsible_department": department.name,
                "responsible_officer": "Administrator",
                "start_date": add_days(today(), -30),
                "end_date": add_days(today(), 365),
                "notice_period_days": 90,
                "currency": "NGN",
                "rent_basis": "Monthly",
                "monthly_rent": 100000,
                "payment_frequency": "Monthly",
                "lease_status": "Active",
            }
        ).insert()

    def make_file(self, *, is_private, extension="pdf"):
        content = f"test-{frappe.generate_hash(length=12)}".encode()
        return save_file(
            f"lease-document-{frappe.generate_hash(length=8)}.{extension}",
            content,
            "Lease",
            self.lease.name,
            is_private=is_private,
        )

    def make_document(self, file_url, **overrides):
        values = {
            "doctype": "Lease Document",
            "lease": self.lease.name,
            "title": "Signed Lease Agreement",
            "category": "Signed Agreement",
            "file": file_url,
            "document_date": today(),
            "effective_date": today(),
        }
        values.update(overrides)
        return frappe.get_doc(values)

    def test_accepts_private_file_and_reattaches_to_metadata(self):
        file_doc = self.make_file(is_private=1)
        document = self.make_document(file_doc.file_url).insert()

        attachment = frappe.db.get_value(
            "File", file_doc.name, ["attached_to_doctype", "attached_to_name"], as_dict=True
        )
        self.assertEqual(attachment.attached_to_doctype, "Lease Document")
        self.assertEqual(attachment.attached_to_name, document.name)

    def test_rejects_public_file(self):
        file_doc = self.make_file(is_private=0)

        self.assertRaises(frappe.ValidationError, self.make_document(file_doc.file_url).insert)

    def test_rejects_disallowed_extension(self):
        file_doc = self.make_file(is_private=1, extension="exe")

        self.assertRaises(frappe.ValidationError, self.make_document(file_doc.file_url).insert)

    def test_rejects_invalid_effective_period(self):
        file_doc = self.make_file(is_private=1)
        document = self.make_document(
            file_doc.file_url,
            effective_date=add_days(today(), 10),
            expiry_date=today(),
        )

        self.assertRaises(frappe.ValidationError, document.insert)

