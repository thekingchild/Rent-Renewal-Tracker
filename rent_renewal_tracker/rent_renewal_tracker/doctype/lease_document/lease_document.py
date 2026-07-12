from pathlib import PurePosixPath

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


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
    def validate(self):
        if (
            self.expiry_date
            and self.effective_date
            and getdate(self.expiry_date) < getdate(self.effective_date)
        ):
            frappe.throw(_("Expiry Date cannot be earlier than Effective Date."))
        self.validate_private_file()

    def after_insert(self):
        self.attach_file_to_document()

    def on_update(self):
        if not self.is_new():
            self.attach_file_to_document()

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
