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
FORMAL_DOCUMENT_CATEGORIES = {
    "Signed Agreement",
    "Addendum",
    "Renewal Letter",
    "Approval",
    "Payment Receipt",
    "Valuation",
}
EFFECTIVE_REVISION_STATES = {"Current", "Superseded"}


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
        self.validate_lifecycle_request()
        self.validate_immutable_file()
        self.validate_revision()
        self.set_document_status()
        self.validate_private_file()

    def after_insert(self):
        self.attach_file_to_document()

    def on_update(self):
        if not self.is_new():
            self.attach_file_to_document()

    def before_submit(self):
        self.flags.was_legacy_unsubmitted = bool(self.legacy_unsubmitted)
        self.validate_submission()
        if self.flags.was_legacy_unsubmitted:
            if self.revision_status not in EFFECTIVE_REVISION_STATES:
                frappe.throw(_("Only a current or superseded legacy document can be submitted."))
        else:
            self.revision_status = "Current"
        self.legacy_unsubmitted = 0
        self.revised_by = frappe.session.user
        self.revised_on = now_datetime()
        self.set_document_status()

    def on_submit(self):
        if not self.flags.was_legacy_unsubmitted:
            self.supersede_previous_revision()

    def before_cancel(self):
        if self.revision_status != "Current":
            frappe.throw(_("Only the current document revision can be cancelled."))
        if not (self.cancellation_reason or "").strip():
            frappe.throw(_("Cancellation Reason is required before cancelling a lease document."))

    def on_cancel(self):
        self.db_set(
            {
                "revision_status": "Cancelled",
                "document_status": "Cancelled",
                "days_to_document_expiry": 0,
            },
            update_modified=False,
        )
        self.restore_previous_revision()

    def on_trash(self):
        if self.docstatus != 0 or self.legacy_unsubmitted or self.revision_status != "Draft":
            frappe.throw(
                _("Submitted, cancelled, and legacy lease-document evidence cannot be deleted.")
            )

    def set_revision_identity(self):
        self.revision_status = "Draft"
        self.legacy_unsubmitted = 0
        self.revised_by = None
        self.revised_on = None
        self.cancellation_reason = None

        if self.amended_from:
            source = self.get_amendment_source()
            self.document_family_id = source.document_family_id or source.name
            self.previous_revision = source.previous_revision
            self.revision_number = self.get_next_revision_number(source.revision_number)
            return

        if self.previous_revision:
            frappe.db.sql(
                "select name from `tabLease Document` where name=%s for update",
                self.previous_revision,
            )
            previous = frappe.get_doc("Lease Document", self.previous_revision)
            previous.check_permission("write")
            self.validate_revision_source(previous)
            self.document_family_id = previous.document_family_id or previous.name
            self.revision_number = self.get_next_revision_number(previous.revision_number)
            return

        self.document_family_id = self.name
        self.revision_number = 1

    def get_next_revision_number(self, fallback=None):
        latest = frappe.db.get_value(
            "Lease Document",
            {"document_family_id": self.document_family_id},
            "revision_number",
            order_by="revision_number desc",
        )
        return (latest or fallback or 1) + 1

    def get_amendment_source(self):
        if not frappe.db.exists("Lease Document", self.amended_from):
            frappe.throw(_("Amended From must reference an existing lease document."))
        source = frappe.get_doc("Lease Document", self.amended_from)
        if source.docstatus != 2:
            frappe.throw(_("An amendment can only be created from a cancelled lease document."))
        if self.lease and source.lease != self.lease:
            frappe.throw(_("An amendment must belong to the same lease as the cancelled document."))
        return source

    def validate_lifecycle_request(self):
        if not self.renewal_request:
            return
        request_lease = frappe.db.get_value("Renewal Request", self.renewal_request, "lease")
        if request_lease != self.lease:
            frappe.throw(_("The Lifecycle Request must belong to the selected Lease."))

    def validate_revision(self):
        if self.amended_from:
            source = self.get_amendment_source()
            if source.lease != self.lease:
                frappe.throw(_("An amendment must belong to the same lease as the cancelled document."))

        if not self.previous_revision:
            if self.amended_from and not (self.revision_reason or "").strip():
                frappe.throw(_("Revision Reason is required for an amendment."))
            return

        previous = frappe.get_doc("Lease Document", self.previous_revision)
        if previous.lease != self.lease:
            frappe.throw(_("A revision must belong to the same lease as its previous revision."))
        if not (self.revision_reason or "").strip():
            frappe.throw(_("Revision Reason is required."))
        if not self.amended_from and previous.file == self.file:
            frappe.throw(_("A new revision must use a new file."))

    def validate_revision_source(self, previous):
        if previous.revision_status != "Current":
            frappe.throw(_("Create a revision from the current document revision."))
        if previous.docstatus != 1 and not previous.legacy_unsubmitted:
            frappe.throw(_("Submit the current document before creating its next revision."))

    def validate_submission(self):
        if self.category in FORMAL_DOCUMENT_CATEGORIES and not self.document_date:
            frappe.throw(_("Document Date is required before submitting this document category."))
        if self.amended_from:
            self.get_amendment_source()
        if self.previous_revision:
            frappe.db.sql(
                "select name from `tabLease Document` where name=%s for update",
                self.previous_revision,
            )
            previous = frappe.get_doc("Lease Document", self.previous_revision)
            previous.check_permission("write")
            self.validate_revision_source(previous)

    def validate_immutable_file(self):
        previous = self.get_doc_before_save()
        if not previous or previous.file == self.file:
            return
        if previous.docstatus != 0 or previous.legacy_unsubmitted or previous.revision_status != "Draft":
            frappe.throw(_("Create a new revision instead of replacing an existing document file."))

    def set_document_status(self):
        if self.docstatus == 2 or self.revision_status == "Cancelled":
            self.document_status = "Cancelled"
            self.days_to_document_expiry = 0
            return
        if self.revision_status == "Draft":
            self.document_status = "Draft"
            self.days_to_document_expiry = 0
            return
        if self.revision_status == "Superseded":
            self.document_status = "Superseded"
            self.days_to_document_expiry = 0
            return
        if not self.expiry_date:
            self.document_status = "No Expiry Date"
            self.days_to_document_expiry = 0
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
        self.validate_revision_source(previous)
        previous.revision_status = "Superseded"
        previous.document_status = "Superseded"
        previous.days_to_document_expiry = 0
        previous.save()

    def restore_previous_revision(self):
        if not self.previous_revision or not frappe.db.exists("Lease Document", self.previous_revision):
            return

        previous = frappe.get_doc("Lease Document", self.previous_revision)
        if previous.docstatus == 2 or previous.revision_status != "Superseded":
            return

        current = frappe.db.get_value(
            "Lease Document",
            {
                "document_family_id": self.document_family_id,
                "revision_status": "Current",
                "docstatus": ["<", 2],
                "name": ["not in", [self.name, previous.name]],
            },
            "name",
        )
        if current:
            frappe.throw(
                _("Cannot restore {0} because current revision {1} already exists.").format(
                    previous.name, current
                )
            )

        previous.revision_status = "Current"
        previous.set_document_status()
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
