frappe.ui.form.on('Purchase Receipt', {
    supplier(frm) {
        if (!frm.doc.supplier) return;

        frappe.call({
            method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.purchase_receipt.purchase_receipt.fetch_aql_from_supplier",
            args: {
                supplier: frm.doc.supplier
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