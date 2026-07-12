frappe.ui.form.on("Lease", {
	setup(frm) {
		frm.set_query("property", () => ({ filters: { active: 1 } }));
		frm.set_query("landlord", () => ({ filters: { active: 1 } }));
		frm.set_query("responsible_department", () => ({ filters: { disabled: 0 } }));
	},
	refresh(frm) {
		if (frm.doc.confidentiality_classification === "Restricted") {
			frm.dashboard.set_headline_alert(__("Restricted lease: access, exports, and attachments are limited to assigned authorized users."), "red");
		}
		if (!frm.is_new() && frm.doc.next_action_date) {
			frm.dashboard.add_comment(__("Next contractual action: {0}", [frappe.datetime.str_to_user(frm.doc.next_action_date)]), "blue", true);
		}
	},
});
