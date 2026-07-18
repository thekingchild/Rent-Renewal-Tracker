import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from rent_renewal_tracker.rent_renewal_tracker.doctype.rent_schedule.rent_schedule import (
    calculate_lease_financial_defaults,
)


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
            due_date=add_days(today(), -10),
            payments=[
                {
                    "payment_date": today(),
                    "amount": 115000,
                    "reference": "TEST-PAID-001",
                }
            ],
        ).insert()

        self.assertEqual(schedule.schedule_status, "Paid")

    def test_rejects_currency_different_from_lease(self):
        schedule = self.make_schedule(currency="USD")

        self.assertRaises(frappe.ValidationError, schedule.insert)

    def test_rejects_period_outside_lease(self):
        schedule = self.make_schedule(period_to=add_days(self.lease.end_date, 1))

        self.assertRaises(frappe.ValidationError, schedule.insert)

    def test_missing_amounts_default_from_monthly_lease(self):
        schedule = self.make_schedule(
            currency=None, base_rent=None, service_charge=None, tax=None
        ).insert()

        self.assertEqual(schedule.currency, "NGN")
        self.assertEqual(schedule.base_rent, 100000)
        self.assertEqual(schedule.total_due, 100000)
        self.assertEqual(schedule.outstanding_balance, 100000)

    def test_annual_terms_are_divided_by_payment_frequency(self):
        lease = frappe.get_doc("Lease", self.lease.name)
        lease.rent_basis = "Annual"
        lease.annual_rent = 1200000
        lease.payment_frequency = "Quarterly"
        lease.annual_service_charge = 120000
        lease.annual_tax = 24000
        defaults = calculate_lease_financial_defaults(lease)

        self.assertEqual(defaults.base_rent, 300000)
        self.assertEqual(defaults.service_charge, 30000)
        self.assertEqual(defaults.tax, 6000)

    def test_unsupported_rent_basis_requires_manual_amount(self):
        lease = frappe.get_doc("Lease", self.lease.name)
        lease.rent_basis = "Per Square Metre"
        defaults = calculate_lease_financial_defaults(lease)

        self.assertTrue(defaults.requires_manual_amount)
        self.assertIsNone(defaults.base_rent)

    def test_partial_payments_accumulate_until_paid_in_full(self):
        schedule = self.make_schedule(
            payments=[{
                "payment_date": today(),
                "amount": 40000,
                "reference": "TEST-PARTIAL-001",
            }]
        ).insert()

        self.assertEqual(schedule.payment_status, "Partially Paid")
        self.assertEqual(schedule.schedule_status, "Partially Paid")
        self.assertEqual(schedule.total_paid, 40000)
        self.assertEqual(schedule.outstanding_balance, 75000)

        schedule.append(
            "payments",
            {
                "payment_date": today(),
                "amount": 75000,
                "reference": "TEST-BALANCE-001",
            },
        )
        schedule.save()

        self.assertEqual(schedule.payment_status, "Paid")
        self.assertEqual(schedule.schedule_status, "Paid")
        self.assertEqual(schedule.total_paid, 115000)
        self.assertEqual(schedule.outstanding_balance, 0)

    def test_rejects_payment_above_outstanding_balance(self):
        schedule = self.make_schedule(
            payments=[{
                "payment_date": today(),
                "amount": 115001,
                "reference": "TEST-OVERPAY-001",
            }]
        )

        with self.assertRaises(frappe.ValidationError):
            schedule.insert()

    def test_payment_can_be_recorded_after_schedule_submission(self):
        schedule = self.make_schedule().insert()
        schedule.submit()
        schedule.append(
            "payments",
            {
                "payment_date": today(),
                "amount": 25000,
                "reference": "TEST-SUBMITTED-001",
            },
        )
        schedule.save()

        self.assertEqual(schedule.payment_status, "Partially Paid")
        self.assertEqual(schedule.outstanding_balance, 90000)

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
