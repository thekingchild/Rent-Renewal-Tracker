from __future__ import annotations

import hashlib
from dataclasses import dataclass

import frappe
from frappe.utils import (
    add_days,
    date_diff,
    escape_html,
    get_url_to_form,
    getdate,
    now_datetime,
    today,
)

from rent_renewal_tracker.reminder_rules import determine_due_threshold


EXCLUDED_LEASE_STATUSES = {"Draft", "Renewed", "Terminated"}
EXCLUDED_RENEWAL_STATUSES = {"Completed", "Not Renewing"}


@dataclass(frozen=True)
class ResolvedRecipient:
    user: str | None
    email: str | None


def process_due_reminders(as_of_date=None, queue_deliveries=True):
    """Reserve and queue every reminder due for the site's current business date."""
    as_of_date = getdate(as_of_date or today())
    settings = frappe.get_single("Rent Renewal Settings")
    if not settings.default_reminder_policy:
        return []

    leases = frappe.get_all(
        "Lease",
        filters={
            "lease_status": ["not in", list(EXCLUDED_LEASE_STATUSES)],
            "renewal_status": ["not in", list(EXCLUDED_RENEWAL_STATUSES)],
            "end_date": ["is", "set"],
        },
        fields=[
            "name",
            "lease_title",
            "property",
            "end_date",
            "responsible_officer",
            "backup_officer",
            "contract_owner",
            "renewal_status",
            "last_renewal_request",
            "reminder_policy",
        ],
    )
    policy_cache = {}
    queued_logs = frappe.get_all(
        "Reminder Log",
        filters={"status": "Queued", "scheduled_date": ["<=", as_of_date]},
        pluck="name",
    )

    for lease in leases:
        policy_name = lease.reminder_policy or settings.default_reminder_policy
        policy = policy_cache.get(policy_name)
        if policy is None:
            policy = frappe.get_doc("Reminder Policy", policy_name)
            policy_cache[policy_name] = policy
        if not policy.enabled:
            continue

        renewal_cycle = lease.last_renewal_request or "Initial"
        existing_keys = frappe.get_all(
            "Reminder Log",
            filters={
                "lease": lease.name,
                "renewal_cycle": renewal_cycle,
                "policy": policy.name,
            },
            pluck="threshold_key",
        )
        days_to_expiry = date_diff(lease.end_date, as_of_date)
        due = determine_due_threshold(policy, days_to_expiry, existing_keys)
        if not due:
            continue
        threshold, threshold_key = due

        created_renewal = maybe_auto_create_renewal(lease, policy, threshold, settings)
        if created_renewal:
            renewal_cycle = created_renewal.name
            lease.last_renewal_request = created_renewal.name
        recipients = resolve_recipients(policy, lease, threshold)
        for recipient in recipients:
            if policy.email_enabled and recipient.email:
                log_name = reserve_reminder(
                    lease,
                    policy,
                    renewal_cycle,
                    threshold,
                    threshold_key,
                    as_of_date,
                    "Email",
                    recipient.email,
                    recipient.user,
                )
                if log_name:
                    queued_logs.append(log_name)
            if policy.system_notification_enabled and recipient.user:
                log_name = reserve_reminder(
                    lease,
                    policy,
                    renewal_cycle,
                    threshold,
                    threshold_key,
                    as_of_date,
                    "System Notification",
                    recipient.user,
                    recipient.user,
                )
                if log_name:
                    queued_logs.append(log_name)

    if queue_deliveries:
        for log_name in queued_logs:
            frappe.enqueue(
                "rent_renewal_tracker.reminders.deliver_reminder",
                queue="short",
                enqueue_after_commit=True,
                job_id=f"rent-reminder-{log_name}",
                deduplicate=True,
                log_name=log_name,
            )
    return queued_logs


