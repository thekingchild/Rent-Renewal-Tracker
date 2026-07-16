import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today
from frappe.utils.file_manager import save_file

from rent_renewal_tracker.patches.v0_6.initialize_required_settings_and_document_families import (
    execute as run_v0_6_upgrade_patch,
)
from rent_renewal_tracker.patches.v0_8.enable_lease_document_submission_compatibility import (
    execute as run_v0_8_upgrade_patch,
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
        file_doc = save_file(
            f"lease-document-{frappe.generate_hash(length=8)}.txt",
            f"test-{frappe.generate_hash(length=12)}".encode(),
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

    def test_rejects_public_file_and_disallowed_extension(self):
        public_file = self.make_file(is_private=0)
        self.assertRaises(frappe.ValidationError, self.make_document(public_file.file_url).insert)

        executable = self.make_file(is_private=1, extension="exe")
        self.assertRaises(frappe.ValidationError, self.make_document(executable.file_url).insert)

    def test_rejects_invalid_effective_period(self):
        document = self.make_document(
            self.make_file(is_private=1).file_url,
            effective_date=add_days(today(), 10),
            expiry_date=today(),
        )
        self.assertRaises(frappe.ValidationError, document.insert)

    def test_draft_becomes_current_only_on_submit(self):
        document = self.make_document(
            self.make_file(is_private=1).file_url,
            effective_date=add_days(today(), -30),
            expiry_date=add_days(today(), -1),
        ).insert()

        self.assertEqual(document.docstatus, 0)
        self.assertEqual(document.document_status, "Draft")
        self.assertEqual(document.revision_status, "Draft")
        document.submit()

        self.assertEqual(document.docstatus, 1)
        self.assertEqual(document.document_status, "Expired")
        self.assertEqual(document.revision_status, "Current")
        self.assertEqual(document.document_family_id, document.name)
        self.assertEqual(document.revision_number, 1)

    def test_formal_document_requires_date_at_submission(self):
        document = self.make_document(
            self.make_file(is_private=1).file_url, document_date=None
        ).insert()
        self.assertEqual(document.document_status, "Draft")
        self.assertRaises(frappe.ValidationError, document.submit)

    def test_draft_revision_does_not_supersede_until_submit(self):
        original = self.make_document(self.make_file(is_private=1).file_url).insert().submit()
        revision = self.make_document(
            self.make_file(is_private=1).file_url,
            previous_revision=original.name,
            revision_reason="Executed terms replaced the earlier copy.",
        ).insert()

        original.reload()
        self.assertEqual(original.revision_status, "Current")
        self.assertEqual(revision.revision_status, "Draft")
        self.assertEqual(revision.revision_number, 2)
        revision.submit()
        original.reload()

        self.assertEqual(revision.revision_status, "Current")
        self.assertEqual(original.revision_status, "Superseded")
        self.assertEqual(original.document_status, "Superseded")

    def test_cancellation_requires_reason_and_restores_previous_revision(self):
        original = self.make_document(self.make_file(is_private=1).file_url).insert().submit()
        revision = self.make_document(
            self.make_file(is_private=1).file_url,
            previous_revision=original.name,
            revision_reason="Replace executed evidence.",
        ).insert().submit()

        self.assertRaises(frappe.ValidationError, revision.cancel)
        revision.reload()
        revision.cancellation_reason = "The uploaded execution copy was invalid."
        revision.save()
        revision.cancel()
        original.reload()

        self.assertEqual(revision.docstatus, 2)
        self.assertEqual(revision.revision_status, "Cancelled")
        self.assertEqual(revision.document_status, "Cancelled")
        self.assertEqual(original.revision_status, "Current")

    def test_superseded_revision_cannot_be_cancelled(self):
        original = self.make_document(self.make_file(is_private=1).file_url).insert().submit()
        self.make_document(
            self.make_file(is_private=1).file_url,
            previous_revision=original.name,
            revision_reason="New executed evidence.",
        ).insert().submit()
        original.reload()
        original.cancellation_reason = "Should not be permitted."
        original.save()
        self.assertRaises(frappe.ValidationError, original.cancel)

    def test_cancelled_document_can_be_amended_and_resubmitted(self):
        original = self.make_document(self.make_file(is_private=1).file_url).insert().submit()
        original.cancellation_reason = "Metadata requires correction."
        original.save()
        original.cancel()

        amendment = frappe.copy_doc(original)
        amendment.docstatus = 0
        amendment.amended_from = original.name
        amendment.revision_reason = "Corrected metadata after cancellation."
        amendment.title = "Corrected Signed Lease Agreement"
        amendment.insert()
        self.assertFalse(amendment.cancellation_reason)
        amendment.submit()

        self.assertEqual(amendment.amended_from, original.name)
        self.assertEqual(amendment.document_family_id, original.document_family_id)
        self.assertEqual(amendment.revision_number, 2)
        self.assertEqual(amendment.revision_status, "Current")

    def test_draft_file_can_change_but_submitted_file_is_immutable(self):
        document = self.make_document(self.make_file(is_private=1).file_url).insert()
        replacement = self.make_file(is_private=1)
        document.file = replacement.file_url
        document.save()
        document.submit()

        document.file = self.make_file(is_private=1).file_url
        with self.assertRaises((frappe.ValidationError, frappe.UpdateAfterSubmitError)):
            document.save()

    def test_only_true_drafts_can_be_deleted(self):
        draft = self.make_document(self.make_file(is_private=1).file_url).insert()
        draft.delete()
        self.assertFalse(frappe.db.exists("Lease Document", draft.name))

        submitted = self.make_document(self.make_file(is_private=1).file_url).insert().submit()
        with self.assertRaises(frappe.ValidationError):
            submitted.delete()

    def test_upgrade_patch_repairs_and_marks_legacy_metadata(self):
        document = self.make_document(self.make_file(is_private=1).file_url).insert()
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
        run_v0_8_upgrade_patch()
        run_v0_8_upgrade_patch()
        document.reload()

        self.assertEqual(document.document_family_id, document.name)
        self.assertEqual(document.revision_number, 1)
        self.assertEqual(document.revision_status, "Current")
        self.assertEqual(document.confidentiality, "Confidential")
        self.assertTrue(document.legacy_unsubmitted)

    def test_legacy_current_record_can_be_submitted_without_state_change(self):
        document = self.make_document(self.make_file(is_private=1).file_url).insert()
        frappe.db.set_value(
            "Lease Document",
            document.name,
            {"revision_status": "Current", "document_status": "No Expiry Date", "legacy_unsubmitted": 1},
            update_modified=False,
        )
        document.reload()
        document.submit()

        self.assertEqual(document.docstatus, 1)
        self.assertEqual(document.revision_status, "Current")
        self.assertFalse(document.legacy_unsubmitted)
