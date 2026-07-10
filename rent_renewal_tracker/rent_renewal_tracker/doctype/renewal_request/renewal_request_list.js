frappe.listview_settings["Renewal Request"] = {
	add_fields: ["workflow_state", "current_approver_role"],
	get_indicator(doc) {
		const colors = {
			Draft: "gray",
			"Department Review": "orange",
			"Finance Review": "orange",
			"Legal Review": "orange",
			"Management Approval": "orange",
			Approved: "green",
			Rejected: "red",
			Completed: "green",
		};
		const state = doc.workflow_state || "Draft";
		return [__(state), colors[state] || "gray", `workflow_state,=,${state}`];
	},
};

