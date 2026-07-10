import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


class RentRenewalSettings(Document):
    def validate(self):
        if (self.expiring_soon_threshold or 0) < 1:
            frappe.throw(_("Expiring Soon Threshold must be at least one day."))
        if (self.reminder_retry_limit or 0) < 0:
            frappe.throw(_("Reminder Retry Limit cannot be negative."))
        for email in self.get_error_recipient_emails():
            validate_email_address(email, throw=True)

    def get_error_recipient_emails(self):
        raw = (self.administrator_error_recipients or "").replace(",", "\n")
        return [email.strip() for email in raw.splitlines() if email.strip()]

