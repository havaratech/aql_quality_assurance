// frappe.ui.form.on('Delivery Note', {
//     customer(frm) {
//         if (!frm.doc.customer) return;

//         frappe.call({
//             method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.delivery_note.delivery_note.fetch_aql_from_customer",
//             args: {
//                 customer: frm.doc.customer
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


frappe.ui.form.on("Delivery Note", {
    onload(frm) {
        fetch_aql_dn(frm);
    },

    customer(frm) {
        fetch_aql_dn(frm);
    }
});

frappe.ui.form.on("Delivery Note Item", {
    item_code(frm) {
        fetch_aql_dn(frm);
    }
});

function fetch_aql_dn(frm) {
    // 🔒 HARD GUARDS (same pattern as PR)
    if (!frm.doc.customer) return;
    if (!frm.doc.items || !frm.doc.items.length) return;
    if (!frm.doc.items[0].item_code) return;

    frappe.call({
        method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.delivery_note.delivery_note.fetch_aql_from_customer",
        args: {
            customer: frm.doc.customer,
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
