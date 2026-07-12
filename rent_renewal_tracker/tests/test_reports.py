import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from rent_renewal_tracker.reminders import process_due_reminders
from rent_renewal_tracker.rent_renewal_tracker.report.my_actions.my_actions import (
    execute as my_actions,
)
from rent_renewal_tracker.rent_renewal_tracker.report.reminder_delivery.reminder_delivery import (
    execute as reminder_delivery,
)
from rent_renewal_tracker.rent_renewal_tracker.report.renewal_pipeline.renewal_pipeline import (
    execute as renewal_pipeline,
)
from rent_renewal_tracker.rent_renewal_tracker.report.rent_exposure.rent_exposure import (
    execute as rent_exposure,
)
from rent_renewal_tracker.rent_renewal_tracker.report.upcoming_expiries.upcoming_expiries import (
    execute as upcoming_expiries,
)
from rent_renewal_tracker.rent_renewal_tracker.report.upcoming_payments.upcoming_payments import (
    execute as upcoming_payments,
)


class TestOperationalReports(IntegrationTestCase):
    def setUp(self):
        self.department = frappe.get_doc(
            {"doctype": "Lease Department", "department_name": frappe.generate_hash(length=10)}
        ).insert()
        self.property = frappe.get_doc(
            {
                "doctype": "Property",
                "property_name": f"Report Property {frappe.generate_hash(length=8)}",
                "property_type": "Office",
                "region": "West",
            }
        ).insert()
        self.landlord = frappe.get_doc(
            {
                "doctype": "Landlord",
                "legal_name": f"Report Landlord {frappe.generate_hash(length=8)}",
            }
        ).insert()
        self.lease = frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_title": "Report Test Lease",
                "property": self.property.name,
                "landlord": self.landlord.name,
                "lease_type": "Commercial",
                "responsible_department": self.department.name,
                "responsible_officer": "Administrator",
                "start_date": add_days(today(), -365),
                "end_date": add_days(today(), 60),
                "notice_period_days": 30,
                "currency": "NGN",
                "rent_basis": "Monthly",
                "monthly_rent": 100000,
                "payment_frequency": "Monthly",
                "lease_status": "Active",
            }
        ).insert()

    def test_upcoming_expiries_returns_permitted_lease(self):
        columns, rows, _, chart = upcoming_expiries(
            {"from_date": today(), "to_date": add_days(today(), 90)}
        )

        self.assertIn("days_to_expiry", {column["fieldname"] for column in columns})
        row = next(row for row in rows if row.name == self.lease.name)
        self.assertEqual(row.days_to_expiry, 60)
        self.assertGreaterEqual(chart["data"]["datasets"][0]["values"][1], 1)

    def test_renewal_pipeline_returns_snapshot_and_age(self):
        renewal = frappe.get_doc(
            {
                "doctype": "Renewal Request",
                "lease": self.lease.name,
                "proposed_end_date": add_days(self.lease.end_date, 365),
                "recommendation": "Renew",
                "business_justification": "Operational continuity.",
            }
        ).insert()

        _, rows, _, chart = renewal_pipeline({})
        row = next(row for row in rows if row.name == renewal.name)
        self.assertEqual(row.workflow_state, "Draft")
        self.assertEqual(row.proposed_annual_rent, 1200000)
        self.assertEqual(row.age_days, 0)
        self.assertEqual(chart["data"]["datasets"][0]["values"][0], 1)

    def test_upcoming_payments_returns_calculated_total(self):
        schedule = frappe.get_doc(
            {
                "doctype": "Rent Schedule",
                "lease": self.lease.name,
                "description": "Next rent payment",
                "period_from": today(),
                "period_to": add_days(today(), 30),
                "due_date": add_days(today(), 10),
                "currency": "NGN",
                "base_rent": 100000,
                "service_charge": 10000,
                "tax": 5000,
            }
        ).insert()

        _, rows = upcoming_payments(
            {"from_date": today(), "to_date": add_days(today(), 30)}
        )
        row = next(row for row in rows if row.name == schedule.name)
        self.assertEqual(row.total_due, 115000)
        self.assertEqual(row.days_until_due, 10)

    def test_rent_exposure_preserves_currency_and_region(self):
        _, rows, message = rent_exposure({"currency": "NGN", "region": "West"})

        row = next(row for row in rows if row.name == self.lease.name)
        self.assertEqual(row.region, "West")
        self.assertEqual(row.annual_rent, 1200000)
        self.assertEqual(row.total_annual_occupancy_cost, 1200000)
        self.assertIsNone(message)

    def test_reminder_delivery_reconciles_attempt_summary(self):
        process_due_reminders(queue_deliveries=False)
        columns, rows, _, chart, summary = reminder_delivery(
            {"from_date": today(), "to_date": today(), "lease": self.lease.name}
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual({row.status for row in rows}, {"Queued"})
        self.assertIn("status", {column["fieldname"] for column in columns})
        self.assertEqual(chart["data"]["datasets"][0]["values"], [2, 0, 0])
        self.assertEqual(summary[0]["value"], 2)

    def test_my_actions_includes_assigned_expiry(self):
        _, rows, _ = my_actions({"action_type": "Lease Expiry"})

        row = next(row for row in rows if row.reference_name == self.lease.name)
        self.assertEqual(row.reference_doctype, "Lease")
        self.assertEqual(row.priority, "Medium")
