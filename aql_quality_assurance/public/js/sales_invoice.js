frappe.ui.form.on('Sales Invoice', {
    customer(frm) {
        if (!frm.doc.customer) return;

        frappe.call({
            method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.sales_invoice.sales_invoice.fetch_aql_from_customer",
            args: {
                customer: frm.doc.customer
            },
            callback(r) {
                if (r.message) {
                    frm.set_value(r.message);
                    frappe.show_alert({
                        message: __('AQL Parameters Populated'),
                        indicator: 'green'
                    });
                }
            }
        });
    }
});