frappe.views.calendar["Rent Schedule"] = {
	field_map: {
		start: "due_date",
		end: "due_date",
		id: "name",
		title: "description",
		status: "schedule_status",
	},
	style_map: {
		Planned: "info",
		Due: "warning",
		Paid: "success",
		Waived: "secondary",
		Overdue: "danger",
		Cancelled: "secondary",
	},
	get_events_method: "frappe.desk.calendar.get_events",
};
