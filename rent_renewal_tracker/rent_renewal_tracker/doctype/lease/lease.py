import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, flt, getdate, today


FINAL_STATUSES = {"Renewed", "Terminated"}
RENEWAL_IN_PROGRESS = {"Draft", "Pending Approval", "Approved"}


class Lease(Document):
    def before_insert(self):
        self.lease_id = self.name

    def after_insert(self):
        # Frappe assigns series names after before_insert on current releases.
        if self.lease_id != self.name:
            self.lease_id = self.name
            self.db_set("lease_id", self.name, update_modified=False)

    def before_submit(self):
        self.lease_status = "Active"
        self.calculate_derived_values()
        self.validate_required_terms()

    def before_cancel(self):
        self.lease_status = "Terminated"

    def validate(self):
        self.set_property_region()
        self.validate_dates()
        self.validate_amounts()
        self.calculate_derived_values()
        self.validate_active_requirements()

    def set_property_region(self):
        if self.property:
            self.region = frappe.db.get_value("Property", self.property, "region")

    def validate_dates(self):
        if self.start_date and self.end_date and getdate(self.end_date) <= getdate(self.start_date):
            frappe.throw(_("End Date must be later than Start Date."))

        if (self.notice_period_days or 0) < 0:
            frappe.throw(_("Notice Period (Days) cannot be negative."))

    def validate_amounts(self):
        amount_fields = (
            "monthly_rent",
            "annual_rent",
            "security_deposit",
            "annual_service_charge",
            "annual_tax",
        )
        for fieldname in amount_fields:
            if flt(self.get(fieldname)) < 0:
                frappe.throw(_("{0} cannot be negative.").format(self.meta.get_label(fieldname)))

    def calculate_derived_values(self):
        if self.end_date:
            self.notice_deadline = add_days(self.end_date, -(self.notice_period_days or 0))
            self.days_to_expiry = date_diff(self.end_date, today())
            action_dates = [
                value
                for value in (
                    self.notice_deadline,
                    self.renewal_option_deadline,
                    self.break_clause_date,
                )
                if value
            ]
            future_dates = [value for value in action_dates if getdate(value) >= getdate(today())]
            self.next_action_date = min(future_dates, key=getdate) if future_dates else None

        if self.rent_basis == "Monthly" and flt(self.monthly_rent):
            self.annual_rent = flt(self.monthly_rent) * 12

        self.total_annual_occupancy_cost = (
            flt(self.annual_rent) + flt(self.annual_service_charge) + flt(self.annual_tax)
        )
        self.set_derived_status()

    def set_derived_status(self):
        if not self.end_date or self.lease_status in FINAL_STATUSES:
            return

        if self.renewal_status in RENEWAL_IN_PROGRESS:
            self.lease_status = "Renewal in Progress"
        elif getdate(self.end_date) < getdate(today()):
            self.lease_status = "Expired"
        elif self.lease_status != "Draft" and self.days_to_expiry <= self.get_expiring_threshold():
            self.lease_status = "Expiring Soon"
        elif self.lease_status != "Draft":
            self.lease_status = "Active"

    def get_expiring_threshold(self):
        if frappe.db.exists("DocType", "Rent Renewal Settings"):
            return (
                frappe.db.get_single_value(
                    "Rent Renewal Settings", "expiring_soon_threshold", cache=True
                )
                or 90
            )
        return 90

    def validate_active_requirements(self):
        if self.lease_status not in {"Active", "Expiring Soon", "Renewal in Progress"}:
            return

        self.validate_required_terms()

    def validate_required_terms(self):

        required = (
            "property",
            "landlord",
            "responsible_department",
            "responsible_officer",
            "end_date",
            "currency",
        )
        missing = [self.meta.get_label(fieldname) for fieldname in required if not self.get(fieldname)]
        if not flt(self.monthly_rent) and not flt(self.annual_rent):
            missing.append(_("Monthly Rent or Annual Rent"))

        if missing:
            frappe.throw(_("Submitted or active leases require: {0}.").format(", ".join(missing)))
