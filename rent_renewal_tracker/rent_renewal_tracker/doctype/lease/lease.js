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
		const eligible = frm.doc.docstatus === 1 && ["Active", "Expiring Soon", "Expired"].includes(frm.doc.lease_status);
		if (eligible) {
			frm.add_custom_button(__("Start Renewal"), () => start_lifecycle(frm, "Renew"), __("Lifecycle"));
			frm.add_custom_button(__("Start Termination"), () => start_lifecycle(frm, "Terminate"), __("Lifecycle"));
		}
		if (frm.doc.last_renewal_request) {
			frm.add_custom_button(__("Open Current Request"), () => frappe.set_route("Form", "Renewal Request", frm.doc.last_renewal_request), __("Lifecycle"));
		}
	},
});

function start_lifecycle(frm, action) {
	frappe.call({
		method: "rent_renewal_tracker.rent_renewal_tracker.doctype.lease.lease.start_lifecycle_request",
		args: { lease: frm.doc.name, action },
		freeze: true,
		callback: (response) => response.message && frappe.set_route("Form", "Renewal Request", response.message),
	});
}
