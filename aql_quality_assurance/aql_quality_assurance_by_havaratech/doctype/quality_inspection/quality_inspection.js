/*************************************************
 * QUALITY INSPECTION – AQL SCRIPT (FIXED)
 *************************************************/

frappe.ui.form.on('Quality Inspection', {
    refresh(frm) {
        console.log("AQL script refresh fired");

        frm.add_custom_button(
            __('1 - Refresh AQL'),
            () => refresh_aql_values(frm),
            __('Actions')
        );

        // frm.add_custom_button(
        //     __('Calculate AQL'),
        //     () => calculate_aql_for_quality_inspection(frm),
        //     __('Actions')
        // );
    }
});

/*************************************************
 * SERVER CALL – WORKING
 *************************************************/

function refresh_aql_values(frm) {

    frappe.call({
        method: "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.quality_inspection.quality_inspection.set_aql_parameters",
        args: { doc: frm.doc },
        callback(r) {

            if (!r.message) {
                frappe.msgprint("No AQL data returned");
                return;
            }

            const d = r.message;

            frm.set_value("custom_aql_party_name", d.custom_aql_party_name);
            frm.set_value("custom_aql_party_type", d.custom_aql_party_type);
            frm.set_value("custom_aql_inspection_level", d.custom_aql_inspection_level);
            frm.set_value("custom_aql_critical_scale", d.custom_aql_critical_scale);
            frm.set_value("custom_aql_major_scale", d.custom_aql_major_scale);
            frm.set_value("custom_aql_minor_scale", d.custom_aql_minor_scale);
            frm.set_value("custom_aql_lot_size", d.custom_aql_lot_size);

            frm.refresh_fields();

            frappe.show_alert({
                message: __('AQL values refreshed'),
                indicator: 'green'
            });
        }
    });
}

/*************************************************
 * AQL STEP-1 : SAMPLE SIZE CALCULATION
 * ERPNext – Quality Inspection
 *************************************************/

/*************************************************
 * AQL LOOKUP TABLES & HELPERS (MUST BE ON TOP)
 *************************************************/

const AQLLetters = {
    "I-8":"A","I-15":"B","I-25":"C","I-50":"D","I-90":"E","I-150":"F",
    "I-280":"G","I-500":"H","I-1200":"J","I-3200":"K","I-10000":"L",
    "I-35000":"M","I-150000":"N","I-500000":"P","I-500001":"Q",

    "II-8":"A","II-15":"B","II-25":"C","II-50":"D","II-90":"E","II-150":"F",
    "II-280":"G","II-500":"H","II-1200":"J","II-3200":"K","II-10000":"L",
    "II-35000":"M","II-150000":"N","II-500000":"P","II-500001":"Q",

    "III-8":"B","III-15":"C","III-25":"D","III-50":"E","III-90":"F","III-150":"G",
    "III-280":"H","III-500":"J","III-1200":"K","III-3200":"L","III-10000":"M",
    "III-35000":"N","III-150000":"P","III-500000":"Q","III-500001":"Q"
};

const AQLSampleSizeByLetter = {
    "A": 2,
    "B": 3,
    "C": 5,
    "D": 8,
    "E": 13,
    "F": 20,
    "G": 32,
    "H": 50,
    "J": 80,
    "K": 125,
    "L": 200,
    "M": 315,
    "N": 500,
    "P": 500,
    "Q": 500
};

function normalize_lot_size(qty) {
    if (qty <= 8) return 8;
    if (qty <= 15) return 15;
    if (qty <= 25) return 25;
    if (qty <= 50) return 50;
    if (qty <= 90) return 90;
    if (qty <= 150) return 150;
    if (qty <= 280) return 280;
    if (qty <= 500) return 500;
    if (qty <= 1200) return 1200;
    if (qty <= 3200) return 3200;
    if (qty <= 10000) return 10000;
    if (qty <= 35000) return 35000;
    if (qty <= 150000) return 150000;
    if (qty <= 500000) return 500000;
    return 500001;
}

function normalize_inspection_level(level) {
    if (!level) return null;

    // "Gen II" → "II"
    if (level.includes("I")) {
        return level.replace("Gen", "").trim();
    }

    return level.trim();
}

