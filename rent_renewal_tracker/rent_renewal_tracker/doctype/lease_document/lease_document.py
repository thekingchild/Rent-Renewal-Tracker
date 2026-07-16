from pathlib import PurePosixPath

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, getdate, now_datetime, today


ALLOWED_EXTENSIONS = {
    ".csv",
    ".docx",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".txt",
    ".xlsx",
}


class LeaseDocument(Document):
    def before_validate(self):
        if self.is_new():
            self.set_revision_identity()

    def validate(self):
        if (
            self.expiry_date
            and self.effective_date
            and getdate(self.expiry_date) < getdate(self.effective_date)
        ):
            frappe.throw(_("Expiry Date cannot be earlier than Effective Date."))
        self.validate_immutable_file()
        self.validate_revision()
        self.set_document_status()
        self.validate_private_file()

    def after_insert(self):
        self.attach_file_to_document()
        self.supersede_previous_revision()

    def on_update(self):
        if not self.is_new():
            self.attach_file_to_document()

    def set_revision_identity(self):
        self.revision_status = "Current"
        self.revised_by = frappe.session.user
        self.revised_on = now_datetime()
        if self.previous_revision:
            frappe.db.sql(
                "select name from `tabLease Document` where name=%s for update", self.previous_revision
            )
            previous = frappe.get_doc("Lease Document", self.previous_revision)
            previous.check_permission("write")
            if previous.revision_status == "Superseded":
                frappe.throw(_("Create a revision from the current document revision."))
            self.document_family_id = previous.document_family_id or previous.name
            latest = frappe.db.get_value(
                "Lease Document", {"document_family_id": self.document_family_id},
                "revision_number", order_by="revision_number desc"
            ) or previous.revision_number or 1
            self.revision_number = latest + 1
        else:
            self.document_family_id = self.name
            self.revision_number = 1

    def validate_revision(self):
        if not self.previous_revision:
            return
        previous = frappe.get_doc("Lease Document", self.previous_revision)
        if previous.lease != self.lease:
            frappe.throw(_("A revision must belong to the same lease as its previous revision."))
        if not (self.revision_reason or "").strip():
            frappe.throw(_("Revision Reason is required."))
        if previous.file == self.file:
            frappe.throw(_("A new revision must use a new file."))

    def validate_immutable_file(self):
        previous = self.get_doc_before_save()
        if previous and previous.file != self.file:
            frappe.throw(_("Create a new revision instead of replacing an existing document file."))

    def set_document_status(self):
        if self.revision_status == "Superseded":
            self.document_status = "Superseded"
            self.days_to_document_expiry = None
            return
        if not self.expiry_date:
            self.document_status = "No Expiry Date"
            self.days_to_document_expiry = None
            return
        self.days_to_document_expiry = date_diff(self.expiry_date, today())
        threshold = frappe.db.get_single_value(
            "Rent Renewal Settings", "document_expiring_soon_threshold", cache=True
        ) or 30
        if self.days_to_document_expiry < 0:
            self.document_status = "Expired"
        elif self.days_to_document_expiry <= threshold:
            self.document_status = "Expiring Soon"
        else:
            self.document_status = "Current"

    def supersede_previous_revision(self):
        if not self.previous_revision:
            return

        previous = frappe.get_doc("Lease Document", self.previous_revision)
        previous.check_permission("write")
        previous.revision_status = "Superseded"
        previous.document_status = "Superseded"
        previous.days_to_document_expiry = None
        previous.save()

    def get_file_record(self):
        if not self.file:
            return None
        return frappe.db.get_value(
            "File",
            {"file_url": self.file},
            ["name", "file_name", "file_size", "is_private", "attached_to_doctype", "attached_to_name"],
            as_dict=True,
        )

    def validate_private_file(self):
        file_record = self.get_file_record()
        if not file_record:
            frappe.throw(_("The selected file does not exist."))
        if not file_record.is_private:
            frappe.throw(_("Lease documents must be uploaded as private files."))

        extension = PurePosixPath(file_record.file_name or self.file).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            frappe.throw(
                _("File type {0} is not permitted for lease documents.").format(
                    extension or _("unknown")
                )
            )

        from frappe.core.api.file import get_max_file_size

        max_size_bytes = get_max_file_size()
        if file_record.file_size and file_record.file_size > max_size_bytes:
            frappe.throw(
                _("Lease document exceeds the {0} MB file-size limit.").format(
                    max_size_bytes / (1024 * 1024)
                )
            )

        if not self.can_use_file(file_record):
            frappe.throw(
                _("You do not have permission to use the selected file or its attached record."),
                frappe.PermissionError,
            )

    def can_use_file(self, file_record):
        if not frappe.has_permission("File", "read", file_record.name):
            return False
        attached_doctype = file_record.attached_to_doctype
        attached_name = file_record.attached_to_name
        if not attached_doctype or not attached_name:
            return frappe.db.get_value("File", file_record.name, "owner") == frappe.session.user
        if (attached_doctype, attached_name) in {
            ("Lease", self.lease),
            ("Lease Document", self.name),
        }:
            return frappe.db.get_value("File", file_record.name, "owner") == frappe.session.user

        # Uploads made before the form is saved are attached to a temporary name.
        if attached_doctype == "Lease Document" and not frappe.db.exists(
            "Lease Document", attached_name
        ):
            return True

        return frappe.has_permission(attached_doctype, "read", attached_name)

    def attach_file_to_document(self):
        file_record = self.get_file_record()
        if not file_record or not self.name:
            return
        attached_doctype = file_record.attached_to_doctype
        attached_name = file_record.attached_to_name
        if (attached_doctype, attached_name) == ("Lease Document", self.name):
            return
        if attached_doctype and attached_name:
            # Keep shared files attached to their original record. Only adopt files
            # uploaded for this lease or against an unsaved Lease Document form.
            is_temporary_upload = attached_doctype == "Lease Document" and not frappe.db.exists(
                "Lease Document", attached_name
            )
            if (attached_doctype, attached_name) != ("Lease", self.lease) and not is_temporary_upload:
                return
        frappe.db.set_value(
            "File",
            file_record.name,
            {"attached_to_doctype": "Lease Document", "attached_to_name": self.name},
            update_modified=False,
        )
