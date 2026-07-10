import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


def derive_schedule_status(*, due_date, payment_status, docstatus=0):
    if docstatus == 2:
        return "Cancelled"
    if payment_status in {"Paid", "Waived"}:
        return payment_status
    if not due_date or getdate(due_date) > getdate(today()):
        return "Planned"
    if getdate(due_date) == getdate(today()):
        return "Due"
    return "Overdue"


class RentSchedule(Document):
    def validate(self):
        self.validate_period()
        self.validate_amounts()
        self.validate_lease_currency()
        self.total_due = flt(self.base_rent) + flt(self.service_charge) + flt(self.tax)
        self.schedule_status = derive_schedule_status(
            due_date=self.due_date,
            payment_status=self.payment_status,
            docstatus=self.docstatus,
        )

    def before_cancel(self):
        self.schedule_status = "Cancelled"

    def validate_period(self):
        if self.period_from and self.period_to and getdate(self.period_to) < getdate(self.period_from):
            frappe.throw(_("Period To cannot be earlier than Period From."))

        if not self.lease or not self.period_from or not self.period_to:
            return

        lease_dates = frappe.db.get_value("Lease", self.lease, ["start_date", "end_date"])
        lease_start, lease_end = lease_dates or (None, None)
        if lease_start and getdate(self.period_from) < getdate(lease_start):
            frappe.throw(_("Rent period cannot begin before the lease starts."))
        if lease_end and getdate(self.period_to) > getdate(lease_end):
            frappe.throw(_("Rent period cannot end after the lease ends."))

    def validate_amounts(self):
        for fieldname in ("base_rent", "service_charge", "tax"):
            if flt(self.get(fieldname)) < 0:
                frappe.throw(_("{0} cannot be negative.").format(self.meta.get_label(fieldname)))

        if not any(flt(self.get(fieldname)) for fieldname in ("base_rent", "service_charge", "tax")):
            frappe.throw(_("A rent schedule must contain at least one non-zero amount."))

    def validate_lease_currency(self):
        if not self.lease or not self.currency:
            return
        lease_currency = frappe.db.get_value("Lease", self.lease, "currency")
        if lease_currency and lease_currency != self.currency:
            frappe.throw(
                _("Schedule currency {0} must match lease currency {1}.").format(
                    self.currency, lease_currency
                )
            )

