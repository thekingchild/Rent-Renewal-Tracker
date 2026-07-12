frappe.listview_settings["Lease"] = {
	add_fields: ["lease_status", "end_date", "renewal_status"],
	get_indicator(doc) {
		const colors = {
			Draft: "gray",
			Active: "green",
			"Expiring Soon": "orange",
			"Renewal in Progress": "blue",
			"Termination in Progress": "orange",
			Renewed: "green",
			Expired: "red",
			Terminated: "gray",
		};
		const status = doc.lease_status || "Draft";
		return [__(status), colors[status] || "gray", `lease_status,=,${status}`];
	},
};
