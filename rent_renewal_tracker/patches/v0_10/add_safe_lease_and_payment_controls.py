import frappe
from frappe.utils import flt, getdate

from rent_renewal_tracker.rent_renewal_tracker.doctype.lease.lease import (
    sync_lease_overlap_review_flags,
)


def execute():
    frappe.db.add_index("Lease", ["property", "start_date", "end_date", "docstatus"], "property_lease_period")
    migrate_legacy_payment_balances()
    sync_lease_overlap_review_flags()


def migrate_legacy_payment_balances():
    schedules = frappe.get_all(
        "Rent Schedule",
        fields=[
            "name", "total_due", "base_rent", "service_charge", "tax",
            "payment_status", "payment_reference", "paid_on", "modified",
        ],
        limit=0,
    )
    for schedule in schedules:
        total_due = flt(schedule.total_due) or (
            flt(schedule.base_rent) + flt(schedule.service_charge) + flt(schedule.tax)
        )
        migrate_legacy_schedule_payment(schedule, total_due)


def migrate_legacy_schedule_payment(schedule, total_due):
    if frappe.db.exists(
        "Rent Schedule Payment",
        {"parent": schedule.name, "parenttype": "Rent Schedule", "parentfield": "payments"},
    ):
        return

    values = {
        "total_paid": 0,
        "outstanding_balance": total_due,
        "payment_reconciliation_required": 0,
    }

    if schedule.payment_status == "Paid" and total_due > 0:
        payment = frappe.get_doc(
            {
                "doctype": "Rent Schedule Payment",
                "parent": schedule.name,
                "parenttype": "Rent Schedule",
                "parentfield": "payments",
                "idx": 1,
                "payment_date": schedule.paid_on or getdate(schedule.modified),
                "amount": total_due,
                "reference": schedule.payment_reference or "Legacy paid status",
                "notes": "Created from the legacy paid status during migration.",
            }
        )
        payment.db_insert()
        values.update({"total_paid": total_due, "outstanding_balance": 0})
    elif schedule.payment_status == "Partially Paid":
        values.update({"payment_reconciliation_required": 1})
    elif schedule.payment_status == "Waived":
        values.update({"outstanding_balance": 0})

    frappe.db.set_value("Rent Schedule", schedule.name, values, update_modified=False)
