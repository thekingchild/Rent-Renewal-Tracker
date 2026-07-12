import frappe
from frappe.utils import date_diff, getdate, today


def execute():
    """Conservatively initialize revision and expiry metadata for existing documents."""
    threshold = frappe.db.get_single_value(
        "Rent Renewal Settings", "document_expiring_soon_threshold"
    ) or 30
    documents = frappe.get_all(
        "Lease Document",
        fields=["name", "expiry_date", "document_family_id", "revision_number", "revision_status"],
    )
    for document in documents:
        values = {
            "document_family_id": document.document_family_id or document.name,
            "revision_number": document.revision_number or 1,
            "revision_status": document.revision_status or "Current",
        }
        if values["revision_status"] == "Superseded":
            values["document_status"] = "Superseded"
            values["days_to_document_expiry"] = None
        elif not document.expiry_date:
            values["document_status"] = "No Expiry Date"
            values["days_to_document_expiry"] = None
        else:
            days = date_diff(getdate(document.expiry_date), getdate(today()))
            values["days_to_document_expiry"] = days
            values["document_status"] = (
                "Expired" if days < 0 else "Expiring Soon" if days <= threshold else "Current"
            )
        frappe.db.set_value("Lease Document", document.name, values, update_modified=False)
