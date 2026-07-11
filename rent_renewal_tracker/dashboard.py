from __future__ import annotations

import frappe
from frappe.utils import add_days, flt, today


ACTIVE_LEASE_FILTER = ["not in", ["Draft", "Renewed", "Terminated"]]
OPEN_RENEWAL_STATES = [
    "Draft",
    "Department Review",
    "Finance Review",
    "Legal Review",
    "Management Approval",
    "Approved",
]


def _card(value, route, route_options=None, fieldtype="Int", currency=None):
    result = {
        "value": value,
        "fieldtype": fieldtype,
        "route": route,
        "route_options": route_options or {},
    }
    if currency:
        result["currency"] = currency
    return result


def _count(doctype, filters):
    return len(frappe.get_list(doctype, filters=filters, pluck="name", limit_page_length=0))


def _expiring_within(days):
    return _card(
        _count(
            "Lease",
            {
                "end_date": ["between", [today(), add_days(today(), days)]],
                "lease_status": ACTIVE_LEASE_FILTER,
            },
        ),
        ["query-report", "Upcoming Expiries"],
        {"from_date": today(), "to_date": add_days(today(), days)},
    )


@frappe.whitelist()
def leases_expiring_30_days():
    return _expiring_within(30)


@frappe.whitelist()
def leases_expiring_60_days():
    return _expiring_within(60)


@frappe.whitelist()
def leases_expiring_90_days():
    return _expiring_within(90)


@frappe.whitelist()
def renewals_waiting_for_me():
    approver_roles = sorted(set(frappe.get_roles()) & set(_renewal_approver_roles()))
    count = 0
    if approver_roles:
        count = _count(
            "Renewal Request",
            {
                "workflow_state": ["in", OPEN_RENEWAL_STATES],
                "current_approver_role": ["in", approver_roles],
            },
        )
    return _card(count, ["query-report", "My Actions"], {"action_type": "Renewal Approval"})


@frappe.whitelist()
def overdue_rent_obligations():
    return _card(
        _count(
            "Rent Schedule",
            {
                "due_date": ["<", today()],
                "payment_status": ["not in", ["Paid", "Waived"]],
                "docstatus": ["<", 2],
            },
        ),
        ["query-report", "My Actions"],
        {"action_type": "Overdue Payment"},
    )


@frappe.whitelist()
def failed_reminders():
    if not frappe.has_permission("Reminder Log", "read"):
        return _card(0, ["query-report", "My Actions"], {"action_type": "Failed Reminder"})
    return _card(
        _count("Reminder Log", {"status": "Failed"}),
        ["query-report", "My Actions"],
        {"action_type": "Failed Reminder"},
    )


@frappe.whitelist()
def annual_rent_exposure():
    settings = frappe.get_single("Rent Renewal Settings")
    currency = settings.default_currency or frappe.defaults.get_global_default("currency")
    filters = {"lease_status": ACTIVE_LEASE_FILTER}
    if not currency:
        currency_rows = frappe.get_list(
            "Lease",
            filters=filters,
            fields=["currency"],
            limit_page_length=0,
        )
        currencies = sorted({row.currency for row in currency_rows if row.currency})
        if len(currencies) == 1:
            currency = currencies[0]
        elif len(currencies) > 1:
            return _card(
                "Multiple currencies",
                ["query-report", "Rent Exposure"],
                fieldtype="Data",
            )
    if currency:
        filters["currency"] = currency
    rows = frappe.get_list("Lease", filters=filters, fields=["annual_rent"], limit_page_length=0)
    return _card(
        sum(flt(row.annual_rent) for row in rows),
        ["query-report", "Rent Exposure"],
        {"currency": currency} if currency else {},
        fieldtype="Currency",
        currency=currency,
    )


def _renewal_approver_roles():
    return (
        "Responsible Officer",
        "Department Head",
        "Finance Approver",
        "Legal Approver",
        "Management Approver",
        "Lease Administrator",
    )
