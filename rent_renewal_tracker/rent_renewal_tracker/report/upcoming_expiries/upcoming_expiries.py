import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    from_date = getdate(filters.from_date or today())
    to_date = getdate(filters.to_date or add_days(from_date, 90))
    if to_date < from_date:
        frappe.throw(_("To Date cannot be earlier than From Date."))

    query_filters = {
        "end_date": ["between", [from_date, to_date]],
        "lease_status": ["not in", ["Draft", "Renewed", "Terminated"]],
    }
    for fieldname in ("responsible_department", "responsible_officer", "lease_status"):
        if filters.get(fieldname):
            query_filters[fieldname] = filters[fieldname]

    rows = frappe.get_list(
        "Lease",
        filters=query_filters,
        fields=[
            "name",
            "lease_title",
            "property",
            "landlord",
            "responsible_department",
            "responsible_officer",
            "end_date",
            "lease_status",
            "renewal_status",
            "next_action_date",
        ],
        order_by="end_date asc",
    )
    for row in rows:
        row.days_to_expiry = date_diff(row.end_date, today())

    buckets = ((0, 30), (31, 60), (61, 90))
    values = [
        sum(1 for row in rows if lower <= row.days_to_expiry <= upper)
        for lower, upper in buckets
    ]
    chart = {
        "data": {
            "labels": [_("0-30 Days"), _("31-60 Days"), _("61-90 Days")],
            "datasets": [{"name": _("Leases"), "values": values}],
        },
        "type": "bar",
        "fieldtype": "Int",
        "colors": ["#d97706"],
    }
    message = None if rows else _("No leases expire within the selected date range.")
    return get_columns(), rows, message, chart


def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Lease"),
            "fieldtype": "Link",
            "options": "Lease",
            "width": 150,
        },
        {"fieldname": "lease_title", "label": _("Title"), "fieldtype": "Data", "width": 220},
        {
            "fieldname": "property",
            "label": _("Property"),
            "fieldtype": "Link",
            "options": "Property",
            "width": 170,
        },
        {
            "fieldname": "landlord",
            "label": _("Landlord"),
            "fieldtype": "Link",
            "options": "Landlord",
            "width": 160,
        },
        {
            "fieldname": "responsible_department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Lease Department",
            "width": 150,
        },
        {
            "fieldname": "responsible_officer",
            "label": _("Officer"),
            "fieldtype": "Link",
            "options": "User",
            "width": 170,
        },
        {"fieldname": "end_date", "label": _("End Date"), "fieldtype": "Date", "width": 105},
        {"fieldname": "days_to_expiry", "label": _("Days"), "fieldtype": "Int", "width": 75},
        {"fieldname": "lease_status", "label": _("Lease Status"), "fieldtype": "Data", "width": 135},
        {
            "fieldname": "renewal_status",
            "label": _("Renewal Status"),
            "fieldtype": "Data",
            "width": 135,
        },
        {
            "fieldname": "next_action_date",
            "label": _("Next Action"),
            "fieldtype": "Date",
            "width": 105,
        },
    ]
