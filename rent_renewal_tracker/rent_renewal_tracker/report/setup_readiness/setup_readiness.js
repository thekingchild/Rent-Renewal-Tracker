frappe.query_reports["Setup Readiness"] = {
	formatter(value, row, column, data, default_formatter) {
		const formatted = default_formatter(value, row, column, data);
		if (column.fieldname !== "status") {
			return formatted;
		}
		const color = data.ready ? "green" : "orange";
		return `<span class="indicator-pill ${color}">${formatted}</span>`;
	},
};
