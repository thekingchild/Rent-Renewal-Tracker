frappe.listview_settings["Lease Document"] = {
	add_fields: ["document_status", "expiry_date", "revision_number"],
	get_indicator(doc) {
		const colors = {
			"No Expiry Date": "gray",
			Current: "green",
			"Expiring Soon": "orange",
			Expired: "red",
			Superseded: "gray",
		};
		const status = doc.document_status || "No Expiry Date";
		return [__(status), colors[status] || "gray", `document_status,=,${status}`];
	},
};
