import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


LEASE_USER_FIELDS = {
    "responsible_officer",
    "backup_officer",
    "contract_owner",
}
LEASE_CONTACT_TYPES = {"Landlord", "Legal", "Facility", "Finance", "Escalation", "Other"}


class ReminderPolicy(Document):
    def validate(self):
        self.validate_thresholds()
        self.validate_recipients()
        if not self.email_enabled and not self.system_notification_enabled:
            frappe.throw(_("At least one reminder channel must be enabled."))
        self.validate_templates()

    def validate_templates(self):
        context = {
            "lease": frappe._dict(name="LEASE-TEST", lease_title="Test Lease", end_date="2099-12-31", responsible_officer="test@example.com", renewal_status="Not Started"),
            "property_name": "Test Property", "days_to_expiry": 90,
            "lease_url": "https://example.invalid",
        }
        for fieldname in ("subject_template", "message_template"):
            try:
                frappe.render_template(self.get(fieldname) or "", context)
            except Exception as exc:
                frappe.throw(_("Invalid {0}: {1}").format(self.meta.get_label(fieldname), exc))

    def validate_thresholds(self):
        enabled = [row.days_before_expiry for row in self.thresholds if row.enabled]
        if not enabled:
            frappe.throw(_("At least one reminder threshold must be enabled."))
        if any(days < 0 for days in enabled):
            frappe.throw(_("Reminder thresholds cannot be negative."))
        if len(enabled) != len(set(enabled)):
            frappe.throw(_("Enabled reminder thresholds must be unique."))
        if (self.overdue_cadence_days or 0) < 1:
            frappe.throw(_("Overdue Cadence must be at least one day."))

    def validate_recipients(self):
        if not self.recipients:
            frappe.throw(_("At least one reminder recipient rule is required."))

        for row in self.recipients:
            value = (row.recipient_value or "").strip()
            if row.recipient_type == "Lease User Field" and value not in LEASE_USER_FIELDS:
                frappe.throw(_("Unsupported Lease user field: {0}.").format(value))
            if row.recipient_type == "Lease Contact Type" and value not in LEASE_CONTACT_TYPES:
                frappe.throw(_("Unsupported Lease contact type: {0}.").format(value))
            if row.recipient_type == "Role" and not frappe.db.exists("Role", value):
                frappe.throw(_("Role {0} does not exist.").format(value))
            if row.recipient_type == "Explicit User" and not frappe.db.exists("User", value):
                frappe.throw(_("User {0} does not exist.").format(value))
            if row.recipient_type == "Email":
                validate_email_address(value, throw=True)
