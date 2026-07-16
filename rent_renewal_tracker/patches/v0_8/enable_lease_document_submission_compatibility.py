import frappe
from frappe import _


def execute():
    sync_app_managed_custom_permissions()

    duplicate_families = frappe.db.sql(
        """
        select coalesce(nullif(document_family_id, ''), name) as family_id, count(*) as total
        from `tabLease Document`
        where docstatus < 2 and revision_status = 'Current'
        group by coalesce(nullif(document_family_id, ''), name)
        having count(*) > 1
        """,
        as_dict=True,
    )
    if duplicate_families:
        families = ", ".join(row.family_id for row in duplicate_families)
        frappe.throw(
            _("Lease Document migration stopped because multiple current revisions exist for: {0}.").format(
                families
            )
        )

    # Records created before Lease Document became submittable remain usable as
    # legacy evidence. Migration must never submit evidence without user action.
    frappe.db.sql(
        """
        update `tabLease Document`
        set legacy_unsubmitted = 1
        where docstatus = 0
          and ifnull(legacy_unsubmitted, 0) = 0
          and ifnull(revision_status, 'Current') in ('Current', 'Superseded')
        """
    )


def sync_app_managed_custom_permissions():
    """Keep existing-site Custom DocPerm overrides aligned with the app lifecycle."""
    if not frappe.db.exists("Custom DocPerm", {"parent": "Lease Document"}):
        return

    grants = {
        "Rent Renewal System Manager": {"submit": 1, "cancel": 1},
        "Lease Administrator": {"submit": 1, "cancel": 1},
        "Responsible Officer": {"submit": 1, "cancel": 0},
    }
    for role, values in grants.items():
        name = frappe.db.get_value(
            "Custom DocPerm",
            {"parent": "Lease Document", "role": role, "permlevel": 0, "if_owner": 0},
            "name",
        )
        if name:
            frappe.db.set_value("Custom DocPerm", name, values, update_modified=False)

    frappe.clear_cache(doctype="Lease Document")
