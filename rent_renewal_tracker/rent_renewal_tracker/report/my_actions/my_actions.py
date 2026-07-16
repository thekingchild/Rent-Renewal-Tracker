from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, today


PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    rows = []
    rows.extend(get_renewal_actions())
    rows.extend(get_overdue_payment_actions())
    rows.extend(get_expiry_actions())
    rows.extend(get_document_expiry_actions())
    rows.extend(get_failed_reminder_actions())

    if filters.action_type:
        rows = [row for row in rows if row.action_type == filters.action_type]
    if filters.priority:
        rows = [row for row in rows if row.priority == filters.priority]
    rows.sort(key=lambda row: (PRIORITY_ORDER[row.priority], row.due_date or today(), row.reference_name))

    message = None if rows else _("You have no actions matching the selected filters.")
    return get_columns(), rows, message


def get_renewal_actions():
    roles = sorted(
        set(frappe.get_roles())
        & {
            "Responsible Officer",
            "Department Head",
            "Finance Approver",
            "Legal Approver",
            "Management Approver",
            "Lease Administrator",
        }
    )
    if not roles:
        return []
    rows = frappe.get_list(
        "Renewal Request",
        filters={
            "current_approver_role": ["in", roles],
            "workflow_state": ["not in", ["Completed", "Rejected"]],
        },
        fields=["name", "lease", "workflow_state", "current_approver_role", "requested_on"],
        order_by="requested_on asc",
        limit_page_length=0,
    )
    actions = []
    for row in rows:
        age = date_diff(today(), row.requested_on) if row.requested_on else 0
        actions.append(
            frappe._dict(
                action_type="Renewal Approval",
                priority="High" if age > 7 else "Medium",
                reference_doctype="Renewal Request",
                reference_name=row.name,
                lease=row.lease,
                due_date=row.requested_on,
                age_days=age,
                assigned_to=row.current_approver_role,
                description=_("Review renewal in {0}").format(row.workflow_state),
            )
        )
    return actions


def get_overdue_payment_actions():
    rows = frappe.get_list(
        "Rent Schedule",
        filters={
            "due_date": ["<", today()],
            "payment_status": ["not in", ["Paid", "Waived"]],
            "docstatus": ["<", 2],
        },
        fields=["name", "lease", "description", "due_date", "currency", "total_due"],
        order_by="due_date asc",
        limit_page_length=0,
    )
    return [
        frappe._dict(
            action_type="Overdue Payment",
            priority="Critical" if date_diff(today(), row.due_date) > 30 else "High",
            reference_doctype="Rent Schedule",
            reference_name=row.name,
            lease=row.lease,
            due_date=row.due_date,
            age_days=date_diff(today(), row.due_date),
            assigned_to=None,
            description=_("{0} {1:,.2f} overdue: {2}").format(
                row.currency or "", row.total_due or 0, row.description or row.name
            ),
        )
        for row in rows
    ]


def get_expiry_actions():
    user = frappe.session.user
    rows = frappe.get_list(
        "Lease",
        filters={
            "end_date": ["between", [today(), add_days(today(), 90)]],
            "lease_status": ["not in", ["Draft", "Renewed", "Terminated"]],
        },
        or_filters=[
            ["responsible_officer", "=", user],
            ["contract_owner", "=", user],
            ["backup_officer", "=", user],
        ],
        fields=["name", "lease_title", "end_date", "responsible_officer"],
        order_by="end_date asc",
        limit_page_length=0,
    )
    actions = []
    for row in rows:
        days = date_diff(row.end_date, today())
        actions.append(
            frappe._dict(
                action_type="Lease Expiry",
                priority="High" if days <= 30 else "Medium" if days <= 60 else "Low",
                reference_doctype="Lease",
                reference_name=row.name,
                lease=row.name,
                due_date=row.end_date,
                age_days=days,
                assigned_to=row.responsible_officer,
                description=_("{0} expires in {1} day(s)").format(row.lease_title, days),
            )
        )
    return actions


def get_failed_reminder_actions():
    rows = frappe.get_list(
        "Reminder Log",
        filters={"status": "Failed"},
        fields=["name", "lease", "scheduled_date", "error_summary"],
        order_by="creation desc",
        limit_page_length=0,
    )
    return [
        frappe._dict(
            action_type="Failed Reminder",
            priority="Critical",
            reference_doctype="Reminder Log",
            reference_name=row.name,
            lease=row.lease,
            due_date=row.scheduled_date,
            age_days=date_diff(today(), row.scheduled_date) if row.scheduled_date else 0,
            assigned_to=None,
            description=row.error_summary or _("Reminder delivery failed"),
        )
        for row in rows
    ]


def get_document_expiry_actions():
    rows = frappe.get_list(
        "Lease Document",
        filters={
            "document_status": ["in", ["Expiring Soon", "Expired"]],
            "docstatus": ["<", 2],
        },
        fields=["name", "lease", "title", "expiry_date", "document_status"],
        order_by="expiry_date asc",
        limit_page_length=0,
    )
    return [
        frappe._dict(
            action_type="Document Expiry",
            priority="Critical" if row.document_status == "Expired" else "High",
            reference_doctype="Lease Document",
            reference_name=row.name,
            lease=row.lease,
            due_date=row.expiry_date,
            age_days=date_diff(row.expiry_date, today()) if row.expiry_date else 0,
            assigned_to=None,
            description=_("{0}: {1}").format(row.title, row.document_status),
        )
        for row in rows
    ]


def get_columns():
    return [
        {"fieldname": "priority", "label": _("Priority"), "fieldtype": "Data", "width": 85},
        {"fieldname": "action_type", "label": _("Action"), "fieldtype": "Data", "width": 135},
        {
            "fieldname": "reference_doctype",
            "label": _("Record Type"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 130,
        },
        {
            "fieldname": "reference_name",
            "label": _("Record"),
            "fieldtype": "Dynamic Link",
            "options": "reference_doctype",
            "width": 160,
        },
        {"fieldname": "lease", "label": _("Lease"), "fieldtype": "Link", "options": "Lease", "width": 150},
        {"fieldname": "due_date", "label": _("Due / Event Date"), "fieldtype": "Date", "width": 120},
        {"fieldname": "age_days", "label": _("Days"), "fieldtype": "Int", "width": 70},
        {"fieldname": "assigned_to", "label": _("Pending With"), "fieldtype": "Data", "width": 165},
        {"fieldname": "description", "label": _("What Needs Attention"), "fieldtype": "Data", "width": 320},
    ]
