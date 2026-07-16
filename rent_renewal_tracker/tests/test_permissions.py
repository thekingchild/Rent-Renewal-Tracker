import frappe
from frappe.handler import check_write_permission
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today
from frappe.utils.file_manager import save_file

from rent_renewal_tracker.permissions import can_access_lease, can_access_lease_doc


class TestLeasePermissions(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        super().setUp()
        self.department = frappe.get_doc(
            {
                "doctype": "Lease Department",
                "department_name": frappe.generate_hash(length=10),
            }
        ).insert()
        self.property_doc = frappe.get_doc(
            {
                "doctype": "Property",
                "property_name": frappe.generate_hash(length=10),
                "property_type": "Office",
            }
        ).insert()
        self.landlord = frappe.get_doc(
            {
                "doctype": "Landlord",
                "legal_name": frappe.generate_hash(length=10),
            }
        ).insert()
        self.user = f"lease-user-{frappe.generate_hash(length=8)}@example.com"
        frappe.get_doc(
            {
                "doctype": "User",
                "email": self.user,
                "first_name": "Lease",
                "send_welcome_email": 0,
                "roles": [{"role": "Lease Viewer"}],
            }
        ).insert()
        self.lease = frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_title": "Restricted Test",
                "property": self.property_doc.name,
                "landlord": self.landlord.name,
                "lease_type": "Commercial",
                "responsible_department": self.department.name,
                "responsible_officer": "Administrator",
                "start_date": today(),
                "end_date": add_days(today(), 365),
                "notice_period_days": 30,
                "currency": "NGN",
                "rent_basis": "Monthly",
                "monthly_rent": 100,
                "payment_frequency": "Monthly",
                "confidentiality_classification": "Restricted",
            }
        ).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def make_user(self, role):
        user = f"lease-user-{frappe.generate_hash(length=8)}@example.com"
        frappe.get_doc(
            {
                "doctype": "User",
                "email": user,
                "first_name": "Lease",
                "send_welcome_email": 0,
                "roles": [{"role": role}],
            }
        ).insert()
        frappe.clear_cache(user=user)
        return user

    def new_lease(self, user, classification="Internal"):
        return frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_title": f"Permission Test {frappe.generate_hash(length=8)}",
                "property": self.property_doc.name,
                "landlord": self.landlord.name,
                "lease_type": "Commercial",
                "responsible_department": self.department.name,
                "responsible_officer": user,
                "start_date": today(),
                "end_date": add_days(today(), 365),
                "notice_period_days": 30,
                "currency": "NGN",
                "rent_basis": "Monthly",
                "monthly_rent": 100,
                "payment_frequency": "Monthly",
                "confidentiality_classification": classification,
            }
        )

    def make_lease_document(self, lease, confidentiality="Confidential"):
        content = f"permission-{frappe.generate_hash(length=12)}".encode()
        file_doc = save_file(
            f"permission-{frappe.generate_hash(length=8)}.txt",
            content,
            "Lease",
            lease.name,
            is_private=1,
        )
        document = frappe.get_doc(
            {
                "doctype": "Lease Document",
                "lease": lease.name,
                "title": "Permission Evidence",
                "category": "Correspondence",
                "file": file_doc.file_url,
                "document_date": today(),
                "effective_date": today(),
                "confidentiality": confidentiality,
            }
        ).insert()
        attached_file = frappe.get_doc("File", file_doc.name)
        return document, attached_file

    def test_viewer_cannot_read_unassigned_restricted_lease(self):
        self.assertFalse(can_access_lease(self.lease.name, self.user))

    def test_assignment_does_not_override_viewer_clearance(self):
        self.lease.responsible_officer = self.user
        self.lease.save()
        self.assertFalse(can_access_lease(self.lease.name, self.user))

    def test_administrator_retains_access(self):
        self.assertTrue(can_access_lease(self.lease.name, "Administrator"))

    def test_unrestricted_roles_can_create_leases(self):
        for role in ("Rent Renewal System Manager", "Lease Administrator"):
            with self.subTest(role=role):
                user = self.make_user(role)
                lease = self.new_lease(user)
                self.assertTrue(lease.has_permission("create", user=user))
                frappe.set_user(user)
                try:
                    lease.insert()
                finally:
                    frappe.set_user("Administrator")
                self.assertTrue(frappe.db.exists("Lease", lease.name))

    def test_responsible_officer_can_create_assigned_lease(self):
        user = self.make_user("Responsible Officer")
        lease = self.new_lease(user)

        self.assertTrue(can_access_lease_doc(lease, user))
        self.assertTrue(lease.has_permission("create", user=user))
        frappe.set_user(user)
        try:
            lease.insert()
        finally:
            frappe.set_user("Administrator")

        self.assertTrue(frappe.db.exists("Lease", lease.name))

    def test_responsible_officer_cannot_create_unassigned_lease(self):
        user = self.make_user("Responsible Officer")
        lease = self.new_lease("Administrator")

        self.assertFalse(can_access_lease_doc(lease, user))
        self.assertFalse(lease.has_permission("create", user=user))

    def test_department_permission_allows_scoped_creation(self):
        user = self.make_user("Responsible Officer")
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user,
                "allow": "Lease Department",
                "for_value": self.department.name,
                "applicable_for": "Lease",
            }
        ).insert()
        lease = self.new_lease("Administrator")

        self.assertTrue(can_access_lease_doc(lease, user))
        self.assertTrue(lease.has_permission("create", user=user))

    def test_allowed_existing_lease_returns_true_to_frappe(self):
        user = self.make_user("Lease Administrator")
        lease = frappe.get_doc("Lease", self.lease.name)

        self.assertTrue(can_access_lease(lease.name, user))
        self.assertTrue(lease.has_permission("read", user=user))

    def test_dependent_doctypes_accept_authorized_parent(self):
        user = self.make_user("Lease Administrator")
        checks = {
            "Lease Document": "create",
            "Rent Schedule": "create",
            "Renewal Request": "create",
            "Reminder Log": "read",
        }

        for doctype, permission_type in checks.items():
            with self.subTest(doctype=doctype):
                doc = frappe.new_doc(doctype)
                doc.lease = self.lease.name
                self.assertTrue(doc.has_permission(permission_type, user=user))

    def test_dependent_doctypes_reject_unauthorized_parent(self):
        user = self.make_user("Responsible Officer")
        checks = {
            "Lease Document": "create",
            "Rent Schedule": "create",
            "Renewal Request": "create",
        }

        for doctype, permission_type in checks.items():
            with self.subTest(doctype=doctype):
                doc = frappe.new_doc(doctype)
                doc.lease = self.lease.name
                self.assertFalse(doc.has_permission(permission_type, user=user))

    def test_document_confidentiality_restricts_record_and_private_file(self):
        user = self.make_user("Responsible Officer")
        lease = self.new_lease(user, classification="Internal").insert()
        document, file_doc = self.make_lease_document(lease, confidentiality="Restricted")

        self.assertTrue(can_access_lease(lease.name, user))
        self.assertFalse(document.has_permission("read", user=user))
        self.assertFalse(file_doc.has_permission("read", user=user))

        frappe.set_user(user)
        try:
            visible = frappe.get_list("Lease Document", pluck="name", limit=0)
            self.assertNotIn(document.name, visible)
            with self.assertRaises(frappe.PermissionError):
                frappe.get_doc("Lease Document", document.name).check_permission("read")
        finally:
            frappe.set_user("Administrator")

    def test_authorized_document_and_file_follow_linked_lease_scope(self):
        user = self.make_user("Responsible Officer")
        lease = self.new_lease(user, classification="Internal").insert()
        document, file_doc = self.make_lease_document(lease, confidentiality="Confidential")

        self.assertTrue(document.has_permission("read", user=user))
        self.assertTrue(file_doc.has_permission("read", user=user))

        frappe.set_user(user)
        try:
            visible = frappe.get_list("Lease Document", pluck="name", limit=0)
            self.assertIn(document.name, visible)
        finally:
            frappe.set_user("Administrator")

    def test_user_cannot_create_document_above_clearance(self):
        user = self.make_user("Responsible Officer")
        lease = self.new_lease(user, classification="Internal").insert()
        document = frappe.get_doc(
            {
                "doctype": "Lease Document",
                "lease": lease.name,
                "title": "Restricted Evidence",
                "category": "Correspondence",
                "file": "/private/files/unavailable.txt",
                "confidentiality": "Restricted",
            }
        )

        self.assertFalse(document.has_permission("create", user=user))
        frappe.set_user(user)
        try:
            with self.assertRaises(frappe.PermissionError):
                document.insert()
        finally:
            frappe.set_user("Administrator")

    def test_unsaved_document_upload_allows_every_write_enabled_role(self):
        for role in (
            "Rent Renewal System Manager",
            "Lease Administrator",
            "Responsible Officer",
        ):
            with self.subTest(role=role):
                user = self.make_user(role)
                frappe.set_user(user)
                try:
                    check_write_permission(
                        "Lease Document",
                        f"new-lease-document-{frappe.generate_hash(length=10)}",
                    )
                finally:
                    frappe.set_user("Administrator")

    def test_unsaved_document_upload_rejects_roles_without_write_permission(self):
        for role in (
            "System Manager",
            "Department Head",
            "Finance Approver",
            "Legal Approver",
            "Management Approver",
            "Lease Auditor",
            "Lease Viewer",
        ):
            with self.subTest(role=role):
                user = self.make_user(role)
                frappe.set_user(user)
                try:
                    with self.assertRaises(frappe.PermissionError):
                        check_write_permission(
                            "Lease Document",
                            f"new-lease-document-{frappe.generate_hash(length=10)}",
                        )
                finally:
                    frappe.set_user("Administrator")

    def test_authorized_writer_can_save_document_after_temporary_upload(self):
        for role in (
            "Rent Renewal System Manager",
            "Lease Administrator",
            "Responsible Officer",
        ):
            with self.subTest(role=role):
                user = self.make_user(role)
                lease = self.new_lease(user, classification="Internal").insert()
                temporary_name = f"new-lease-document-{frappe.generate_hash(length=10)}"

                frappe.set_user(user)
                try:
                    check_write_permission("Lease Document", temporary_name)
                    file_doc = save_file(
                        f"permission-{frappe.generate_hash(length=8)}.txt",
                        f"permission-{frappe.generate_hash(length=12)}".encode(),
                        "Lease Document",
                        temporary_name,
                        is_private=1,
                        df="file",
                    )
                    document = frappe.get_doc(
                        {
                            "doctype": "Lease Document",
                            "lease": lease.name,
                            "title": "Temporary Upload Evidence",
                            "category": "Correspondence",
                            "file": file_doc.file_url,
                            "document_date": today(),
                            "effective_date": today(),
                            "confidentiality": "Confidential",
                        }
                    ).insert()
                finally:
                    frappe.set_user("Administrator")

                file_doc.reload()
                self.assertEqual(file_doc.attached_to_doctype, "Lease Document")
                self.assertEqual(file_doc.attached_to_name, document.name)

    def test_read_only_role_cannot_create_revision(self):
        user = self.make_user("Department Head")
        frappe.get_doc(
            {
                "doctype": "User Permission",
                "user": user,
                "allow": "Lease Department",
                "for_value": self.department.name,
                "applicable_for": "Lease",
            }
        ).insert()
        lease = self.new_lease("Administrator", classification="Internal").insert()
        document, _ = self.make_lease_document(lease, confidentiality="Confidential")
        revision = frappe.get_doc(
            {
                "doctype": "Lease Document",
                "lease": lease.name,
                "title": document.title,
                "category": document.category,
                "file": "/private/files/unavailable.txt",
                "confidentiality": document.confidentiality,
                "previous_revision": document.name,
                "revision_reason": "Read-only users cannot revise evidence.",
            }
        )

        self.assertTrue(document.has_permission("read", user=user))
        frappe.set_user(user)
        try:
            with self.assertRaises(frappe.PermissionError):
                revision.insert()
        finally:
            frappe.set_user("Administrator")

        self.assertFalse(document.has_permission("write", user=user))
        self.assertFalse(revision.has_permission("create", user=user))


    def test_submit_and_cancel_roles_follow_evidence_responsibilities(self):
        for role in ("Rent Renewal System Manager", "Lease Administrator", "Responsible Officer"):
            with self.subTest(role=role):
                user = self.make_user(role)
                lease = self.new_lease(user, classification="Internal").insert()
                frappe.set_user(user)
                try:
                    document, _ = self.make_lease_document(lease, confidentiality="Confidential")
                    self.assertTrue(document.has_permission("submit"))
                    document.submit()
                finally:
                    frappe.set_user("Administrator")
                self.assertEqual(document.docstatus, 1)

        for role in ("Rent Renewal System Manager", "Lease Administrator"):
            with self.subTest(cancel_role=role):
                user = self.make_user(role)
                lease = self.new_lease(user, classification="Internal").insert()
                frappe.set_user(user)
                try:
                    document, _ = self.make_lease_document(lease, confidentiality="Confidential")
                    document.submit()
                    document.cancellation_reason = "Authorised evidence cancellation."
                    document.save()
                    self.assertTrue(document.has_permission("cancel"))
                    document.cancel()
                finally:
                    frappe.set_user("Administrator")
                self.assertEqual(document.docstatus, 2)

    def test_responsible_officer_can_submit_but_cannot_cancel(self):
        user = self.make_user("Responsible Officer")
        lease = self.new_lease(user, classification="Internal").insert()
        frappe.set_user(user)
        try:
            document, _ = self.make_lease_document(lease, confidentiality="Confidential")
            document.submit()
            document.cancellation_reason = "Responsible Officer must escalate cancellation."
            document.save()
            self.assertFalse(document.has_permission("cancel"))
            with self.assertRaises(frappe.PermissionError):
                document.cancel()
        finally:
            frappe.set_user("Administrator")

    def test_read_only_roles_cannot_submit_or_cancel_lease_documents(self):
        document, _ = self.make_lease_document(self.lease, confidentiality="Confidential")
        for role in (
            "Department Head",
            "Finance Approver",
            "Legal Approver",
            "Management Approver",
            "Lease Auditor",
            "Lease Viewer",
        ):
            with self.subTest(role=role):
                user = self.make_user(role)
                self.assertFalse(document.has_permission("submit", user=user))
                self.assertFalse(document.has_permission("cancel", user=user))
