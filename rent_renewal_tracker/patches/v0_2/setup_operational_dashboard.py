import frappe

from rent_renewal_tracker.install import setup_dashboard_defaults


def execute():
    setup_dashboard_defaults()
    for lease_name in frappe.get_all(
        "Lease",
        filters={"lease_id": ["is", "not set"]},
        pluck="name",
    ):
        frappe.db.set_value("Lease", lease_name, "lease_id", lease_name, update_modified=False)
