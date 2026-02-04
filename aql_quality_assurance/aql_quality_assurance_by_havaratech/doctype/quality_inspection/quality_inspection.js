//***************************************************************//
// Keep reading_1 and reading_value read-only based on numeric flag
//***************************************************************//

frappe.ui.form.on('Quality Inspection', {
    refresh(frm) {
        console.log("Readonly logic applied on refresh");
        // Ensure rules are applied after grid renders
        frm.fields_dict.readings.grid.refresh();
        setTimeout(() => apply_all_aql_rules(frm), 100); // Delay to ensure grid rows are ready
    },
    onload(frm) {
        console.log("Readonly logic applied on form load");
        setTimeout(() => apply_all_aql_rules(frm), 100); // Apply rules on form load
    },
    validate(frm) {
        console.log("Readonly logic applied on validate");
        apply_all_aql_rules(frm); // Apply rules before saving
    },
    change(frm) {
        console.log("Readonly logic applied on change");
        apply_all_aql_rules(frm); // Apply rules on any change
    },
    refresh(frm){
        console.log("Form reloaded - applied readonly")
        apply_all_aql_rules(frm);
    }
});

frappe.ui.form.on('Quality Inspection Reading', {
    numeric(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        console.log("Readonly logic applied on numeric toggle");
        apply_row_rule(frm, row);
    },
    reading_1(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        console.log("Readonly logic applied on reading_1 change");
        apply_row_rule(frm, row);
    },
    reading_value(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        console.log("Readonly logic applied on reading_value change");
        apply_row_rule(frm, row);
    }
});

/* ------------------------------------------------ */

function apply_all_aql_rules(frm) {
    if (!frm.doc.readings) return;
    frm.doc.readings.forEach(row => {
        apply_row_rule(frm, row);
    });
}

function apply_row_rule(frm, row) {
    const grid = frm.fields_dict.readings.grid;
    const grid_row = grid.grid_rows_by_docname[row.name];
    console.log("Grid row:", grid_row); // Debugging log
    if (!grid_row) {
        console.log("Grid row not found for row:", row.name); // Debugging log
        return;
    }

    const is_numeric = cint(row.numeric);

    const $reading_1 = grid_row.row.find('[data-fieldname="reading_1"] input');
    const $reading_value = grid_row.row.find('[data-fieldname="reading_value"] input');

    console.log("Selectors for reading_1 and reading_value:", $reading_1, $reading_value); // Debugging log

    if (is_numeric) {
        enable($reading_1);
        disable($reading_value);
    } else {
        disable($reading_1);
        enable($reading_value);
    }
}

/* ------------------------------------------------ */

function disable($el) {
    $el.prop('readonly', true)
       .addClass('aql-readonly');
}

function enable($el) {
    $el.prop('readonly', false)
       .removeClass('aql-readonly');
}

/* ------------------------------------------------ */
/* Grey background for readonly */

(() => {
    if (document.getElementById('aql-style')) return;

    const style = document.createElement('style');
    style.id = 'aql-style';
    style.innerHTML = `
        .aql-readonly {
            background-color: #f3f3f3 !important;
            color: #666 !important;
            cursor: not-allowed;
        }
    `;
    document.head.appendChild(style);
})();
//**************************************************************************************************************************************************************//
// Auto-Run AQL Logic on New Quality Inspection Forms
//**************************************************************************************************************************************************************//
frappe.ui.form.on("Quality Inspection", {
    refresh: function(frm) {
        // 1. Only run for new documents
        if (!frm.is_new()) return;
        
        // 2. Prevent running if already done
        if (frm.__aql_done) return;

        // 3. Show a visual message so you know the script is alive
        frappe.show_alert({
            message: __('Waiting for template rows...'),
            indicator: 'orange'
        });

        // 4. Start the 5-second "Brute Force" loop
        let attempts = 0;
        const max_attempts = 5; // 5 attempts * 1000ms = 5 Seconds

        const interval_id = setInterval(() => {
            attempts++;
            console.log(`[AQL Check] Attempt ${attempts}: Checking for readings...`);

            // CHECK: Do we have readings rows yet?
            if (frm.doc.readings && frm.doc.readings.length > 0) {
                
                // FOUND THEM! Stop the timer immediately.
                clearInterval(interval_id);
                
                // Run the logic
                if (!frm.__aql_done) {
                    frm.__aql_done = true;
                    console.log("[AQL Check] Rows found! Running Logic.");
                    run_aql_force(frm);
                }
            } 
            else if (attempts >= max_attempts) {
                // TIME'S UP: Stop checking to save memory
                clearInterval(interval_id);
                console.log("[AQL Check] Timed out. No rows found.");
            }

        }, 1000); // Check every 1 second
    }
});

function run_aql_force(frm) {
    frappe.call({
        method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.quality_inspection.quality_inspection.refresh_aql_logic",
        args: { doc: frm.doc },
        freeze: true,
        freeze_message: __("Calculating & Populating Values..."),
        callback: function (r) {
            if (r.message) {
                // Use a safe update method to avoid the 'parent' error
                // We wrap this in a try-catch block just in case
                try {
                    // Update the form data
                    frm.set_value(r.message).then(() => {
                        frm.refresh_fields();
                        frappe.show_alert({ message: __('AQL Data Populated!'), indicator: 'green' });
                    });
                } catch (e) {
                    console.error("AQL Population Error:", e);
                    // Fallback: If set_value fails, force refresh
                    frappe.model.sync(r.message);
                    frm.refresh();
                }
            }
        }
    });
}
//--------------------------------------------------------------------------------------------------------------------------------------------------------------//
// Quality Inspection Status Indicator
//--------------------------------------------------------------------------------------------------------------------------------------------------------------//
frappe.ui.form.on("Quality Inspection", {
    refresh(frm) {
        // Clear any previously set custom indicator
        frm.page.clear_indicator();

        const status = frm.doc.status;
        const docstatus = frm.doc.docstatus;

        // Nothing to show
        if (!status && docstatus === 0) return;

        let label = null;
        let color = null;

        // -------------------------------
        // DRAFT (docstatus = 0)
        // -------------------------------
        if (docstatus === 0) {
            if (status === "Pending") {
                label = "Draft - Pending";
                color = "orange";
            }
            else if (status === "On Hold") {
                label = "Draft - On Hold";
                color = "pink";
            }
            else if (status === "Accepted") {
                label = "Draft - Accepted";
                color = "green";
            }
            else if (status === "Rejected") {
                label = "Draft - Rejected";
                color = "red";
            }
        }

        // -------------------------------
        // SUBMITTED (docstatus = 1)
        // -------------------------------
        else if (docstatus === 1) {
            if (status === "Accepted") {
                label = "Submitted - Accepted";
                color = "green";
            }
            else if (status === "Rejected") {
                label = "Submitted - Rejected";
                color = "red";
            }
        }

        // -------------------------------
        // CANCELLED (docstatus = 2)
        // -------------------------------
        else if (docstatus === 2) {
            label = "Cancelled";
            color = "red";
        }

        // Add indicator beside Draft / Submitted
        if (label && color) {
            frm.page.set_indicator(label, color);
        }
    }
});
