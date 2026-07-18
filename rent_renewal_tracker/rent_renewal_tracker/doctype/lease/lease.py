import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, flt, getdate, today


FINAL_STATUSES = {"Renewed", "Terminated"}
RENEWAL_IN_PROGRESS = {"Draft", "Pending Approval", "Approved"}
LIFECYCLE_ELIGIBLE_STATUSES = {"Active", "Expiring Soon", "Expired"}
ONGOING_LEASE_STATUSES = {
    "Active",
    "Expiring Soon",
    "Renewal in Progress",
    "Termination in Progress",
}
OVERLAP_RELEVANT_FIELDS = ("property", "start_date", "end_date", "lease_status")


class Lease(Document):
    def before_insert(self):
        self.lease_id = self.name
        if self.amended_from:
            self.migration_source_id = None

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
        self.overlap_review_required = 0

    def validate(self):
        self.set_property_region()
        self.validate_dates()
        self.validate_amounts()
        self.validate_current_successor()
        self.calculate_derived_values()
        self.validate_active_requirements()
        self.validate_property_lease_overlap()

    def validate_current_successor(self):
        if not self.predecessor_lease:
            return

        existing = frappe.db.get_value(
            "Lease",
            {
                "name": ["!=", self.name or ""],
                "predecessor_lease": self.predecessor_lease,
                "docstatus": ["<", 2],
            },
            "name",
        )
        if existing:
            frappe.throw(
                _("Lease {0} already has current successor {1}.").format(
                    self.predecessor_lease, existing
                )
            )

    def validate_property_lease_overlap(self):
        if not self.property or not self.start_date or not self.end_date:
            self.overlap_review_required = 0
            return

        # A legacy conflict must remain resolvable by ending either lease.
        if not self.is_new() and self.lease_status not in ONGOING_LEASE_STATUSES:
            self.overlap_review_required = 0
            return

        should_block = self.is_new() or any(
            self.has_value_changed(fieldname) for fieldname in OVERLAP_RELEVANT_FIELDS
        )
        conflicts = get_property_lease_overlaps(
            property_name=self.property,
            start_date=self.start_date,
            end_date=self.end_date,
            exclude_lease=self.name,
            lock_property=should_block,
        )
        self.overlap_review_required = int(bool(conflicts))
        if not conflicts or not should_block:
            return

        visible = [row for row in conflicts if _can_read_conflicting_lease(row.name)]
        if visible:
            details = ", ".join(
                _("{0} ({1} to {2})").format(row.name, row.start_date, row.end_date)
                for row in visible
            )
            frappe.throw(
                _("This property already has an ongoing Lease with an overlapping period: {0}.").format(
                    details
                ),
                title=_("Overlapping Lease Period"),
            )
        frappe.throw(
            _("This property already has an ongoing Lease with an overlapping period."),
            title=_("Overlapping Lease Period"),
        )

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
        if not self.end_date or self.lease_status in FINAL_STATUSES or self.lease_status == "Termination in Progress":
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
        if self.lease_status not in {"Active", "Expiring Soon", "Renewal in Progress", "Termination in Progress"}:
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


def get_property_lease_overlaps(
    *, property_name, start_date, end_date, exclude_lease=None, lock_property=False
):
    """Return ongoing leases whose inclusive terms overlap the proposed term."""
    if not property_name or not start_date or not end_date:
        return []

    if lock_property:
        # Serializing by Property closes the race where two users insert leases
        # for the same property before either transaction has committed.
        frappe.db.sql("select name from `tabProperty` where name=%s for update", property_name)

    return frappe.db.sql(
        """
        select name, start_date, end_date, lease_status
        from `tabLease`
        where property = %(property)s
          and name != %(exclude_lease)s
          and docstatus < 2
          and lease_status in %(ongoing_statuses)s
          and start_date <= %(end_date)s
          and end_date >= %(start_date)s
        order by start_date, name
        """,
        {
            "property": property_name,
            "exclude_lease": exclude_lease or "",
            "ongoing_statuses": tuple(sorted(ONGOING_LEASE_STATUSES)),
            "start_date": getdate(start_date),
            "end_date": getdate(end_date),
        },
        as_dict=True,
    )


def sync_lease_overlap_review_flags():
    rows = frappe.db.sql(
        """
        select a.name, b.name
        from `tabLease` a
        join `tabLease` b on a.name < b.name
          and a.property = b.property
          and a.docstatus < 2 and b.docstatus < 2
          and a.lease_status in %(ongoing_statuses)s
          and b.lease_status in %(ongoing_statuses)s
          and a.start_date <= b.end_date and a.end_date >= b.start_date
        """,
        {"ongoing_statuses": tuple(sorted(ONGOING_LEASE_STATUSES))},
    )
    overlap_names = {name for row in rows for name in row}
    flagged = set(frappe.get_all("Lease", {"overlap_review_required": 1}, pluck="name"))
    for lease_name in overlap_names ^ flagged:
        frappe.db.set_value(
            "Lease",
            lease_name,
            "overlap_review_required",
            int(lease_name in overlap_names),
            update_modified=False,
        )
    return sorted(overlap_names)


def _can_read_conflicting_lease(lease_name):
    try:
        return frappe.has_permission("Lease", "read", doc=lease_name)
    except (frappe.DoesNotExistError, frappe.PermissionError):
        return False


@frappe.whitelist()
def check_property_lease_overlap(property_name, start_date, end_date, exclude_lease=None):
    """Provide a non-blocking form warning without exposing restricted Lease details."""
    if not frappe.has_permission("Lease", "create") and not exclude_lease:
        frappe.throw(_("Not permitted to create a Lease."), frappe.PermissionError)

    conflicts = get_property_lease_overlaps(
        property_name=property_name,
        start_date=start_date,
        end_date=end_date,
        exclude_lease=exclude_lease,
    )
    visible = [row for row in conflicts if _can_read_conflicting_lease(row.name)]
    return {
        "has_conflict": bool(conflicts),
        "visible_conflicts": [
            {
                "name": row.name,
                "start_date": row.start_date,
                "end_date": row.end_date,
                "lease_status": row.lease_status,
            }
            for row in visible
        ],
    }


@frappe.whitelist()
def start_lifecycle_request(lease, action):
    """Start, or return, the single open renewal/termination process for a lease."""
    if action not in {"Renew", "Terminate"}:
        frappe.throw(_("Action must be Renew or Terminate."))

    doc = frappe.get_doc("Lease", lease)
    doc.check_permission("read")
    if doc.docstatus != 1 or doc.lease_status not in LIFECYCLE_ELIGIBLE_STATUSES:
        frappe.throw(_("Only submitted active, expiring, or expired leases can start this action."))

    existing = frappe.db.get_value(
        "Renewal Request", {"open_cycle_key": doc.name}, ["name", "recommendation"], as_dict=True
    )
    if existing:
        if existing.recommendation != action:
            frappe.throw(
                _("Open {0} request {1} must be completed or cancelled first.").format(
                    existing.recommendation, existing.name
                )
            )
        return existing.name

    request = frappe.get_doc(
        {
            "doctype": "Renewal Request",
            "lease": doc.name,
            "recommendation": action,
            "business_justification": _("Lifecycle request initiated from lease {0}.").format(doc.name),
        }
    )
    request.insert()
    return request.name
