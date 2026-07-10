import frappe

from rent_renewal_tracker.install import APP_ROLES, WORKFLOW_ACTIONS, WORKFLOW_STATES


REQUIRED_DOCTYPES = (
    "Property",
    "Landlord",
    "Lease Department",
    "Lease Contact",
    "Lease",
    "Rent Schedule",
    "Lease Document",
    "Renewal Request",
    "Renewal Decision",
    "Reminder Policy",
    "Reminder Threshold",
    "Reminder Recipient",
    "Reminder Log",
    "Rent Renewal Settings",
)

REQUIRED_REPORTS = (
    "Upcoming Expiries",
    "Renewal Pipeline",
    "Upcoming Payments",
    "Rent Exposure",
    "Reminder Delivery",
)


def verify_installation():
    """Raise on an incomplete Bench installation and return a concise health snapshot."""
    checks = {
        "app_installed": "rent_renewal_tracker" in frappe.get_installed_apps(),
        "doctypes": all(frappe.db.exists("DocType", name) for name in REQUIRED_DOCTYPES),
        "roles": all(frappe.db.exists("Role", name) for name in APP_ROLES),
        "workflow_states": all(
            frappe.db.exists("Workflow State", name) for name in WORKFLOW_STATES
        ),
        "workflow_actions": all(
            frappe.db.exists("Workflow Action Master", name) for name in WORKFLOW_ACTIONS
        ),
        "workflow": bool(
            frappe.db.get_value(
                "Workflow",
                "Rent Renewal Approval",
                "is_active",
            )
        ),
        "reminder_policy": bool(
            frappe.db.get_single_value("Rent Renewal Settings", "default_reminder_policy")
        ),
        "workspace": bool(frappe.db.exists("Workspace", "Rent Renewal Tracker")),
        "reports": all(frappe.db.exists("Report", name) for name in REQUIRED_REPORTS),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        frappe.throw(f"Rent Renewal Tracker installation checks failed: {', '.join(failed)}")
    return checks
