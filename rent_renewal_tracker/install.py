import frappe


APP_ROLES = (
    "Rent Renewal System Manager",
    "Lease Administrator",
    "Responsible Officer",
    "Department Head",
    "Finance Approver",
    "Legal Approver",
    "Management Approver",
    "Lease Auditor",
    "Lease Viewer",
)

WORKFLOW_STATES = {
    "Draft": "Info",
    "Department Review": "Warning",
    "Finance Review": "Warning",
    "Legal Review": "Warning",
    "Management Approval": "Warning",
    "Approved": "Success",
    "Rejected": "Danger",
    "Completed": "Success",
}

WORKFLOW_ACTIONS = (
    "Submit for Department Review",
    "Approve",
    "Return",
    "Reject",
    "Mark Executed",
)


def before_install():
    """Create roles before DocType permissions referencing them are synchronized."""
    setup_roles_and_workflow_primitives()


def setup_roles_and_workflow_primitives():
    for role_name in APP_ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)

    for state_name, style in WORKFLOW_STATES.items():
        if not frappe.db.exists("Workflow State", state_name):
            frappe.get_doc(
                {"doctype": "Workflow State", "workflow_state_name": state_name, "style": style}
            ).insert(ignore_permissions=True)

    for action_name in WORKFLOW_ACTIONS:
        if not frappe.db.exists("Workflow Action Master", action_name):
            frappe.get_doc(
                {"doctype": "Workflow Action Master", "workflow_action_name": action_name}
            ).insert(ignore_permissions=True)


def after_install():
    """Install the default native renewal workflow after app DocTypes are synchronized."""
    setup_renewal_workflow()
    setup_reminder_defaults()
    setup_dashboard_defaults()


NUMBER_CARDS = (
    ("Expiring in 30 Days", "rent_renewal_tracker.dashboard.leases_expiring_30_days", "Lease", "#b45309"),
    ("Expiring in 60 Days", "rent_renewal_tracker.dashboard.leases_expiring_60_days", "Lease", "#d97706"),
    ("Expiring in 90 Days", "rent_renewal_tracker.dashboard.leases_expiring_90_days", "Lease", "#f59e0b"),
    (
        "Renewals Waiting for Me",
        "rent_renewal_tracker.dashboard.renewals_waiting_for_me",
        "Renewal Request",
        "#2563eb",
    ),
    (
        "Overdue Rent Obligations",
        "rent_renewal_tracker.dashboard.overdue_rent_obligations",
        "Rent Schedule",
        "#dc2626",
    ),
    ("Failed Reminders", "rent_renewal_tracker.dashboard.failed_reminders", "Reminder Log", "#991b1b"),
    ("Annual Rent Exposure", "rent_renewal_tracker.dashboard.annual_rent_exposure", "Lease", "#047857"),
)

DASHBOARD_CHARTS = (
    ("Lease Expiry Outlook", "Upcoming Expiries"),
    ("Renewal Workflow", "Renewal Pipeline"),
)


def setup_dashboard_defaults():
    for label, method, document_type, color in NUMBER_CARDS:
        name = frappe.db.get_value("Number Card", {"label": label}, "name")
        card = frappe.get_doc("Number Card", name) if name else frappe.new_doc("Number Card")
        card.update(
            {
                "label": label,
                "type": "Custom",
                "method": method,
                "document_type": document_type,
                "is_public": 1,
                "is_standard": 0,
                "module": "Rent Renewal Tracker",
                "show_percentage_stats": 0,
                "show_full_number": 1,
                "color": color,
            }
        )
        card.save(ignore_permissions=True)

    for chart_name, report_name in DASHBOARD_CHARTS:
        chart = (
            frappe.get_doc("Dashboard Chart", chart_name)
            if frappe.db.exists("Dashboard Chart", chart_name)
            else frappe.new_doc("Dashboard Chart")
        )
        chart.update(
            {
                "chart_name": chart_name,
                "chart_type": "Report",
                "report_name": report_name,
                "use_report_chart": 1,
                "filters_json": "{}",
                "is_public": 1,
                "is_standard": 0,
                "module": "Rent Renewal Tracker",
            }
        )
        chart.save(ignore_permissions=True)


