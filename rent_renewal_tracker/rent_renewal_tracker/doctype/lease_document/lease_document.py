from pathlib import PurePosixPath

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


ALLOWED_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".txt",
    ".xls",
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

        attached_to = (file_record.attached_to_doctype, file_record.attached_to_name)
        permitted_attachments = {(None, None), ("Lease", self.lease), ("Lease Document", self.name)}
        if attached_to not in permitted_attachments:
            frappe.throw(_("The selected file is already attached to another record."))

    def attach_file_to_document(self):
        file_record = self.get_file_record()
        if not file_record or not self.name:
            return
        if (file_record.attached_to_doctype, file_record.attached_to_name) == (
            "Lease Document",
            self.name,
        ):
            return
        frappe.db.set_value(
            "File",
            file_record.name,
            {"attached_to_doctype": "Lease Document", "attached_to_name": self.name},
            update_modified=False,
        )
