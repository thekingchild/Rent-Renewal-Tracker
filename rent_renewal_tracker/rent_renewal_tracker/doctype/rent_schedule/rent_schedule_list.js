frappe.listview_settings["Rent Schedule"] = {
	add_fields: ["schedule_status", "payment_status", "due_date"],
	get_indicator(doc) {
		const colors = {
			Planned: "blue",
			Due: "orange",
			Paid: "green",
			Waived: "gray",
			Overdue: "red",
			Cancelled: "gray",
		};
		const status = doc.schedule_status || "Planned";
		return [__(status), colors[status] || "gray", `schedule_status,=,${status}`];
	},
};

