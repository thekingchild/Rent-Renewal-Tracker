frappe.query_reports["Rent Exposure"] = {
	filters: [
		{
			fieldname: "currency",
			label: __("Currency"),
			fieldtype: "Link",
			options: "Currency",
		},
		{
			fieldname: "responsible_department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Lease Department",
		},
		{
			fieldname: "region",
			label: __("Region"),
			fieldtype: "Data",
		},
		{
			fieldname: "lease_status",
			label: __("Lease Status"),
			fieldtype: "Select",
			options: "\nActive\nExpiring Soon\nRenewal in Progress\nExpired",
		},
	],
};

