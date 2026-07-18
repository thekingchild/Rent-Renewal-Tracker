import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today


PAYMENTS_PER_YEAR = {
    "Monthly": 12,
    "Quarterly": 4,
    "Semi-Annual": 2,
    "Annual": 1,
}


def derive_schedule_status(*, due_date, payment_status, docstatus=0):
    if docstatus == 2:
        return "Cancelled"
    if payment_status in {"Paid", "Waived"}:
        return payment_status
    if payment_status == "Partially Paid":
        return "Partially Paid"
    if not due_date or getdate(due_date) > getdate(today()):
        return "Planned"
    if getdate(due_date) == getdate(today()):
        return "Due"
    return "Overdue"


class RentSchedule(Document):
    def validate(self):
        self.validate_period()
        if self.is_new():
            self.set_missing_lease_financials()
        self.validate_amounts()
        self.validate_lease_currency()
        self.validate_no_overlap()
        self.total_due = flt(self.base_rent) + flt(self.service_charge) + flt(self.tax)
        self.validate_payment_tracking()
        self.schedule_status = derive_schedule_status(
            due_date=self.due_date,
            payment_status=self.payment_status,
            docstatus=self.docstatus,
        )

    def before_update_after_submit(self):
        self.validate_payment_tracking()
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

    def set_missing_lease_financials(self):
        if not self.lease:
            return
        defaults = calculate_lease_financial_defaults(self.lease)
        for fieldname in ("currency", "base_rent", "service_charge", "tax"):
            if self.get(fieldname) in (None, "") and defaults.get(fieldname) is not None:
                self.set(fieldname, defaults.get(fieldname))

    def validate_payment_tracking(self):
        payments = self.get("payments") or []
        total_paid = 0.0
        for row in payments:
            amount = flt(row.amount)
            if amount <= 0:
                frappe.throw(_("Payment amount must be greater than zero."))
            if not row.payment_date or not row.reference:
                frappe.throw(_("Payment Date and Reference are required for every payment."))
            total_paid += amount

        if total_paid > flt(self.total_due):
            frappe.throw(_("Total payments cannot exceed Total Due."))

        self.total_paid = total_paid
        self.outstanding_balance = max(flt(self.total_due) - total_paid, 0)

        if payments:
            self.payment_reconciliation_required = 0
            latest = payments[-1]
            self.payment_reference = latest.reference
            self.paid_on = latest.payment_date
            if self.outstanding_balance <= 0:
                self.payment_status = "Paid"
            else:
                self.payment_status = "Partially Paid"
            return

        if self.payment_reconciliation_required:
            self.total_paid = 0
            self.outstanding_balance = flt(self.total_due)
            self.payment_status = "Partially Paid"
            return

        if self.payment_status == "Waived":
            if not (self.notes or "").strip():
                frappe.throw(_("A waiver reason is required in Notes."))
            self.total_paid = 0
            self.outstanding_balance = 0
            return

        if self.payment_status in {"Partially Paid", "Paid"}:
            frappe.throw(_("Use Record Payment to capture paid amounts and calculate the balance."))

        self.payment_status = "Not Paid"
        self.total_paid = 0
        self.outstanding_balance = flt(self.total_due)

    def validate_no_overlap(self):
        if not self.lease or not self.period_from or not self.period_to:
            return
        existing = frappe.db.get_value(
            "Rent Schedule",
            {
                "name": ["!=", self.name or ""],
                "lease": self.lease,
                "docstatus": ["<", 2],
                "period_from": ["<=", self.period_to],
                "period_to": [">=", self.period_from],
            },
            "name",
        )
        if existing:
            frappe.throw(_("Rent period overlaps existing schedule {0}.").format(existing))


def calculate_lease_financial_defaults(lease):
    if isinstance(lease, str):
        lease = frappe.get_doc("Lease", lease)

    installments = PAYMENTS_PER_YEAR.get(lease.payment_frequency)
    result = frappe._dict(
        currency=lease.currency,
        base_rent=None,
        service_charge=None,
        tax=None,
        requires_manual_amount=False,
        message=None,
    )

    if not installments:
        result.requires_manual_amount = True
        result.message = _("Payment Frequency {0} requires manual schedule amounts.").format(
            lease.payment_frequency
        )
        return result

    if lease.rent_basis not in {"Monthly", "Annual"}:
        result.requires_manual_amount = True
        result.message = _(
            "Rent Basis {0} cannot be calculated safely from the current Lease fields; "
            "enter the amount manually."
        ).format(lease.rent_basis)
        return result

    annual_base = flt(lease.annual_rent)
    if lease.rent_basis == "Monthly" and flt(lease.monthly_rent):
        annual_base = flt(lease.monthly_rent) * 12
    elif not annual_base and flt(lease.monthly_rent):
        annual_base = flt(lease.monthly_rent) * 12

    if annual_base:
        result.base_rent = annual_base / installments
    result.service_charge = flt(lease.annual_service_charge) / installments
    result.tax = flt(lease.annual_tax) / installments
    return result


@frappe.whitelist()
def get_lease_financial_defaults(lease, period_from=None, period_to=None):
    lease_doc = frappe.get_doc("Lease", lease)
    lease_doc.check_permission("read")
    if period_from and period_to:
        if getdate(period_from) < getdate(lease_doc.start_date):
            frappe.throw(_("Rent period cannot begin before the lease starts."))
        if getdate(period_to) > getdate(lease_doc.end_date):
            frappe.throw(_("Rent period cannot end after the lease ends."))
    return calculate_lease_financial_defaults(lease_doc)
