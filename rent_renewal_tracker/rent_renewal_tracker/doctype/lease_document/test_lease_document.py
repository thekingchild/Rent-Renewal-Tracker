import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today
from frappe.utils.file_manager import save_file

from rent_renewal_tracker.patches.v0_6.initialize_required_settings_and_document_families import (
    execute as run_v0_6_upgrade_patch,
)


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

    def make_file(self, *, is_private, extension="txt"):
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

    def test_accepts_file_uploaded_against_unsaved_document(self):
        content = f"test-{frappe.generate_hash(length=12)}".encode()
        file_doc = save_file(
            f"lease-document-{frappe.generate_hash(length=8)}.txt",
            content,
            "Lease Document",
            f"new-lease-document-{frappe.generate_hash(length=8)}",
            is_private=1,
        )

        document = self.make_document(file_doc.file_url).insert()

        attachment = frappe.db.get_value(
            "File", file_doc.name, ["attached_to_doctype", "attached_to_name"], as_dict=True
        )
        self.assertEqual(attachment.attached_to_doctype, "Lease Document")
        self.assertEqual(attachment.attached_to_name, document.name)

    def test_reuses_permitted_file_without_moving_original_attachment(self):
        file_doc = self.make_file(is_private=1)
        original = self.make_document(file_doc.file_url).insert()

        reused = self.make_document(file_doc.file_url, title="Agreement Copy").insert()

        attachment = frappe.db.get_value(
            "File", file_doc.name, ["attached_to_doctype", "attached_to_name"], as_dict=True
        )
        self.assertNotEqual(reused.name, original.name)
        self.assertEqual(attachment.attached_to_doctype, "Lease Document")
        self.assertEqual(attachment.attached_to_name, original.name)

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

    def test_derives_expiry_attention_status(self):
        file_doc = self.make_file(is_private=1)
        document = self.make_document(
            file_doc.file_url,
            effective_date=add_days(today(), -30),
            expiry_date=add_days(today(), -1),
        ).insert()

        self.assertEqual(document.document_status, "Expired")
        self.assertEqual(document.document_family_id, document.name)
        self.assertEqual(document.revision_number, 1)
        self.assertEqual(document.revision_status, "Current")

    def test_new_revision_supersedes_previous_document(self):
        original_file = self.make_file(is_private=1)
        original = self.make_document(
            original_file.file_url,
            effective_date=add_days(today(), -30),
            expiry_date=add_days(today(), 30),
        ).insert()
        revision_file = self.make_file(is_private=1)
        revision = self.make_document(
            revision_file.file_url,
            previous_revision=original.name,
            revision_reason="Executed terms replaced the earlier copy.",
        ).insert()

        original.reload()
        self.assertEqual(revision.revision_number, 2)
        self.assertEqual(revision.document_family_id, original.document_family_id)
        self.assertEqual(original.document_family_id, original.name)
        self.assertEqual(original.revision_status, "Superseded")
        self.assertEqual(original.document_status, "Superseded")
        self.assertFalse(original.days_to_document_expiry)

        rejected_file = self.make_file(is_private=1)
        rejected_revision = self.make_document(
            rejected_file.file_url,
            previous_revision=original.name,
            revision_reason="Attempted branch from a superseded revision.",
        )

        with self.assertRaises(frappe.ValidationError):
            rejected_revision.insert()

    def test_upgrade_patch_repairs_revision_and_confidentiality_metadata(self):
        file_doc = self.make_file(is_private=1)
        document = self.make_document(file_doc.file_url).insert()
        frappe.db.set_value(
            "Lease Document",
            document.name,
            {
                "document_family_id": "",
                "revision_number": 0,
                "revision_status": "",
                "confidentiality": "",
            },
            update_modified=False,
        )

        run_v0_6_upgrade_patch()
        document.reload()

        self.assertEqual(document.document_family_id, document.name)
        self.assertEqual(document.revision_number, 1)
        self.assertEqual(document.revision_status, "Current")
        self.assertEqual(document.confidentiality, "Confidential")

    def test_existing_file_cannot_be_replaced_in_place(self):
        original_file = self.make_file(is_private=1)
        document = self.make_document(original_file.file_url).insert()
        replacement = self.make_file(is_private=1)
        document.file = replacement.file_url

        self.assertRaises(frappe.ValidationError, document.save)
