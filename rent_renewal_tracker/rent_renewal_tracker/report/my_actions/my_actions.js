frappe.query_reports["My Actions"] = {
	filters: [
		{
			fieldname: "action_type",
			label: __("Action Type"),
			fieldtype: "Select",
			options: "\nRenewal Approval\nOverdue Payment\nLease Expiry\nFailed Reminder",
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "Select",
			options: "\nCritical\nHigh\nMedium\nLow",
		},
	],
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		if (column.fieldname !== "priority") {
			return formatted;
		}
		const colors = { Critical: "red", High: "orange", Medium: "blue", Low: "gray" };
		return `<span class="indicator-pill ${colors[data.priority] || "gray"}">${formatted}</span>`;
	},
};