def setup_renewal_workflow():
    workflow_name = "Rent Renewal Approval"
    workflow = (
        frappe.get_doc("Workflow", workflow_name)
        if frappe.db.exists("Workflow", workflow_name)
        else frappe.new_doc("Workflow")
    )
    workflow.update(
        {
            "workflow_name": workflow_name,
            "document_type": "Renewal Request",
            "is_active": 1,
            "override_status": 0,
            "send_email_alert": 1,
            "enable_action_confirmation": 1,
            "workflow_state_field": "workflow_state",
        }
    )
    workflow.set(
        "states",
        [
            {"state": "Draft", "doc_status": "0", "allow_edit": "All"},
            {"state": "Department Review", "doc_status": "0", "allow_edit": "Department Head"},
            {"state": "Finance Review", "doc_status": "0", "allow_edit": "Finance Approver"},
            {"state": "Legal Review", "doc_status": "0", "allow_edit": "Legal Approver"},
            {
                "state": "Management Approval",
                "doc_status": "0",
                "allow_edit": "Management Approver",
            },
            {"state": "Approved", "doc_status": "1", "allow_edit": "Lease Administrator"},
            {"state": "Rejected", "doc_status": "0", "allow_edit": "Management Approver"},
            {"state": "Completed", "doc_status": "1", "allow_edit": "Lease Administrator"},
        ],
    )
    workflow.set(
        "transitions",
        [
            {
                "state": "Draft",
                "action": "Submit for Department Review",
                "next_state": "Department Review",
                "allowed": "Responsible Officer",
                "allow_self_approval": 1,
            },
            {
                "state": "Draft",
                "action": "Submit for Department Review",
                "next_state": "Department Review",
                "allowed": "Lease Administrator",
                "allow_self_approval": 1,
            },
            {
                "state": "Department Review",
                "action": "Approve",
                "next_state": "Finance Review",
                "allowed": "Department Head",
                "allow_self_approval": 0,
            },
            {
                "state": "Department Review",
                "action": "Return",
                "next_state": "Draft",
                "allowed": "Department Head",
                "allow_self_approval": 0,
            },
            {
                "state": "Finance Review",
                "action": "Approve",
                "next_state": "Legal Review",
                "allowed": "Finance Approver",
                "allow_self_approval": 0,
            },
            {
                "state": "Finance Review",
                "action": "Return",
                "next_state": "Draft",
                "allowed": "Finance Approver",
                "allow_self_approval": 0,
            },
            {
                "state": "Legal Review",
                "action": "Approve",
                "next_state": "Management Approval",
                "allowed": "Legal Approver",
                "allow_self_approval": 0,
            },
            {
                "state": "Legal Review",
                "action": "Return",
                "next_state": "Draft",
                "allowed": "Legal Approver",
                "allow_self_approval": 0,
            },
            {
                "state": "Management Approval",
                "action": "Approve",
                "next_state": "Approved",
                "allowed": "Management Approver",
                "allow_self_approval": 0,
            },
            {
                "state": "Management Approval",
                "action": "Reject",
                "next_state": "Rejected",
                "allowed": "Management Approver",
                "allow_self_approval": 0,
            },
            {
                "state": "Approved",
                "action": "Mark Executed",
                "next_state": "Completed",
                "allowed": "Lease Administrator",
                "allow_self_approval": 1,
            },
        ],
    )
    workflow.save(ignore_permissions=True)


def setup_reminder_defaults():
    policy_name = "Default Lease Expiry Policy"
    if not frappe.db.exists("Reminder Policy", policy_name):
        policy = frappe.get_doc(
            {
                "doctype": "Reminder Policy",
                "policy_name": policy_name,
                "enabled": 1,
                "overdue_cadence_days": 7,
                "email_enabled": 1,
                "system_notification_enabled": 1,
                "subject_template": "Lease {{ lease.name }} expires in {{ days_to_expiry }} day(s)",
                "message_template": (
                    "<p>{{ lease.lease_title }} for {{ property_name }} ends on "
                    "{{ lease.end_date }}.</p><p>Responsible officer: "
                    "{{ lease.responsible_officer }}. Renewal status: "
                    "{{ lease.renewal_status }}.</p><p><a href=\"{{ lease_url }}\">"
                    "Open lease</a></p>"
                ),
            }
        )
        for days in (90, 60, 30, 14, 7, 0):
            policy.append(
                "thresholds",
                {
                    "days_before_expiry": days,
                    "label": "Expiry Day" if days == 0 else f"{days} Days Before Expiry",
                    "enabled": 1,
                },
            )
        policy.append(
            "recipients",
            {
                "recipient_type": "Lease User Field",
                "recipient_value": "responsible_officer",
                "scope": "All",
            },
        )
        policy.append(
            "recipients",
            {
                "recipient_type": "Lease User Field",
                "recipient_value": "backup_officer",
                "scope": "Overdue",
            },
        )
        policy.insert(ignore_permissions=True)

    settings = frappe.get_single("Rent Renewal Settings")
    settings.default_reminder_policy = policy_name
    settings.expiring_soon_threshold = settings.expiring_soon_threshold or 90
    settings.reminder_retry_limit = settings.reminder_retry_limit or 2
    settings.save(ignore_permissions=True)
