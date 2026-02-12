import frappe
from frappe.utils import now, getdate

# =================================================
# AQL LEVEL ORDER (FOR COMPARISON / REPORTING)
# =================================================

AQL_ORDER = ["Gen I", "Gen II", "Gen III", "Spl I", "Spl II", "Spl III", "Spl IV"]

# =================================================
# MAIN ENTRY
# =================================================

def process_supplier_aql(supplier, start_date, end_date):
    """ Create or update Supplier AQL Performance Report using explicit bucket-based AQL logic. """

    start_date = getdate(start_date)
    end_date = getdate(end_date)

    # ---------------------------------------
    # Load AQL Settings (Single DocType)
    # ---------------------------------------
    settings = frappe.get_single("AQL Settings")

    gen_1_max = settings.supplier_gen_i_max
    gen_2_max = settings.supplier_gen_ii_max

    spl_1_max = settings.supplier_spl_i_max
    spl_2_max = settings.supplier_spl_ii_max
    spl_3_max = settings.supplier_spl_iii_max

    minimum_inspections = settings.aql_batch_minimum_sample_size or 0
    # ---------------------------------------
    # Aggregate Quality Inspections
    # ---------------------------------------
    result = frappe.db.sql(
        """
        SELECT
            COUNT(*) AS total,
            SUM(status = 'Accepted') AS accepted,
            SUM(status = 'Rejected') AS rejected,
            SUM(status = 'Pending') AS pending
        FROM `tabQuality Inspection`
        WHERE
            docstatus = 1
            AND custom_aql_party_types = 'Supplier'
            AND custom_aql_party_names = %s
            AND report_date BETWEEN %s AND %s
        """,
        (supplier, start_date, end_date),
        as_dict=True,
    )[0]

    if not result.total:
        return

    acceptance_pct = (result.accepted / result.total) * 100
    rejection_pct = (result.rejected / result.total) * 100

    # ---------------------------------------
    # Fetch Previous Snapshot
    # ---------------------------------------
    prev = get_previous_aql_snapshot(supplier)

    previous_level = (
        prev.current_aql_level if prev and prev.current_aql_level else "Gen II"
    )

    previous_rejection_pct = (
        prev.rejection_percentage if prev else None
    )

    # ----------------------------------------------------------------------------------------
    # DECISION ENGINE (ULTRA-EXPLICIT) WITH MINIMUM SAMPLE SIZE CHECK
    # ----------------------------------------------------------------------------------------
    if result.total < minimum_inspections:
        current_level = previous_level
        raw_decision = (
            f"Hold (Insufficient sample size: {result.total} < {minimum_inspections})"
        ) 
    else:
        current_level, raw_decision = decide_aql_ultra_explicit(
            prev_level=previous_level,
            rejection_pct=rejection_pct,
            gen_1_max=gen_1_max,
            gen_2_max=gen_2_max,
            spl_1_max=spl_1_max,
            spl_2_max=spl_2_max,
            spl_3_max=spl_3_max,
        )

    normalized_decision = normalize_decision(
        previous_level,
        current_level
    )

    # ---------------------------------------
    # Update Supplier Master
    # ---------------------------------------
    update_supplier_master_aql_level(
        supplier=supplier,
        previous_level=previous_level,
        current_level=current_level,
        decision=normalized_decision,
    )

    # ---------------------------------------
    # UPSERT Performance Report
    # ---------------------------------------
    existing = frappe.get_all(
        "Supplier AQL Performance Report",
        filters={
            "reference_type": "Supplier",
            "aql_party_names": supplier,
            "inspection_start_from": start_date,
            "inspection_end_to": end_date,
        },
        pluck="name",
    )

    values = {
        "total_quality_inspection": result.total,
        "accepted_inspection": result.accepted,
        "rejected_inspection": result.rejected,
        "pending_inspection": result.pending,
        "acceptance_percentage": acceptance_pct,
        "rejection_percentage": rejection_pct,
        "previous_aql_level": previous_level,
        "current_aql_level": current_level,
        "last_decision": normalized_decision,
        "last_decision_on": now(),
        "decision_reason": build_decision_reason(
            supplier=supplier,
            total=result.total,
            accepted=result.accepted,
            rejected=result.rejected,
            prev_pct=previous_rejection_pct,
            curr_pct=rejection_pct,
            decision=raw_decision,
        ),
    }

    if existing:
        doc = frappe.get_doc(
            "Supplier AQL Performance Report",
            existing[0]
        )
        doc.update(values)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Supplier AQL Performance Report",
                "reference_type": "Supplier",
                "aql_party_names": supplier,
                "inspection_start_from": start_date,
                "inspection_end_to": end_date,
                **values,
            }
        )
        doc.insert(ignore_permissions=True)

