frappe.ui.form.on("Rent Schedule", {
	refresh(frm) {
		frm.toggle_reqd("notes", frm.doc.payment_status === "Waived");
		if (frm.doc.payment_reconciliation_required) {
			frm.dashboard.set_headline_alert(__("Legacy partial payment requires reconciliation. Record the total amount paid to date."), "orange");
		}
		const can_write = Boolean(frm.perm?.[0]?.write);
		if (can_write && frm.doc.docstatus < 2 && frm.doc.payment_status !== "Waived" && flt(frm.doc.outstanding_balance) > 0) {
			frm.add_custom_button(__("Record Payment"), () => record_payment(frm), __("Payments"));
		}
		if (can_write && frm.doc.lease && frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Fetch Lease Financials"), () => fetch_lease_financials(frm), __("Amounts"));
		}
	},
	lease(frm) { fetch_lease_financials(frm); },
	payment_status(frm) { frm.trigger("refresh"); },
});

function fetch_lease_financials(frm) {
	if (!frm.doc.lease) {
		return;
	}
	frappe.call({
		method: "rent_renewal_tracker.rent_renewal_tracker.doctype.rent_schedule.rent_schedule.get_lease_financial_defaults",
		args: {
			lease: frm.doc.lease,
			period_from: frm.doc.period_from,
			period_to: frm.doc.period_to,
		},
		callback: ({ message }) => {
			if (!message) return;
			for (const fieldname of ["currency", "base_rent", "service_charge", "tax"]) {
				if ([null, undefined, ""].includes(frm.doc[fieldname]) && message[fieldname] !== null) {
					frm.set_value(fieldname, message[fieldname]);
				}
			}
			if (message.requires_manual_amount && message.message) {
				frappe.show_alert({ message: message.message, indicator: "orange" }, 8);
			}
			frm.refresh_fields(["currency", "base_rent", "service_charge", "tax"]);
		},
	});
}

function record_payment(frm) {
	const maximum = flt(frm.doc.outstanding_balance);
	frappe.prompt(
		[
			{ fieldname: "payment_date", fieldtype: "Date", label: __("Payment Date"), default: frappe.datetime.get_today(), reqd: 1 },
			{ fieldname: "amount", fieldtype: "Currency", label: __("Amount"), default: maximum, reqd: 1 },
			{ fieldname: "reference", fieldtype: "Data", label: __("Reference"), reqd: 1 },
			{ fieldname: "payment_method", fieldtype: "Select", label: __("Payment Method"), options: "Bank Transfer\nCash\nCheque\nCard\nJournal Entry\nOther" },
			{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes") },
		],
		(values) => {
			const amount = flt(values.amount);
			if (amount <= 0 || amount > maximum) {
				frappe.msgprint(__("Payment must be greater than zero and cannot exceed the outstanding balance."));
				return;
			}
			frm.add_child("payments", values);
			frm.refresh_field("payments");
			frm.save();
		},
		__("Record Payment"),
		__("Add Payment"),
	);
}
