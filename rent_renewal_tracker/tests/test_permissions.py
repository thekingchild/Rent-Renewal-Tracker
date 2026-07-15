import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

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
