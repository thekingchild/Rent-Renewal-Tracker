frappe.ui.form.on("Lease", {
	setup(frm) {
		frm.set_query("property", () => ({ filters: { active: 1 } }));
		frm.set_query("landlord", () => ({ filters: { active: 1 } }));
		frm.set_query("responsible_department", () => ({ filters: { disabled: 0 } }));
	},
	refresh(frm) {
		show_overlap_warning(frm);
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
	property(frm) { check_overlap(frm); },
	start_date(frm) { check_overlap(frm); },
	end_date(frm) { check_overlap(frm); },
});

function check_overlap(frm) {
	if (!frm.doc.property || !frm.doc.start_date || !frm.doc.end_date) return;
	frappe.call({
		method: "rent_renewal_tracker.rent_renewal_tracker.doctype.lease.lease.check_property_lease_overlap",
		args: {
			property_name: frm.doc.property,
			start_date: frm.doc.start_date,
			end_date: frm.doc.end_date,
			exclude_lease: frm.is_new() ? null : frm.doc.name,
		},
		callback: ({ message }) => {
			if (!message?.has_conflict) return;
			const visible = message.visible_conflicts || [];
			const detail = visible.length
				? __(" Conflicting Lease(s): {0}.", [visible.map((row) => row.name).join(", ")])
				: "";
			frappe.show_alert({
				message: __("This property has an ongoing Lease that overlaps the selected period.") + detail,
				indicator: "red",
			}, 8);
		},
	});
}

function show_overlap_warning(frm) {
	if (frm.doc.overlap_review_required) {
		frm.dashboard.set_headline_alert(
			__("Existing overlapping Lease period: review the Property and term before changing them."),
			"red",
		);
	}
}

function start_lifecycle(frm, action) {
	frappe.call({
		method: "rent_renewal_tracker.rent_renewal_tracker.doctype.lease.lease.start_lifecycle_request",
		args: { lease: frm.doc.name, action },
		freeze: true,
		callback: (response) => response.message && frappe.set_route("Form", "Renewal Request", response.message),
	});
}
