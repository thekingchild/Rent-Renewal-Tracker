frappe.query_reports["Upcoming Expiries"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), 90),
			reqd: 1,
		},
		{
			fieldname: "responsible_department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Lease Department",
		},
		{
			fieldname: "responsible_officer",
			label: __("Responsible Officer"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "lease_status",
			label: __("Lease Status"),
			fieldtype: "Select",
			options: "\nActive\nExpiring Soon\nRenewal in Progress\nExpired",
		},
	],
};

