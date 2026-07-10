frappe.views.calendar["Lease"] = {
	field_map: {
		start: "start_date",
		end: "end_date",
		id: "name",
		title: "lease_title",
		status: "lease_status",
	},
	style_map: {
		Active: "success",
		"Expiring Soon": "warning",
		"Renewal in Progress": "info",
		Expired: "danger",
		Terminated: "secondary",
	},
	get_events_method: "frappe.desk.calendar.get_events",
};