function get_sample_size(lot_size, inspection_level) {

    const normalized_lot = normalize_lot_size(lot_size);
    const normalized_level = normalize_inspection_level(inspection_level);

    const key = normalized_level + "-" + normalized_lot;
    const letter = AQLLetters[key];

    if (!letter) {
        console.error("AQL Letter not found for", key);
        return null;
    }

    const sample = AQLSampleSizeByLetter[letter];

    if (!sample) {
        console.error("Sample size not found for letter", letter);
        return null;
    }

    return {
        letter: letter,
        sample_size: sample
    };
}

/*************************************************
 * QUALITY INSPECTION FORM SCRIPT
 *************************************************/

frappe.ui.form.on('Quality Inspection', {
    refresh(frm) {

        frm.add_custom_button(
            __('2 - Calculate Sample Size (AQL)'),
            () => calculate_aql_sample_size(frm),
            __('Actions')
        );
    }
});

/*************************************************
 * MAIN CALCULATION – STEP-1 ONLY
 *************************************************/

function calculate_aql_sample_size(frm) {

    if (!frm || !frm.doc) return;

    const lot = frm.doc.custom_aql_lot_size;
    const level = frm.doc.custom_aql_inspection_level;

    if (!lot || !level) {
        frappe.msgprint("Lot size or Inspection Level is missing");
        return;
    }

    const result = get_sample_size(lot, level);

    if (!result) {
        frappe.msgprint("Unable to calculate sample size");
        return;
    }

    frm.set_value("sample_size", result.sample_size);

    frappe.show_alert({
        message: __('Sample Size calculated (Code Letter: ' + result.letter + ')'),
        indicator: 'green'
    });

    console.log("AQL STEP-1 RESULT", result);
}

/*************************************************
 * AQL ACCEPT / REJECT TABLE (STEP-2)
 *************************************************/

const AQLAcceptReject = {
    "A0.065":"0,1","A0.10":"0,1","A0.15":"0,1","A0.25":"0,1","A0.40":"0,1","A0.65":"0,1","A1.0":"0,1","A1.5":"0,1","A2.5":"0,1","A4.0":"0,1","A6.5":"0,1",
    "B0.065":"0,1","B0.10":"0,1","B0.15":"0,1","B0.25":"0,1","B0.40":"0,1","B0.65":"0,1","B1.0":"0,1","B1.5":"0,1","B2.5":"0,1","B4.0":"0,1","B6.5":"0,1",
    "C0.065":"0,1","C0.10":"0,1","C0.15":"0,1","C0.25":"0,1","C0.40":"0,1","C0.65":"0,1","C1.0":"0,1","C1.5":"0,1","C2.5":"0,1","C4.0":"0,1","C6.5":"1,2",
    "D0.065":"0,1","D0.10":"0,1","D0.15":"0,1","D0.25":"0,1","D0.40":"0,1","D0.65":"0,1","D1.0":"0,1","D1.5":"0,1","D2.5":"0,1","D4.0":"1,2","D6.5":"1,2",
    "E0.065":"0,1","E0.10":"0,1","E0.15":"0,1","E0.25":"0,1","E0.40":"0,1","E0.65":"0,1","E1.0":"0,1","E1.5":"0,1","E2.5":"1,2","E4.0":"1,2","E6.5":"2,3",
    "F0.065":"0,1","F0.10":"0,1","F0.15":"0,1","F0.25":"0,1","F0.40":"0,1","F0.65":"0,1","F1.0":"0,1","F1.5":"1,2","F2.5":"1,2","F4.0":"2,3","F6.5":"3,4",
    "G0.065":"0,1","G0.10":"0,1","G0.15":"0,1","G0.25":"0,1","G0.40":"0,1","G0.65":"0,1","G1.0":"1,2","G1.5":"1,2","G2.5":"2,3","G4.0":"3,4","G6.5":"5,6",
    "H0.065":"0,1","H0.10":"0,1","H0.15":"0,1","H0.25":"0,1","H0.40":"0,1","H0.65":"1,2","H1.0":"1,2","H1.5":"2,3","H2.5":"3,4","H4.0":"5,6","H6.5":"7,8",
    "J0.065":"0,1","J0.10":"0,1","J0.15":"0,1","J0.25":"0,1","J0.40":"1,2","J0.65":"1,2","J1.0":"2,3","J1.5":"3,4","J2.5":"5,6","J4.0":"7,8","J6.5":"10,11",
    "K0.065":"0,1","K0.10":"0,1","K0.15":"0,1","K0.25":"1,2","K0.40":"1,2","K0.65":"2,3","K1.0":"3,4","K1.5":"5,6","K2.5":"7,8","K4.0":"10,11","K6.5":"14,15",
    "L0.065":"0,1","L0.10":"0,1","L0.15":"1,2","L0.25":"1,2","L0.40":"2,3","L0.65":"3,4","L1.0":"5,6","L1.5":"7,8","L2.5":"10,11","L4.0":"14,15","L6.5":"21,22",
    "M0.065":"0,1","M0.10":"1,2","M0.15":"1,2","M0.25":"2,3","M0.40":"3,4","M0.65":"5,6","M1.0":"7,8","M1.5":"10,11","M2.5":"14,15","M4.0":"21,22","M6.5":"21,22",
    "N0.065":"1,2","N0.10":"1,2","N0.15":"2,3","N0.25":"3,4","N0.40":"5,6","N0.65":"7,8","N1.0":"10,11","N1.5":"14,15","N2.5":"21,22","N4.0":"21,22","N6.5":"21,22",
    "P0.065":"1,2","P0.10":"2,3","P0.15":"3,4","P0.25":"5,6","P0.40":"7,8","P0.65":"10,11","P1.0":"14,15","P1.5":"21,22","P2.5":"21,22","P4.0":"21,22","P6.5":"21,22",
    "Q0.065":"2,3","Q0.10":"3,4","Q0.15":"5,6","Q0.25":"7,8","Q0.40":"10,11","Q0.65":"14,15","Q1.0":"21,22","Q1.5":"21,22","Q2.5":"21,22","Q4.0":"21,22","Q6.5":"21,22"
};

