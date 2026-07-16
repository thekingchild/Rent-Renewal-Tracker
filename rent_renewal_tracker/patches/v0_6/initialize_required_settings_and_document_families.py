import frappe

from rent_renewal_tracker.install import set_missing_required_settings


def execute():
    """Initialize upgrade defaults and repair name-dependent revision metadata."""
    settings = frappe.get_single("Rent Renewal Settings")
    set_missing_required_settings(settings)
    settings.save(ignore_permissions=True)

    documents = frappe.get_all(
        "Lease Document",
        fields=[
            "name",
            "document_family_id",
            "revision_number",
            "revision_status",
            "confidentiality",
        ],
    )
    for document in documents:
        values = {}
        if not document.document_family_id:
            values["document_family_id"] = document.name
        if not document.revision_number:
            values["revision_number"] = 1
        if not document.revision_status:
            values["revision_status"] = "Current"
        if not document.confidentiality:
            values["confidentiality"] = "Confidential"
        if values:
            frappe.db.set_value(
                "Lease Document",
                document.name,
                values,
                update_modified=False,
            )
