frappe.query_reports["Upcoming Payments"] = {
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
			fieldname: "schedule_status",
			label: __("Schedule Status"),
			fieldtype: "Select",
			options: "\nPlanned\nDue\nPartially Paid\nPaid\nWaived\nOverdue\nCancelled",
		},
		{
			fieldname: "currency",
			label: __("Currency"),
			fieldtype: "Link",
			options: "Currency",
		},
	],
};

