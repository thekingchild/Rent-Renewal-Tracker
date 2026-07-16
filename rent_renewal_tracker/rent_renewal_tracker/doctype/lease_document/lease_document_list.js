frappe.listview_settings["Lease Document"] = {
	add_fields: ["document_status", "expiry_date", "revision_number", "docstatus", "legacy_unsubmitted"],
	get_indicator(doc) {
		const colors = {
			Draft: "blue",
			"No Expiry Date": "gray",
			Current: "green",
			"Expiring Soon": "orange",
			Expired: "red",
			Superseded: "gray",
			Cancelled: "red",
		};
		const status = doc.document_status || "Draft";
		return [__(status), colors[status] || "gray", `document_status,=,${status}`];
	},
};
