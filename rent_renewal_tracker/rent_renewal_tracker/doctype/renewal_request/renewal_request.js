frappe.ui.form.on("Renewal Request", {
	refresh(frm) {
		const fields = ["start_date", "end_date", "currency", "monthly_rent", "annual_rent", "payment_frequency"];
		const changed = fields.filter((field) => String(frm.doc[`current_${field}`] || "") !== String(frm.doc[`proposed_${field}`] || ""));
		if (changed.length) {
			frm.dashboard.set_headline_alert(__("Changed proposed terms: {0}", [changed.map((field) => __(frappe.model.unscrub(field))).join(", ")]), "orange");
		}
		if (frm.doc.current_approver_role) {
			frm.dashboard.add_comment(__("Pending with: {0}", [frm.doc.current_approver_role]), "blue", true);
		}
	},
});
