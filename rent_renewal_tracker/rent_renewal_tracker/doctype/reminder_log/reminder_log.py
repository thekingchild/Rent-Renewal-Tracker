import frappe
from frappe import _
from frappe.model.document import Document


ALLOWED_STATUS_TRANSITIONS = {
    "Queued": {"Sent", "Failed"},
    "Failed": {"Queued", "Sent"},
}


class ReminderLog(Document):
    def validate(self):
        if self.is_new():
            if self.status != "Queued":
                frappe.throw(_("New reminder logs must start in Queued status."))
            return

        previous = self.get_doc_before_save()
        if not self.flags.delivery_update:
            frappe.throw(_("Reminder Logs can only be updated by the delivery service."))
        if previous and self.status != previous.status:
            allowed = ALLOWED_STATUS_TRANSITIONS.get(previous.status, set())
            if self.status not in allowed:
                frappe.throw(
                    _("Reminder Log cannot move from {0} to {1}.").format(
                        previous.status, self.status
                    )
                )

    def on_trash(self):
        if not getattr(frappe.flags, "in_uninstall", False):
            frappe.throw(_("Reminder Logs are audit records and cannot be deleted."))

