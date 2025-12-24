frappe.ui.form.on('Quality Inspection', {
    // 1. When the form opens
    onload: function(frm) {
        if (frm.doc.reference_name && !frm.doc.custom_aql_party_name) {
            fetch_aql_data(frm);
        }
    },

    // 2. When the Reference ID is selected or changed
    reference_name: function(frm) {
        fetch_aql_data(frm);
    },

    // 3. When the Reference Type is selected or changed
    reference_type: function(frm) {
        fetch_aql_data(frm);
    },

    // 4. When the Item is selected or changed
    item_code: function(frm) {
        fetch_aql_data(frm);
    }   
});

function fetch_aql_data(frm) {
    if (frm.doc.reference_type && frm.doc.reference_name && frm.doc.item_code) {
        frappe.call({
            method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.quality_inspection.quality_inspection.set_aql_parameters",
            args: {
                doc: frm.doc
            },
            callback: function(r) {
                if (r.message) {
                    // Update the UI fields without saving yet
                    frm.set_value('custom_aql_party_name', r.message.custom_aql_party_name);
                    frm.set_value('custom_aql_party_type', r.message.custom_aql_party_type);
                    frm.set_value('custom_aql_lot_size', r.message.custom_aql_lot_size);
                    frm.set_value('custom_aql_inspection_level', r.message.custom_aql_inspection_level);
                    frm.set_value('custom_aql_critical_scale', r.message.custom_aql_critical_scale);
                    frm.set_value('custom_aql_major_scale', r.message.custom_aql_major_scale);
                    frm.set_value('custom_aql_minor_scale', r.message.custom_aql_minor_scale);

                    // Refresh the fields to show updated values
                    frm.refresh_field('custom_aql_party_name');
                    frm.refresh_field('custom_aql_party_type');
                    frm.refresh_field('custom_aql_lot_size');
                    frm.refresh_field('custom_aql_inspection_level');
                    frm.refresh_field('custom_aql_critical_scale');
                    frm.refresh_field('custom_aql_major_scale');
                    frm.refresh_field('custom_aql_minor_scale');
                }
            }
        });
    }
}