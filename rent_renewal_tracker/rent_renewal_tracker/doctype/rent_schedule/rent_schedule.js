frappe.ui.form.on("Rent Schedule", {
	refresh(frm) {
		frm.toggle_reqd("payment_reference", ["Partially Paid", "Paid"].includes(frm.doc.payment_status));
		frm.toggle_reqd("paid_on", ["Partially Paid", "Paid"].includes(frm.doc.payment_status));
		frm.toggle_reqd("notes", frm.doc.payment_status === "Waived");
	},
	payment_status(frm) { frm.trigger("refresh"); },
});
