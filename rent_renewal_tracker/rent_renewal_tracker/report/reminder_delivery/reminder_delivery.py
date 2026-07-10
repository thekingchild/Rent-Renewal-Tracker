from collections import Counter

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    from_date = getdate(filters.from_date or add_days(today(), -30))
    to_date = getdate(filters.to_date or today())
    if to_date < from_date:
        frappe.throw(_("To Date cannot be earlier than From Date."))

    query_filters = {"scheduled_date": ["between", [from_date, to_date]]}
    for fieldname in ("status", "channel", "policy", "lease"):
        if filters.get(fieldname):
            query_filters[fieldname] = filters[fieldname]

    rows = frappe.get_list(
        "Reminder Log",
        filters=query_filters,
        fields=[
            "name",
            "lease",
            "renewal_request",
            "policy",
            "threshold",
            "threshold_key",
            "scheduled_date",
            "channel",
            "recipient",
            "status",
            "sent_at",
            "retry_count",
            "error_summary",
        ],
        order_by="creation desc",
    )
    status_counts = Counter(row.status for row in rows)
    total = len(rows)
    sent = status_counts.get("Sent", 0)
    delivery_rate = flt(sent * 100 / total, 2) if total else 0
    chart = {
        "data": {
            "labels": ["Queued", "Sent", "Failed"],
            "datasets": [
                {
                    "name": _("Attempts"),
                    "values": [
                        status_counts.get(status, 0)
                        for status in ("Queued", "Sent", "Failed")
                    ],
                }
            ],
        },
        "type": "donut",
    }
    summary = [
        {"value": total, "label": _("Attempts"), "datatype": "Int"},
        {"value": sent, "label": _("Sent"), "datatype": "Int", "indicator": "green"},
        {
            "value": status_counts.get("Failed", 0),
            "label": _("Failed"),
            "datatype": "Int",
            "indicator": "red",
        },
        {
            "value": delivery_rate,
            "label": _("Delivery Rate"),
            "datatype": "Percent",
            "indicator": "green" if delivery_rate >= 99 else "orange",
        },
    ]
    return get_columns(), rows, None, chart, summary


def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Log"),
            "fieldtype": "Link",
            "options": "Reminder Log",
            "width": 155,
        },
        {
            "fieldname": "lease",
            "label": _("Lease"),
            "fieldtype": "Link",
            "options": "Lease",
            "width": 145,
        },
        {
            "fieldname": "renewal_request",
            "label": _("Renewal"),
            "fieldtype": "Link",
            "options": "Renewal Request",
            "width": 150,
        },
        {
            "fieldname": "policy",
            "label": _("Policy"),
            "fieldtype": "Link",
            "options": "Reminder Policy",
            "width": 175,
        },
        {"fieldname": "threshold", "label": _("Threshold"), "fieldtype": "Int", "width": 80},
        {
            "fieldname": "threshold_key",
            "label": _("Threshold Key"),
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "fieldname": "scheduled_date",
            "label": _("Scheduled"),
            "fieldtype": "Date",
            "width": 105,
        },
        {"fieldname": "channel", "label": _("Channel"), "fieldtype": "Data", "width": 125},
        {"fieldname": "recipient", "label": _("Recipient"), "fieldtype": "Data", "width": 190},
        {"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 85},
        {"fieldname": "sent_at", "label": _("Sent At"), "fieldtype": "Datetime", "width": 145},
        {"fieldname": "retry_count", "label": _("Retries"), "fieldtype": "Int", "width": 70},
        {"fieldname": "error_summary", "label": _("Error"), "fieldtype": "Small Text", "width": 220},
    ]
