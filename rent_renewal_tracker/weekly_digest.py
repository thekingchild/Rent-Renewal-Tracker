from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, escape_html, flt, formatdate, get_url, today


def send_weekly_management_digest():
    settings = frappe.get_single("Rent Renewal Settings")
    if not settings.weekly_digest_enabled:
        return None

    recipients = settings.get_weekly_digest_recipient_emails()
    if not recipients:
        frappe.log_error(
            title="Rent renewal weekly digest has no recipients",
            message="Configure Weekly Digest Recipients in Rent Renewal Settings.",
        )
        return None

    context = get_digest_context()
    frappe.sendmail(
        recipients=recipients,
        sender=settings.email_sender or None,
        subject=_("Weekly Lease Management Summary - {0}").format(formatdate(today())),
        message=render_digest(context),
        reference_doctype="Rent Renewal Settings",
        reference_name="Rent Renewal Settings",
    )
    return context


def get_digest_context():
    active_filter = ["not in", ["Draft", "Renewed", "Terminated"]]
    expiring = frappe.get_all(
        "Lease",
        filters={
            "end_date": ["between", [today(), add_days(today(), 90)]],
            "lease_status": active_filter,
        },
        fields=["name", "lease_title", "end_date"],
        order_by="end_date asc",
    )
    delayed_renewals = frappe.get_all(
        "Renewal Request",
        filters={
            "workflow_state": [
                "in",
                [
                    "Department Review",
                    "Finance Review",
                    "Legal Review",
                    "Management Approval",
                    "Approved",
                ],
            ],
            "requested_on": ["<", add_days(today(), -7)],
        },
        fields=["name", "lease", "workflow_state", "current_approver_role", "requested_on"],
        order_by="requested_on asc",
    )
    overdue_payments = frappe.get_all(
        "Rent Schedule",
        filters={
            "due_date": ["<", today()],
            "payment_status": ["not in", ["Paid", "Waived"]],
            "docstatus": ["<", 2],
        },
        fields=["name", "lease", "due_date", "currency", "total_due"],
        order_by="due_date asc",
    )
    failed_reminders = frappe.get_all(
        "Reminder Log",
        filters={"status": "Failed"},
        fields=["name", "lease", "scheduled_date", "error_summary"],
        order_by="creation desc",
        limit=20,
    )
    exposure = defaultdict(float)
    for row in frappe.get_all(
        "Lease",
        filters={"lease_status": active_filter},
        fields=["currency", "annual_rent"],
    ):
        exposure[row.currency or _("Unspecified")] += flt(row.annual_rent)

    return frappe._dict(
        expiring=expiring,
        delayed_renewals=delayed_renewals,
        overdue_payments=overdue_payments,
        failed_reminders=failed_reminders,
        exposure=dict(sorted(exposure.items())),
    )


def render_digest(context):
    base_url = get_url()
    metrics = (
        (_("Expiring within 90 days"), len(context.expiring)),
        (_("Delayed approvals"), len(context.delayed_renewals)),
        (_("Overdue payments"), len(context.overdue_payments)),
        (_("Failed reminders"), len(context.failed_reminders)),
    )
    metric_html = "".join(
        "<td style='padding:12px 18px;border:1px solid #dfe2e5'>"
        f"<strong>{value}</strong><br>{escape_html(label)}</td>"
        for label, value in metrics
    )
    exposure_html = "".join(
        f"<li>{escape_html(currency)} {amount:,.2f}</li>"
        for currency, amount in context.exposure.items()
    ) or f"<li>{_('No active lease exposure')}</li>"
    return (
        f"<p>{_('Here is the weekly lease management summary.')}</p>"
        f"<table style='border-collapse:collapse'><tr>{metric_html}</tr></table>"
        f"<h3>{_('Annual Rent Exposure')}</h3><ul>{exposure_html}</ul>"
        f"<p><a href='{base_url}/desk/query-report/My%20Actions'>{_('Open My Actions')}</a> | "
        f"<a href='{base_url}/desk/query-report/Renewal%20Pipeline'>{_('Open Renewal Pipeline')}</a></p>"
    )
