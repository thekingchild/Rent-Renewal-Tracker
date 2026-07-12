frappe.ui.form.on("Lease Document", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.revision_status === "Current") {
			frm.add_custom_button(__("Create Revision"), () => {
				frappe.new_doc("Lease Document", {
					lease: frm.doc.lease,
					renewal_request: frm.doc.renewal_request,
					title: frm.doc.title,
					category: frm.doc.category,
					document_date: frm.doc.document_date,
					effective_date: frm.doc.effective_date,
					expiry_date: frm.doc.expiry_date,
					confidentiality: frm.doc.confidentiality,
					previous_revision: frm.doc.name,
				});
			});
		}
		if (["Expired", "Expiring Soon"].includes(frm.doc.document_status)) {
			const color = frm.doc.document_status === "Expired" ? "red" : "orange";
			frm.dashboard.set_headline_alert(__("Document status: {0} (expiry {1})", [
				frm.doc.document_status,
				frappe.datetime.str_to_user(frm.doc.expiry_date),
			]), color);
		}
	},
});
