import frappe


def refresh_lease_statuses():
    """Refresh date-derived fields daily; saving runs the authoritative controller rules."""
    lease_names = frappe.get_all(
        "Lease",
        filters={"lease_status": ["not in", ["Terminated", "Renewed"]]},
        pluck="name",
    )

    for lease_name in lease_names:
        lease = frappe.get_doc("Lease", lease_name)
        lease.calculate_derived_values()
        frappe.db.set_value(
            "Lease",
            lease.name,
            {
                "notice_deadline": lease.notice_deadline,
                "days_to_expiry": lease.days_to_expiry,
                "next_action_date": lease.next_action_date,
                "annual_rent": lease.annual_rent,
                "total_annual_occupancy_cost": lease.total_annual_occupancy_cost,
                "lease_status": lease.lease_status,
            },
            update_modified=False,
        )


def refresh_rent_schedule_statuses():
    """Refresh unpaid schedule states without altering submitted commercial values."""
    from rent_renewal_tracker.rent_renewal_tracker.doctype.rent_schedule.rent_schedule import (
        derive_schedule_status,
    )

    schedules = frappe.get_all(
        "Rent Schedule",
        filters={
            "docstatus": ["<", 2],
            "payment_status": ["not in", ["Paid", "Waived"]],
        },
        fields=["name", "due_date", "payment_status", "schedule_status", "docstatus"],
    )

    for schedule in schedules:
        status = derive_schedule_status(
            due_date=schedule.due_date,
            payment_status=schedule.payment_status,
            docstatus=schedule.docstatus,
        )
        if status != schedule.schedule_status:
            frappe.db.set_value(
                "Rent Schedule",
                schedule.name,
                "schedule_status",
                status,
                update_modified=False,
            )


def refresh_lease_document_statuses():
    """Refresh stored attention states without modifying document evidence."""
    names = frappe.get_all("Lease Document", pluck="name")
    for name in names:
        document = frappe.get_doc("Lease Document", name)
        document.set_document_status()
        frappe.db.set_value(
            "Lease Document", name,
            {
                "document_status": document.document_status,
                "days_to_document_expiry": document.days_to_document_expiry,
            },
            update_modified=False,
        )