# =================================================
# DECISION ENGINE (ULTRA-EXPLICIT BUCKET LOGIC)
# =================================================

def decide_aql_ultra_explicit(
    prev_level,
    rejection_pct,
    gen_1_max,
    gen_2_max,
    spl_1_max,
    spl_2_max,
    spl_3_max,
):
    """
    Explicit bucket logic with readable ranges.
    No Gen ↔ Spl crossover.
    """

    if not prev_level:
        prev_level = "Gen II"

    # =========================
    # GEN FAMILY
    # =========================
    if prev_level.startswith("Gen"):

        # Gen I
        if rejection_pct <= gen_1_max:
            return "Gen I", "Gen I (rejection ≤ Gen I max)"

        # Gen II
        if gen_1_max < rejection_pct <= gen_2_max:
            return "Gen II", "Gen II (Gen I max < rejection ≤ Gen II max)"

        # Gen III
        if rejection_pct > gen_2_max:
            return "Gen III", "Gen III (rejection > Gen II max)"

    # =========================
    # SPL FAMILY
    # =========================
    if prev_level.startswith("Spl"):

        # Spl I
        if rejection_pct <= spl_1_max:
            return "Spl I", "Spl I (rejection ≤ Spl I max)"

        # Spl II
        if spl_1_max < rejection_pct <= spl_2_max:
            return "Spl II", "Spl II (Spl I max < rejection ≤ Spl II max)"

        # Spl III
        if spl_2_max < rejection_pct <= spl_3_max:
            return "Spl III", "Spl III (Spl II max < rejection ≤ Spl III max)"

        # Spl IV
        if rejection_pct > spl_3_max:
            return "Spl IV", "Spl IV (rejection > Spl III max)"

    return prev_level, "No Change"

# =================================================
# HELPERS
# =================================================

def normalize_decision(previous_level, current_level):
    if previous_level == current_level:
        return "No Change"
    if AQL_ORDER.index(current_level) < AQL_ORDER.index(previous_level):
        return "Upgraded"
    return "Downgraded"


def get_previous_aql_snapshot(supplier):
    return frappe.db.get_value(
        "Supplier AQL Performance Report",
        {"aql_party_names": supplier},
        ["current_aql_level", "rejection_percentage"],
        order_by="creation desc",
        as_dict=True,
    )


def build_decision_reason(
    supplier,
    total,
    accepted,
    rejected,
    prev_pct,
    curr_pct,
    decision,
):
    trend = (
        "improving"
        if prev_pct is not None and curr_pct < prev_pct
        else "worsening"
        if prev_pct is not None and curr_pct > prev_pct
        else "stable"
    )

    return (
        f"Supplier {supplier} | "
        f"Total: {total}, Accepted: {accepted}, Rejected: {rejected}. "
        f"Rejection % changed from {prev_pct}% to {curr_pct}%. "
        f"Trend: {trend}. Decision: {decision}."
    )


def update_supplier_master_aql_level(
    supplier,
    previous_level,
    current_level,
    decision,
):
    if previous_level == current_level:
        return

    frappe.db.set_value(
        "Supplier",
        supplier,
        "custom_aql_inspection_level",
        current_level,
    )

    frappe.logger("aql").info(
        f"SUPPLIER AQL LEVEL UPDATED → {supplier}: "
        f"{previous_level} → {current_level} ({decision})"
    )
