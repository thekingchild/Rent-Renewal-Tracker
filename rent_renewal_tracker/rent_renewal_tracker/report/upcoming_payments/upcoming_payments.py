import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    from_date = getdate(filters.from_date or today())
    to_date = getdate(filters.to_date or add_days(from_date, 90))
    if to_date < from_date:
        frappe.throw(_("To Date cannot be earlier than From Date."))

    query_filters = {"due_date": ["between", [from_date, to_date]], "docstatus": ["<", 2]}
    if filters.schedule_status:
        query_filters["schedule_status"] = filters.schedule_status
    else:
        query_filters["schedule_status"] = ["not in", ["Paid", "Waived", "Cancelled"]]
    if filters.currency:
        query_filters["currency"] = filters.currency
    if filters.responsible_department:
        permitted_leases = frappe.get_list(
            "Lease",
            filters={"responsible_department": filters.responsible_department},
            pluck="name",
        )
        if not permitted_leases:
            return get_columns(), []
        query_filters["lease"] = ["in", permitted_leases]

    rows = frappe.get_list(
        "Rent Schedule",
        filters=query_filters,
        fields=[
            "name",
            "lease",
            "description",
            "period_from",
            "period_to",
            "due_date",
            "currency",
            "base_rent",
            "service_charge",
            "tax",
            "total_due",
            "payment_status",
            "schedule_status",
        ],
        order_by="due_date asc",
    )
    for row in rows:
        row.days_until_due = date_diff(row.due_date, today())
    return get_columns(), rows


def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Schedule"),
            "fieldtype": "Link",
            "options": "Rent Schedule",
            "width": 155,
        },
        {
            "fieldname": "lease",
            "label": _("Lease"),
            "fieldtype": "Link",
            "options": "Lease",
            "width": 150,
        },
        {"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 180},
        {"fieldname": "period_from", "label": _("Period From"), "fieldtype": "Date", "width": 105},
        {"fieldname": "period_to", "label": _("Period To"), "fieldtype": "Date", "width": 105},
        {"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 105},
        {"fieldname": "days_until_due", "label": _("Days"), "fieldtype": "Int", "width": 70},
        {
            "fieldname": "currency",
            "label": _("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80,
        },
        {
            "fieldname": "base_rent",
            "label": _("Base Rent"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 115,
        },
        {
            "fieldname": "service_charge",
            "label": _("Service Charge"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {"fieldname": "tax", "label": _("Tax"), "fieldtype": "Currency", "options": "currency", "width": 95},
        {
            "fieldname": "total_due",
            "label": _("Total Due"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {"fieldname": "schedule_status", "label": _("Status"), "fieldtype": "Data", "width": 100},
    ]