def reserve_reminder(
    lease,
    policy,
    renewal_cycle,
    threshold,
    threshold_key,
    scheduled_date,
    channel,
    recipient,
    recipient_user=None,
):
    key_source = "|".join(
        (lease.name, renewal_cycle, threshold_key, channel, recipient.strip().lower())
    )
    deduplication_key = hashlib.sha256(key_source.encode()).hexdigest()
    try:
        log = frappe.get_doc(
            {
                "doctype": "Reminder Log",
                "lease": lease.name,
                "renewal_request": lease.last_renewal_request,
                "policy": policy.name,
                "renewal_cycle": renewal_cycle,
                "threshold": threshold,
                "threshold_key": threshold_key,
                "scheduled_date": scheduled_date,
                "channel": channel,
                "recipient": recipient,
                "recipient_user": recipient_user,
                "status": "Queued",
                "deduplication_key": deduplication_key,
            }
        ).insert(ignore_permissions=True)
    except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
        return None
    return log.name


def resolve_recipients(policy, lease, threshold):
    event_scope = "Pre-Expiry" if threshold > 0 else "Expiry" if threshold == 0 else "Overdue"
    recipients = set()

    for rule in policy.recipients:
        if rule.scope not in {"All", event_scope}:
            continue
        value = rule.recipient_value.strip()
        if rule.recipient_type == "Lease User Field":
            user = lease.get(value)
            if user:
                add_user_recipient(recipients, user)
        elif rule.recipient_type == "Lease Contact Type":
            contacts = frappe.get_all(
                "Lease Contact",
                filters={
                    "parent": lease.name,
                    "parenttype": "Lease",
                    "parentfield": "lease_contacts",
                    "contact_type": value,
                    "receives_reminders": 1,
                },
                pluck="email",
            )
            for email in contacts:
                if email:
                    recipients.add((None, email.lower()))
        elif rule.recipient_type == "Role":
            users = frappe.get_all(
                "Has Role",
                filters={"role": value, "parenttype": "User"},
                pluck="parent",
            )
            for user in users:
                add_user_recipient(recipients, user)
        elif rule.recipient_type == "Explicit User":
            add_user_recipient(recipients, value)
        elif rule.recipient_type == "Email":
            recipients.add((None, value.lower()))

    ordered = sorted(recipients, key=lambda item: (item[0] or "", item[1] or ""))
    return [ResolvedRecipient(user=user, email=email) for user, email in ordered]


def add_user_recipient(recipients, user):
    user_record = frappe.db.get_value("User", user, ["email", "enabled"], as_dict=True)
    if user_record and user_record.enabled:
        recipients.add((user, (user_record.email or user).lower()))


def maybe_auto_create_renewal(lease, policy, threshold, settings):
    enabled_thresholds = [row.days_before_expiry for row in policy.thresholds if row.enabled]
    if (
        not settings.auto_create_renewal_request
        or not enabled_thresholds
        or threshold != max(enabled_thresholds)
        or lease.last_renewal_request
    ):
        return None

    lease_doc = frappe.get_doc("Lease", lease.name)
    tenure_days = max(1, date_diff(lease_doc.end_date, lease_doc.start_date))
    proposed_start = add_days(lease_doc.end_date, 1)
    return frappe.get_doc(
        {
            "doctype": "Renewal Request",
            "lease": lease.name,
            "proposed_end_date": add_days(proposed_start, tenure_days),
            "recommendation": "Renegotiate",
            "business_justification": "Automatically created at the first reminder threshold.",
        }
    ).insert(ignore_permissions=True)


