import frappe
from frappe.tests import IntegrationTestCase

from rent_renewal_tracker.api import has_app_permission
from rent_renewal_tracker.health import verify_installation
from rent_renewal_tracker.install import APP_ROLES, WORKFLOW_ACTIONS, WORKFLOW_STATES


class TestInstallationDefaults(IntegrationTestCase):
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

    def test_apps_screen_entry_is_not_available_to_guests(self):
        frappe.set_user("Guest")
        try:
            self.assertFalse(has_app_permission())
        finally:
            frappe.set_user("Administrator")

        self.assertTrue(has_app_permission())

    def test_installation_health_contract_passes(self):
        checks = verify_installation()

        self.assertTrue(all(checks.values()))
