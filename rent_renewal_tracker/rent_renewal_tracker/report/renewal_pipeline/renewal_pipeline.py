from collections import Counter

import frappe
from frappe import _
from frappe.utils import date_diff, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    lease_filters = {}
    if filters.responsible_department:
        lease_filters["responsible_department"] = filters.responsible_department
    permitted_leases = frappe.get_list("Lease", filters=lease_filters, pluck="name")
    if not permitted_leases:
        return get_columns(), []

    query_filters = {"lease": ["in", permitted_leases]}
    for fieldname in ("workflow_state", "recommendation"):
        if filters.get(fieldname):
            query_filters[fieldname] = filters[fieldname]

    rows = frappe.get_list(
        "Renewal Request",
        filters=query_filters,
        fields=[
            "name",
            "lease",
            "renewal_sequence",
            "workflow_state",
            "current_approver_role",
            "recommendation",
            "requested_by",
            "requested_on",
            "proposed_start_date",
            "proposed_end_date",
            "proposed_currency",
            "proposed_annual_rent",
        ],
        order_by="creation desc",
    )
    for row in rows:
        row.age_days = date_diff(today(), row.requested_on) if row.requested_on else 0

    state_counts = Counter(row.workflow_state for row in rows)
    states = [
        "Draft",
        "Department Review",
        "Finance Review",
        "Legal Review",
        "Management Approval",
        "Approved",
    ]
    chart = {
        "data": {
            "labels": [_(state) for state in states],
            "datasets": [
                {"name": _("Renewals"), "values": [state_counts.get(state, 0) for state in states]}
            ],
        },
        "type": "bar",
        "colors": ["#2563eb"],
    }
    message = None if rows else _("No renewal requests match the selected filters.")
    return get_columns(), rows, message, chart


def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Renewal"),
            "fieldtype": "Link",
            "options": "Renewal Request",
            "width": 155,
        },
        {
            "fieldname": "lease",
            "label": _("Lease"),
            "fieldtype": "Link",
            "options": "Lease",
            "width": 150,
        },
        {"fieldname": "renewal_sequence", "label": _("Cycle"), "fieldtype": "Int", "width": 65},
        {"fieldname": "workflow_state", "label": _("Workflow State"), "fieldtype": "Data", "width": 165},
        {
            "fieldname": "current_approver_role",
            "label": _("Pending With"),
            "fieldtype": "Data",
            "width": 165,
        },
        {"fieldname": "age_days", "label": _("Age (Days)"), "fieldtype": "Int", "width": 90},
        {"fieldname": "recommendation", "label": _("Recommendation"), "fieldtype": "Data", "width": 120},
        {
            "fieldname": "requested_by",
            "label": _("Requested By"),
            "fieldtype": "Link",
            "options": "User",
            "width": 170,
        },
        {"fieldname": "requested_on", "label": _("Requested On"), "fieldtype": "Date", "width": 105},
        {
            "fieldname": "proposed_start_date",
            "label": _("Proposed Start"),
            "fieldtype": "Date",
            "width": 115,
        },
        {
            "fieldname": "proposed_end_date",
            "label": _("Proposed End"),
            "fieldtype": "Date",
            "width": 115,
        },
        {
            "fieldname": "proposed_currency",
            "label": _("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "width": 85,
        },
        {
            "fieldname": "proposed_annual_rent",
            "label": _("Proposed Annual Rent"),
            "fieldtype": "Currency",
            "options": "proposed_currency",
            "width": 145,
        },
    ]
