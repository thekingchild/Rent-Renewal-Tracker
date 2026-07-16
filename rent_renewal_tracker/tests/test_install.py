import frappe
from frappe.tests import IntegrationTestCase

from rent_renewal_tracker import hooks
from rent_renewal_tracker.api import has_app_permission
from rent_renewal_tracker.health import verify_installation
from rent_renewal_tracker.install import (
    APP_ROLES,
    COUNT_NUMBER_CARDS,
    DASHBOARD_CHARTS,
    FIRST_RUN_BLOCK,
    MONETARY_NUMBER_CARDS,
    NUMBER_CARDS,
    WORKFLOW_ACTIONS,
    WORKFLOW_STATES,
    set_missing_required_settings,
)
from rent_renewal_tracker.patches.v0_7.normalize_dashboard_number_card_currency import (
    execute as normalize_dashboard_number_card_currency,
)


class TestInstallationDefaults(IntegrationTestCase):
    def test_submittable_doctypes_are_amendable(self):
        for doctype in ("Lease", "Renewal Request", "Rent Schedule"):
            field = frappe.get_meta(doctype).get_field("amended_from")

            self.assertIsNotNone(field, doctype)
            self.assertEqual(field.fieldtype, "Link")
            self.assertEqual(field.options, doctype)
            self.assertTrue(field.read_only)
            self.assertTrue(field.print_hide)
            self.assertTrue(field.no_copy)
            self.assertTrue(field.search_index)

    def test_application_roles_exist(self):
        for role in APP_ROLES:
            self.assertTrue(frappe.db.exists("Role", role), role)

    def test_workflow_primitives_exist(self):
        for state in WORKFLOW_STATES:
            self.assertTrue(frappe.db.exists("Workflow State", state), state)
        for action in WORKFLOW_ACTIONS:
            self.assertTrue(frappe.db.exists("Workflow Action Master", action), action)

    def test_default_workflow_is_active(self):
        workflow = frappe.get_doc("Workflow", "Rent Renewal Approval")

        self.assertEqual(workflow.document_type, "Renewal Request")
        self.assertTrue(workflow.is_active)
        self.assertEqual(len(workflow.states), 8)
        self.assertEqual(len(workflow.transitions), 11)
        state_docstatus = {row.state: row.doc_status for row in workflow.states}
        self.assertEqual(state_docstatus["Rejected"], "0")
        self.assertEqual(state_docstatus["Approved"], "1")
        self.assertEqual(state_docstatus["Completed"], "1")

    def test_default_reminder_configuration_exists(self):
        settings = frappe.get_single("Rent Renewal Settings")
        policy = frappe.get_doc("Reminder Policy", settings.default_reminder_policy)

        self.assertTrue(policy.enabled)
        self.assertEqual(
            {row.days_before_expiry for row in policy.thresholds if row.enabled},
            {90, 60, 30, 14, 7, 0},
        )
        self.assertEqual(policy.overdue_cadence_days, 7)

    def test_required_settings_defaults_exist(self):
        settings = frappe.get_single("Rent Renewal Settings")

        self.assertEqual(settings.expiring_soon_threshold, 90)
        self.assertEqual(settings.document_expiring_soon_threshold, 30)
        self.assertIsNotNone(settings.reminder_retry_limit)

    def test_required_settings_defaults_preserve_valid_zero(self):
        settings = frappe.get_single("Rent Renewal Settings")
        settings.reminder_retry_limit = 0

        set_missing_required_settings(settings)
        self.assertEqual(settings.reminder_retry_limit, 0)

    def test_apps_screen_entry_is_not_available_to_guests(self):
        frappe.set_user("Guest")
        try:
            self.assertFalse(has_app_permission())
        finally:
            frappe.set_user("Administrator")

        self.assertTrue(has_app_permission())

    def test_apps_screen_entry_uses_same_page_desk_route(self):
        self.assertEqual(
            hooks.add_to_apps_screen[0]["route"],
            "/desk/rent-renewal-tracker",
        )

    def test_installation_health_contract_passes(self):
        checks = verify_installation()

        self.assertTrue(all(checks.values()))

    def test_dashboard_assets_exist(self):
        for label, method, document_type, _ in NUMBER_CARDS:
            self.assertTrue(
                frappe.db.exists(
                    "Number Card",
                    {"label": label, "method": method, "document_type": document_type},
                )
            )
        for chart_name, report_name in DASHBOARD_CHARTS:
            self.assertTrue(
                frappe.db.exists(
                    "Dashboard Chart",
                    {"name": chart_name, "report_name": report_name},
                )
            )

        self.assertTrue(frappe.db.exists("Custom HTML Block", FIRST_RUN_BLOCK))
        for label in COUNT_NUMBER_CARDS:
            self.assertFalse(frappe.db.get_value("Number Card", {"label": label}, "currency"))

    def test_dashboard_currency_patch_normalizes_existing_cards(self):
        settings = frappe.get_single("Rent Renewal Settings")
        expected_currency = (
            settings.default_currency or frappe.defaults.get_global_default("currency")
        )
        stale_currency = expected_currency or "NGN"

        for label in COUNT_NUMBER_CARDS:
            frappe.db.set_value("Number Card", {"label": label}, "currency", stale_currency)
        for label in MONETARY_NUMBER_CARDS:
            frappe.db.set_value("Number Card", {"label": label}, "currency", None)

        normalize_dashboard_number_card_currency()
        normalize_dashboard_number_card_currency()

        for label in COUNT_NUMBER_CARDS:
            self.assertFalse(frappe.db.get_value("Number Card", {"label": label}, "currency"))
        for label in MONETARY_NUMBER_CARDS:
            self.assertEqual(
                frappe.db.get_value("Number Card", {"label": label}, "currency"),
                expected_currency,
            )
