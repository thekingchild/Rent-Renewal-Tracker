import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    query_filters = {"lease_status": ["not in", ["Draft", "Renewed", "Terminated"]]}
    for fieldname in ("currency", "responsible_department", "region", "lease_status"):
        if filters.get(fieldname):
            query_filters[fieldname] = filters[fieldname]

    rows = frappe.get_list(
        "Lease",
        filters=query_filters,
        fields=[
            "name",
            "lease_title",
            "property",
            "region",
            "landlord",
            "responsible_department",
            "currency",
            "monthly_rent",
            "annual_rent",
            "annual_service_charge",
            "annual_tax",
            "total_annual_occupancy_cost",
            "lease_status",
            "end_date",
        ],
        order_by="currency asc, annual_rent desc",
    )
    message = None
    if not filters.currency and len({row.currency for row in rows}) > 1:
        message = _("Currencies are shown separately and are not combined into one total.")
    return get_columns(), rows, message
def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Lease"),
            "fieldtype": "Link",
            "options": "Lease",
            "width": 150,
        },
        {"fieldname": "lease_title", "label": _("Title"), "fieldtype": "Data", "width": 210},
        {
            "fieldname": "property",
            "label": _("Property"),
            "fieldtype": "Link",
            "options": "Property",
            "width": 165,
        },
        {
            "fieldname": "landlord",
            "label": _("Landlord"),
            "fieldtype": "Link",
            "options": "Landlord",
            "width": 155,
        },
        {"fieldname": "region", "label": _("Region"), "fieldtype": "Data", "width": 105},
        {
            "fieldname": "responsible_department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Lease Department",
            "width": 145,
        },
        {
            "fieldname": "currency",
            "label": _("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80,
        },
        {
            "fieldname": "monthly_rent",
            "label": _("Monthly Rent"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "fieldname": "annual_rent",
            "label": _("Annual Rent"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "fieldname": "annual_service_charge",
            "label": _("Service Charge"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "fieldname": "annual_tax",
            "label": _("Tax"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 95,
        },
        {
            "fieldname": "total_annual_occupancy_cost",
            "label": _("Total Annual Cost"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 145,
        },
        {"fieldname": "lease_status", "label": _("Status"), "fieldtype": "Data", "width": 125},
        {"fieldname": "end_date", "label": _("End Date"), "fieldtype": "Date", "width": 105},
    ]
