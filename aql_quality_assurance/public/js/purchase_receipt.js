// frappe.ui.form.on('Purchase Receipt', {
//     supplier(frm) {
//         if (!frm.doc.supplier) return;

//         frappe.call({
//             method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.purchase_receipt.purchase_receipt.fetch_aql_from_supplier",
//             args: {
//                 supplier: frm.doc.supplier
//             },
//             callback(r) {
//                 if (r.message) {
//                     frm.set_value(r.message);
//                     frappe.show_alert({
//                         message: __('AQL Parameters Populated'),
//                         indicator: 'green'
//                     });
//                 }
//             }
//         });
//     }
// });

frappe.ui.form.on("Purchase Receipt", {
    onload(frm) {
        fetch_aql(frm);
    },

    supplier(frm) {
        fetch_aql(frm);
    }
});

frappe.ui.form.on("Purchase Receipt Item", {
    item_code(frm) {
        fetch_aql(frm);
    }
});

function fetch_aql(frm) {
    // HARD GUARDS (THIS FIXES YOUR ERROR)
    if (!frm.doc.supplier) return;
    if (!frm.doc.items || !frm.doc.items.length) return;
    if (!frm.doc.items[0].item_code) return;

    frappe.call({
        method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.purchase_receipt.purchase_receipt.fetch_aql_from_supplier",
        args: {
            supplier: frm.doc.supplier,
            item_code: frm.doc.items[0].item_code
        },
        callback: function (r) {
            if (r.message) {
                frm.set_value("custom_aql_inspection_level", r.message.custom_aql_inspection_level);
                frm.set_value("custom_aql_critical_scale", r.message.custom_aql_critical_scale);
                frm.set_value("custom_aql_major_scale", r.message.custom_aql_major_scale);
                frm.set_value("custom_aql_minor_scale", r.message.custom_aql_minor_scale);
            }
        }
    });
}