def deliver_reminder(log_name):
    """Deliver one reserved notification and finalize its audit record."""
    log = frappe.get_doc("Reminder Log", log_name)
    if log.status not in {"Queued", "Failed"}:
        return

    # Claim before performing an external side effect. A duplicate worker will
    # observe Sending and exit instead of sending a second message.
    frappe.db.sql(
        "update `tabReminder Log` set status='Sending' where name=%s and status in ('Queued','Failed')",
        log.name,
    )
    if frappe.db._cursor.rowcount != 1:
        return
    log.reload()
    if log.status != "Sending":
        return

    settings = frappe.get_single("Rent Renewal Settings")
    lease = frappe.get_doc("Lease", log.lease)
    policy = frappe.get_doc("Reminder Policy", log.policy)
    property_name = frappe.db.get_value("Property", lease.property, "property_name")
    context = {
        "lease": lease,
        "property_name": property_name,
        "days_to_expiry": date_diff(lease.end_date, log.scheduled_date),
        "lease_url": get_url_to_form("Lease", lease.name),
    }
    subject = frappe.render_template(policy.subject_template, context)
    message = frappe.render_template(policy.message_template, context)
    retry_limit = max(0, settings.reminder_retry_limit or 0)
    last_error = None
    last_traceback = None
    message_id = None

    attempt = (log.retry_count or 0) + 1
    try:
        if log.channel == "Email":
            result = frappe.sendmail(
                recipients=[log.recipient], sender=settings.email_sender or None,
                subject=subject, message=message, reference_doctype="Lease",
                reference_name=lease.name, now=True,
            )
            message_id = str(result)[:140] if result else None
        else:
            notification = frappe.get_doc({
                "doctype": "Notification Log", "subject": subject,
                "email_content": message, "for_user": log.recipient_user,
                "type": "Alert", "document_type": "Lease",
                "document_name": lease.name, "from_user": "Administrator",
            }).insert(ignore_permissions=True)
            message_id = notification.name
        finalize_log(log, "Sent", attempt, message_id=message_id)
        update_lease_reminder_dates(lease, policy, log.threshold)
        return
    except Exception as exc:
        last_error = exc
        last_traceback = frappe.get_traceback()

    finalize_log(log, "Failed", attempt, error_summary=str(last_error)[:500])
    frappe.log_error(
        title=f"Lease reminder delivery failed: {log.name}",
        message=last_traceback,
    )
    notify_error_recipients(settings, log, last_error)
    if attempt <= retry_limit:
        frappe.enqueue(
            "rent_renewal_tracker.reminders.deliver_reminder",
            queue="short",
            enqueue_after_commit=True,
            job_id=f"rent-reminder-retry-{log.name}-{attempt}",
            deduplicate=True,
            log_name=log.name,
        )


def finalize_log(log, status, retry_count, message_id=None, error_summary=None):
    log.flags.delivery_update = True
    log.status = status
    log.retry_count = retry_count
    log.message_id = message_id
    log.error_summary = error_summary
    log.sent_at = now_datetime() if status == "Sent" else None
    log.save(ignore_permissions=True)


def notify_error_recipients(settings, log, error):
    recipients = settings.get_error_recipient_emails()
    if not recipients:
        return
    try:
        frappe.sendmail(
            recipients=recipients,
            sender=settings.email_sender or None,
            subject=f"Lease reminder delivery failed: {log.name}",
            message=(
                f"Reminder {log.name} for lease {log.lease} failed after "
                f"{log.retry_count} retries.<br><br>{escape_html(str(error))}"
            ),
            now=True,
        )
    except Exception:
        frappe.log_error(
            title=f"Could not send reminder failure alert: {log.name}",
            message=frappe.get_traceback(),
        )


def update_lease_reminder_dates(lease, policy, threshold):
    enabled = sorted(
        {row.days_before_expiry for row in policy.thresholds if row.enabled},
        reverse=True,
    )
    lower_thresholds = [days for days in enabled if days < threshold]
    if lower_thresholds:
        next_date = add_days(lease.end_date, -max(lower_thresholds))
    elif threshold >= 0:
        next_date = add_days(lease.end_date, 1)
    else:
        next_date = add_days(today(), max(1, policy.overdue_cadence_days or 1))
    frappe.db.set_value(
        "Lease",
        lease.name,
        {"last_reminder_date": today(), "next_reminder_date": next_date},
        update_modified=False,
    )
