import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from rent_renewal_tracker.permissions import can_access_lease


class TestLeasePermissions(IntegrationTestCase):
    def setUp(self):
        self.department = frappe.get_doc({
            "doctype": "Lease Department",
            "department_name": frappe.generate_hash(length=10),
        }).insert()
        property_doc = frappe.get_doc({
            "doctype": "Property", "property_name": frappe.generate_hash(length=10),
            "property_type": "Office",
        }).insert()
        landlord = frappe.get_doc({
            "doctype": "Landlord", "legal_name": frappe.generate_hash(length=10),
        }).insert()
        self.user = f"lease-user-{frappe.generate_hash(length=8)}@example.com"
        frappe.get_doc({
            "doctype": "User", "email": self.user, "first_name": "Lease", "send_welcome_email": 0,
            "roles": [{"role": "Lease Viewer"}],
        }).insert()
        self.lease = frappe.get_doc({
            "doctype": "Lease", "lease_title": "Restricted Test", "property": property_doc.name,
            "landlord": landlord.name, "lease_type": "Commercial",
            "responsible_department": self.department.name, "responsible_officer": "Administrator",
            "start_date": today(), "end_date": add_days(today(), 365), "notice_period_days": 30,
            "currency": "NGN", "rent_basis": "Monthly", "monthly_rent": 100,
            "payment_frequency": "Monthly", "confidentiality_classification": "Restricted",
        }).insert()

    def test_viewer_cannot_read_unassigned_restricted_lease(self):
        self.assertFalse(can_access_lease(self.lease.name, self.user))

    def test_assignment_does_not_override_viewer_clearance(self):
        self.lease.responsible_officer = self.user
        self.lease.save()
        self.assertFalse(can_access_lease(self.lease.name, self.user))

    def test_administrator_retains_access(self):
        self.assertTrue(can_access_lease(self.lease.name, "Administrator"))
