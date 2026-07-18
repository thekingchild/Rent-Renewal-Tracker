import frappe
from frappe import _


def execute(filters=None):
    settings = frappe.get_single("Rent Renewal Settings")
    checks = [
        check(
            "Lease Departments",
            frappe.db.count("Lease Department") > 0,
            "Lease Department",
            _("Create at least one responsible department."),
        ),
        check(
            "Assigned Users",
            users_are_assigned(),
            "User",
            _("Assign application roles to enabled users."),
        ),
        check(
            "Reminder Policy",
            settings.default_reminder_policy
            and frappe.db.exists("Reminder Policy", settings.default_reminder_policy),
            "Reminder Policy",
            _("Select an enabled default reminder policy."),
        ),
        check(
            "Outgoing Email",
            frappe.db.exists("Email Account", {"enable_outgoing": 1}),
            "Email Account",
            _("Configure an outgoing email account for reminders and digests."),
        ),
        check(
            "Properties",
            frappe.db.count("Property") > 0,
            "Property",
            _("Create or import the property register."),
        ),
        check("Leases", frappe.db.count("Lease") > 0, "Lease", _("Create or import lease records.")),
        check(
            "Lease Overlap Review",
            frappe.db.count("Lease", {"overlap_review_required": 1}) == 0,
            "Lease",
            _("Resolve flagged same-property Lease periods before creating or changing terms."),
        ),
    ]
    completed = sum(row.ready for row in checks)
    summary = [
        {"value": completed, "label": _("Ready"), "datatype": "Int", "indicator": "green"},
        {"value": len(checks) - completed, "label": _("Remaining"), "datatype": "Int", "indicator": "orange"},
        {"value": completed * 100 / len(checks), "label": _("Setup Complete"), "datatype": "Percent"},
    ]
    message = (
        None
        if completed == len(checks)
        else _("Complete the remaining items before relying on automated reminders.")
    )
    return get_columns(), checks, message, None, summary


def check(item, ready, doctype, guidance):
    route = doctype.lower().replace(" ", "-")
    return frappe._dict(
        item=_(item),
        ready=bool(ready),
        status=_("Ready") if ready else _("Action Required"),
        setup_link=f'<a href="/desk/{route}">{_("Open {0}").format(doctype)}</a>',
        guidance=guidance,
    )


def users_are_assigned():
    return bool(
        frappe.db.exists(
            "Has Role",
            {
                "role": [
                    "in",
                    ["Lease Administrator", "Responsible Officer", "Department Head"],
                ],
                "parenttype": "User",
            },
        )
    )


def get_columns():
    return [
        {"fieldname": "item", "label": _("Setup Item"), "fieldtype": "Data", "width": 180},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 125},
        {"fieldname": "setup_link", "label": _("Open"), "fieldtype": "HTML", "width": 170},
        {"fieldname": "guidance", "label": _("Next Step"), "fieldtype": "Data", "width": 420},
    ]
