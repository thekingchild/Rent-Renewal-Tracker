frappe.query_reports["Renewal Pipeline"] = {
	filters: [
		{
			fieldname: "workflow_state",
			label: __("Workflow State"),
			fieldtype: "Select",
			options: "\nDraft\nDepartment Review\nFinance Review\nLegal Review\nManagement Approval\nApproved\nRejected\nCompleted",
		},
		{
			fieldname: "responsible_department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Lease Department",
		},
		{
			fieldname: "recommendation",
			label: __("Recommendation"),
			fieldtype: "Select",
			options: "\nRenew\nRenegotiate\nRelocate\nTerminate",
		},
	],
};

