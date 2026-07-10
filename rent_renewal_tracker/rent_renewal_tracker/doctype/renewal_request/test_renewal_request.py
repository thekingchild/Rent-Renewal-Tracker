import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today


class TestRenewalRequest(IntegrationTestCase):
    def setUp(self):
        department = frappe.get_doc(
            {"doctype": "Lease Department", "department_name": frappe.generate_hash(length=10)}
        ).insert()
        property_doc = frappe.get_doc(
            {
                "doctype": "Property",
                "property_name": f"Renewal Property {frappe.generate_hash(length=8)}",
                "property_type": "Office",
            }
        ).insert()
        landlord = frappe.get_doc(
            {
                "doctype": "Landlord",
                "legal_name": f"Renewal Landlord {frappe.generate_hash(length=8)}",
            }
        ).insert()
        self.lease = frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_title": "Renewal Test Lease",
                "property": property_doc.name,
                "landlord": landlord.name,
                "lease_type": "Commercial",
                "responsible_department": department.name,
                "responsible_officer": "Administrator",
                "start_date": add_days(today(), -365),
                "end_date": add_days(today(), 90),
                "notice_period_days": 60,
                "currency": "NGN",
                "rent_basis": "Monthly",
                "monthly_rent": 100000,
                "payment_frequency": "Monthly",
                "lease_status": "Active",
            }
        ).insert()

    def make_request(self, **overrides):
        values = {
            "doctype": "Renewal Request",
            "lease": self.lease.name,
            "proposed_end_date": add_days(self.lease.end_date, 366),
            "recommendation": "Renew",
            "business_justification": "The location remains operationally necessary.",
        }
        values.update(overrides)
        return frappe.get_doc(values)

    def test_snapshots_current_terms_and_defaults_proposal(self):
        renewal = self.make_request().insert()

        self.assertEqual(renewal.renewal_sequence, 1)
        self.assertEqual(renewal.current_end_date, self.lease.end_date)
        self.assertEqual(renewal.current_annual_rent, 1200000)
        self.assertEqual(renewal.proposed_start_date, add_days(self.lease.end_date, 1))
        self.assertEqual(renewal.proposed_annual_rent, 1200000)
        self.assertEqual(renewal.open_cycle_key, self.lease.name)

    def test_updates_parent_lease_to_renewal_in_progress(self):
        renewal = self.make_request().insert()
        lease = frappe.get_doc("Lease", self.lease.name)

        self.assertEqual(lease.renewal_status, "Draft")
        self.assertEqual(lease.lease_status, "Renewal in Progress")
        self.assertEqual(lease.last_renewal_request, renewal.name)

    def test_prevents_second_open_request_for_same_lease(self):
        first = self.make_request().insert()

        with self.assertRaises(frappe.ValidationError):
            self.make_request().insert()

        self.assertTrue(frappe.db.exists("Renewal Request", first.name))

    def test_rejects_invalid_proposed_term(self):
        renewal = self.make_request(
            proposed_start_date=add_days(today(), 30),
            proposed_end_date=add_days(today(), 29),
        )

        self.assertRaises(frappe.ValidationError, renewal.insert)

    def test_monthly_proposal_recalculates_annual_rent(self):
        renewal = self.make_request(proposed_monthly_rent=125000).insert()

        self.assertEqual(renewal.proposed_annual_rent, 1500000)

    def test_successor_lease_creation_is_idempotent(self):
        renewal = self.make_request().insert()

        first_name = renewal.create_successor_lease()
        second_name = renewal.create_successor_lease()
        successor = frappe.get_doc("Lease", first_name)

        self.assertEqual(second_name, first_name)
        self.assertEqual(successor.predecessor_lease, self.lease.name)
        self.assertEqual(successor.start_date, add_days(self.lease.end_date, 1))
        self.assertEqual(successor.end_date, renewal.proposed_end_date)
        self.assertEqual(successor.annual_rent, renewal.proposed_annual_rent)
