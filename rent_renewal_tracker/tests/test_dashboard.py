from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from rent_renewal_tracker.dashboard import (
    annual_rent_exposure,
    leases_expiring_90_days,
    overdue_rent_obligations,
)
from rent_renewal_tracker.rent_renewal_tracker.report.setup_readiness.setup_readiness import (
    execute as setup_readiness,
)


class TestDashboard(IntegrationTestCase):
    def test_expiry_card_links_to_filtered_report(self):
        card = leases_expiring_90_days()

        self.assertEqual(card["fieldtype"], "Int")
        self.assertNotIn("currency", card)
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

    def test_overdue_obligations_sum_money_instead_of_counting_rows(self):
        settings = frappe.get_single("Rent Renewal Settings")
        settings.default_currency = "NGN"
        settings.save()

        rows = [
            frappe._dict(currency="NGN", total_due=125),
            frappe._dict(currency="NGN", total_due=275),
        ]
        with patch("rent_renewal_tracker.dashboard.frappe.get_list", return_value=rows):
            card = overdue_rent_obligations()

        self.assertEqual(card["value"], 400)
        self.assertEqual(card["fieldtype"], "Currency")
        self.assertEqual(card["currency"], "NGN")
        self.assertEqual(
            card["route_options"],
            {"action_type": "Overdue Payment"},
        )

    def test_setup_readiness_includes_overlap_review(self):
        columns, rows, _, _, summary = setup_readiness({})

        self.assertEqual(len(rows), 7)
        self.assertIn("status", {column["fieldname"] for column in columns})
        self.assertEqual(summary[0]["label"], "Ready")
