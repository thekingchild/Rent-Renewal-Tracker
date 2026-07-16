import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today


class TestRentSchedule(IntegrationTestCase):
    def setUp(self):
        department = frappe.get_doc(
            {"doctype": "Lease Department", "department_name": frappe.generate_hash(length=10)}
        ).insert()
        property_doc = frappe.get_doc(
            {
                "doctype": "Property",
                "property_name": f"Schedule Property {frappe.generate_hash(length=8)}",
                "property_type": "Office",
            }
        ).insert()
        landlord = frappe.get_doc(
            {
                "doctype": "Landlord",
                "legal_name": f"Schedule Landlord {frappe.generate_hash(length=8)}",
            }
        ).insert()
        self.lease = frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_title": "Schedule Test Lease",
                "property": property_doc.name,
                "landlord": landlord.name,
                "lease_type": "Commercial",
                "responsible_department": department.name,
                "responsible_officer": "Administrator",
                "start_date": add_days(today(), -90),
                "end_date": add_days(today(), 275),
                "notice_period_days": 60,
                "currency": "NGN",
                "rent_basis": "Monthly",
                "monthly_rent": 100000,
                "payment_frequency": "Monthly",
                "lease_status": "Active",
            }
        ).insert()

    def make_schedule(self, **overrides):
        values = {
            "doctype": "Rent Schedule",
            "lease": self.lease.name,
            "description": "Monthly rent",
            "period_from": add_days(today(), -30),
            "period_to": add_days(today(), -1),
            "due_date": today(),
            "currency": "NGN",
            "base_rent": 100000,
            "service_charge": 10000,
            "tax": 5000,
        }
        values.update(overrides)
        return frappe.get_doc(values)

    def test_calculates_total_and_due_status(self):
        schedule = self.make_schedule().insert()

        self.assertEqual(schedule.total_due, 115000)
        self.assertEqual(schedule.schedule_status, "Due")

    def test_marks_past_unpaid_schedule_overdue(self):
        schedule = self.make_schedule(due_date=add_days(today(), -1)).insert()

        self.assertEqual(schedule.schedule_status, "Overdue")

    def test_paid_status_takes_precedence_over_due_date(self):
        schedule = self.make_schedule(
            due_date=add_days(today(), -10), payment_status="Paid", paid_on=today(),
            payment_reference="TEST-PAID-001",
        ).insert()

        self.assertEqual(schedule.schedule_status, "Paid")

    def test_rejects_currency_different_from_lease(self):
        schedule = self.make_schedule(currency="USD")

        self.assertRaises(frappe.ValidationError, schedule.insert)

    def test_rejects_period_outside_lease(self):
        schedule = self.make_schedule(period_to=add_days(self.lease.end_date, 1))

        self.assertRaises(frappe.ValidationError, schedule.insert)

    def test_cancelled_schedule_can_be_amended_and_resubmitted(self):
        schedule = self.make_schedule().insert()
        schedule.submit()
        schedule.cancel()

        amendment = frappe.copy_doc(schedule)
        amendment.docstatus = 0
        amendment.amended_from = schedule.name
        amendment.insert()
        amendment.submit()

        self.assertEqual(amendment.amended_from, schedule.name)
        self.assertEqual(amendment.name, f"{schedule.name}-1")
        self.assertEqual(amendment.docstatus, 1)
        self.assertEqual(amendment.schedule_status, "Due")
