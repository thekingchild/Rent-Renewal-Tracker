import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, now_datetime, today


FINAL_STATES = {"Completed", "Rejected"}
REVIEW_STATES = {"Department Review", "Finance Review", "Legal Review", "Management Approval"}
STATE_ACTIONS = {
    ("Draft", "Department Review"): "Submit for Department Review",
    ("Department Review", "Finance Review"): "Approve",
    ("Department Review", "Draft"): "Return",
    ("Finance Review", "Legal Review"): "Approve",
    ("Finance Review", "Draft"): "Return",
    ("Legal Review", "Management Approval"): "Approve",
    ("Legal Review", "Draft"): "Return",
    ("Management Approval", "Approved"): "Approve",
    ("Management Approval", "Rejected"): "Reject",
    ("Approved", "Completed"): "Mark Executed",
}


class RenewalRequest(Document):
    def before_insert(self):
        self.set_sequence_and_snapshot()
        self.requested_by = self.requested_by or frappe.session.user
        self.requested_on = self.requested_on or today()

    def validate(self):
        self.validate_proposed_terms()
        self.validate_one_open_cycle()
        self.set_open_cycle_key()
        self.set_current_approver_role()
        self.record_state_transition()
        self.validate_completion()

    def after_insert(self):
        self.sync_lease_status()

    def on_update(self):
        if self.workflow_state == "Completed" and self.recommendation != "Terminate":
            self.create_successor_lease()
        self.sync_lease_status()

    def on_cancel(self):
        self.db_set("open_cycle_key", None, update_modified=False)
        self.sync_lease_status(cancelled=self.workflow_state != "Rejected")

    def set_sequence_and_snapshot(self):
        if not self.lease:
            return

        lease = frappe.get_doc("Lease", self.lease)
        previous_sequence = frappe.db.get_value(
            "Renewal Request",
            {"lease": self.lease},
            "renewal_sequence",
            order_by="renewal_sequence desc",
        )
        self.renewal_sequence = (previous_sequence or 0) + 1

        snapshots = {
            "current_start_date": lease.start_date,
            "current_end_date": lease.end_date,
            "current_currency": lease.currency,
            "current_monthly_rent": lease.monthly_rent,
            "current_annual_rent": lease.annual_rent,
            "current_payment_frequency": lease.payment_frequency,
        }
        for fieldname, value in snapshots.items():
            if not self.get(fieldname):
                self.set(fieldname, value)

        defaults = {
            "proposed_property": lease.property,
            "proposed_start_date": add_days(lease.end_date, 1) if lease.end_date else None,
            "proposed_currency": lease.currency,
            "proposed_rent_basis": lease.rent_basis,
            "proposed_monthly_rent": lease.monthly_rent,
            "proposed_annual_rent": lease.annual_rent,
            "proposed_payment_frequency": lease.payment_frequency,
            "proposed_escalation_rule": lease.escalation_rule,
        }
        for fieldname, value in defaults.items():
            if not self.get(fieldname):
                self.set(fieldname, value)

    def validate_proposed_terms(self):
        if (
            self.proposed_start_date
            and self.proposed_end_date
            and getdate(self.proposed_end_date) <= getdate(self.proposed_start_date)
        ):
            frappe.throw(_("Proposed End Date must be later than Proposed Start Date."))

        if (
            self.proposed_notice_date
            and self.proposed_end_date
            and getdate(self.proposed_notice_date) > getdate(self.proposed_end_date)
        ):
            frappe.throw(_("Proposed Notice Date cannot be later than Proposed End Date."))

        for fieldname in ("proposed_monthly_rent", "proposed_annual_rent", "budget_impact"):
            if flt(self.get(fieldname)) < 0:
                frappe.throw(_("{0} cannot be negative.").format(self.meta.get_label(fieldname)))

        if self.proposed_rent_basis == "Monthly" and flt(self.proposed_monthly_rent):
            self.proposed_annual_rent = flt(self.proposed_monthly_rent) * 12

    def set_open_cycle_key(self):
        self.open_cycle_key = (
            None if self.workflow_state in FINAL_STATES or self.docstatus == 2 else self.lease
        )

    def validate_one_open_cycle(self):
        if self.workflow_state in FINAL_STATES or self.docstatus == 2 or not self.lease:
            return
        existing = frappe.db.get_value(
            "Renewal Request",
            {"open_cycle_key": self.lease, "name": ["!=", self.name or ""]},
            "name",
        )
        if existing:
            frappe.throw(
                _("Lease {0} already has open renewal request {1}.").format(self.lease, existing)
            )

    def set_current_approver_role(self):
        self.current_approver_role = {
            "Draft": "Responsible Officer",
            "Department Review": "Department Head",
            "Finance Review": "Finance Approver",
            "Legal Review": "Legal Approver",
            "Management Approval": "Management Approver",
            "Approved": "Lease Administrator",
        }.get(self.workflow_state)

    def record_state_transition(self):
        previous = self.get_doc_before_save()
        if not previous or previous.workflow_state == self.workflow_state:
            return

        from_state = previous.workflow_state
        to_state = self.workflow_state
        action = STATE_ACTIONS.get((from_state, to_state))
        if not action:
            frappe.throw(_("Transition from {0} to {1} is not permitted.").format(from_state, to_state))

        comment = (self.workflow_comment or "").strip()
        if action in {"Return", "Reject"} and not comment:
            frappe.throw(_("A workflow comment is required when returning or rejecting a renewal."))
        if from_state in REVIEW_STATES and self.requested_by == frappe.session.user:
            frappe.throw(_("The renewal requester cannot approve their own review stage."))

        self.append(
            "decision_history",
            {
                "from_state": from_state,
                "action": action,
                "to_state": to_state,
                "actor": frappe.session.user,
                "acted_on": now_datetime(),
                "comment": comment,
            },
        )
        self.workflow_comment = None

        if to_state in {"Approved", "Rejected"}:
            self.final_decision_by = frappe.session.user
            self.final_decision_on = today()
        if to_state == "Rejected":
            self.rejection_reason = comment
        if to_state == "Completed":
            self.completion_date = today()

    def validate_completion(self):
        if self.workflow_state != "Completed":
            return
        if not self.proposed_start_date or not self.proposed_end_date:
            frappe.throw(_("Proposed lease dates are required before completion."))
        document_category = "Approval" if self.recommendation == "Terminate" else "Renewal Letter"
        if not frappe.db.exists("Lease Document", {"lease": self.lease, "category": document_category}):
            frappe.throw(
                _("A private {0} document is required before completion.").format(document_category)
            )

    def create_successor_lease(self):
        if self.successor_lease:
            return self.successor_lease

        existing = frappe.db.get_value("Lease", {"predecessor_lease": self.lease}, "name")
        if existing:
            self.db_set("successor_lease", existing, update_modified=False)
            return existing

        predecessor = frappe.get_doc("Lease", self.lease)
        notice_period_days = predecessor.notice_period_days
        if self.proposed_notice_date and self.proposed_end_date:
            notice_period_days = max(
                0, (getdate(self.proposed_end_date) - getdate(self.proposed_notice_date)).days
            )

        successor = frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_title": _("{0} - Renewal {1}").format(
                    predecessor.lease_title, self.renewal_sequence
                ),
                "property": self.proposed_property or predecessor.property,
                "landlord": predecessor.landlord,
                "lease_type": predecessor.lease_type,
                "external_reference": predecessor.external_reference,
                "responsible_department": predecessor.responsible_department,
                "responsible_officer": predecessor.responsible_officer,
                "contract_owner": predecessor.contract_owner,
                "backup_officer": predecessor.backup_officer,
                "lease_contacts": [
                    {
                        "contact_type": row.contact_type,
                        "contact_name": row.contact_name,
                        "organization": row.organization,
                        "email": row.email,
                        "phone": row.phone,
                        "receives_reminders": row.receives_reminders,
                        "notes": row.notes,
                    }
                    for row in predecessor.lease_contacts
                ],
                "start_date": self.proposed_start_date,
                "end_date": self.proposed_end_date,
                "notice_period_days": notice_period_days,
                "renewal_option": predecessor.renewal_option,
                "auto_renew": predecessor.auto_renew,
                "currency": self.proposed_currency,
                "rent_basis": self.proposed_rent_basis,
                "monthly_rent": self.proposed_monthly_rent,
                "annual_rent": self.proposed_annual_rent,
                "payment_frequency": self.proposed_payment_frequency,
                "security_deposit": predecessor.security_deposit,
                "annual_service_charge": predecessor.annual_service_charge,
                "annual_tax": predecessor.annual_tax,
                "escalation_rule": self.proposed_escalation_rule,
                "lease_status": "Active",
                "renewal_status": "Not Started",
                "confidentiality_classification": predecessor.confidentiality_classification,
                "predecessor_lease": predecessor.name,
            }
        ).insert(ignore_permissions=True)
        self.db_set("successor_lease", successor.name, update_modified=False)
        return successor.name

    def sync_lease_status(self, cancelled=False):
        if not self.lease or not frappe.db.exists("Lease", self.lease):
            return

        if cancelled:
            lease_end_date = frappe.db.get_value("Lease", self.lease, "end_date")
            status = "Expired" if lease_end_date and getdate(lease_end_date) < getdate(today()) else "Active"
            values = {
                "renewal_status": "Not Started",
                "lease_status": status,
                "renewal_completed": 0,
                "last_renewal_request": None,
            }
        else:
            renewal_status = {
                "Draft": "Draft",
                "Department Review": "Pending Approval",
                "Finance Review": "Pending Approval",
                "Legal Review": "Pending Approval",
                "Management Approval": "Pending Approval",
                "Approved": "Approved",
                "Rejected": "Rejected",
                "Completed": "Completed",
            }.get(self.workflow_state, "Not Started")
            values = {
                "renewal_status": renewal_status,
                "lease_status": "Renewed" if self.workflow_state == "Completed" else "Renewal in Progress",
                "renewal_completed": self.workflow_state == "Completed",
                "last_renewal_request": self.name,
            }
            if self.workflow_state == "Rejected":
                lease_end_date = frappe.db.get_value("Lease", self.lease, "end_date")
                values["lease_status"] = (
                    "Expired"
                    if lease_end_date and getdate(lease_end_date) < getdate(today())
                    else "Active"
                )
            elif self.workflow_state == "Completed" and self.recommendation == "Terminate":
                values["lease_status"] = "Terminated"

        frappe.db.set_value("Lease", self.lease, values, update_modified=False)
