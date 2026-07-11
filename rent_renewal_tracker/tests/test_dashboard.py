import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from rent_renewal_tracker.dashboard import annual_rent_exposure, leases_expiring_90_days
from rent_renewal_tracker.rent_renewal_tracker.report.setup_readiness.setup_readiness import (
    execute as setup_readiness,
)


class TestDashboard(IntegrationTestCase):
    def test_expiry_card_links_to_filtered_report(self):
        card = leases_expiring_90_days()

        self.assertEqual(card["route"], ["query-report", "Upcoming Expiries"])
        self.assertEqual(card["route_options"]["from_date"], today())
        self.assertEqual(card["route_options"]["to_date"], add_days(today(), 90))

    def test_exposure_card_never_combines_currencies(self):
        settings = frappe.get_single("Rent Renewal Settings")
        settings.default_currency = "NGN"
        settings.save()

        card = annual_rent_exposure()

        self.assertEqual(card["fieldtype"], "Currency")
        self.assertEqual(card["currency"], "NGN")
        self.assertEqual(card["route_options"], {"currency": "NGN"})

    def test_setup_readiness_returns_six_checks(self):
        columns, rows, _, _, summary = setup_readiness({})

        self.assertEqual(len(rows), 6)
        self.assertIn("status", {column["fieldname"] for column in columns})
        self.assertEqual(summary[0]["label"], "Ready")
