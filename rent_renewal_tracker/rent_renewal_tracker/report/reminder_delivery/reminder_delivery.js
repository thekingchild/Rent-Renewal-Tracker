frappe.query_reports["Reminder Delivery"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nQueued\nSent\nFailed",
		},
		{
			fieldname: "channel",
			label: __("Channel"),
			fieldtype: "Select",
			options: "\nEmail\nSystem Notification",
		},
		{
			fieldname: "policy",
			label: __("Policy"),
			fieldtype: "Link",
			options: "Reminder Policy",
		},
		{
			fieldname: "lease",
			label: __("Lease"),
			fieldtype: "Link",
			options: "Lease",
		},
	],
};