function get_accept_reject(letter, aql) {

    if (!letter || !aql) return null;

    const key = letter + aql;
    const row = AQLAcceptReject[key];

    if (!row) {
        console.error("AQL scale mismatch for", key);
        return null;
    }

    const [accept, reject] = row.split(",").map(Number);

    return {
        accept: accept,
        reject: reject
    };
}

function calculate_aql_accept_reject(frm) {

    const lot = frm.doc.custom_aql_lot_size;
    const level = frm.doc.custom_aql_inspection_level;

    if (!lot || !level) {
        frappe.msgprint("Lot size or Inspection Level missing");
        return;
    }

    // Step-1 result (already proven working)
    const base = get_sample_size(lot, level);
    if (!base) return;

    const letter = base.letter;

    const critical = get_accept_reject(letter, frm.doc.custom_aql_critical_scale);
    const major    = get_accept_reject(letter, frm.doc.custom_aql_major_scale);
    const minor    = get_accept_reject(letter, frm.doc.custom_aql_minor_scale);

    if (!critical || !major || !minor) {
        frappe.msgprint("AQL calculation failed – scale mismatch");
        return;
    }

    // Sample size already fixed
    frm.set_value("sample_size", base.sample_size);

    frm.set_value("custom_aql_critical_acceptable_limit", critical.accept);
    //frm.set_value("custom_aql_critical_reject", critical.reject);

    frm.set_value("custom_aql_major_acceptable_limit", major.accept);
    //frm.set_value("custom_aql_major_reject", major.reject);

    frm.set_value("custom_aql_minor_acceptable_limit", minor.accept);
    //frm.set_value("custom_aql_minor_reject", minor.reject);

    frappe.show_alert({
        message: __('AQL Accept / Reject calculated (Code ' + letter + ')'),
        indicator: 'green'
    });

    console.log("AQL STEP-2 COMPLETE", {
        letter, critical, major, minor
    });
}

frappe.ui.form.on('Quality Inspection', {
    refresh(frm) {
        frm.add_custom_button(
            __('3 - Calculate AQL Accept / Reject'),
            () => calculate_aql_accept_reject(frm),
            __('Actions')
        );
    }
});
