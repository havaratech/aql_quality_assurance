import frappe
from frappe.utils import now, getdate

AQL_ORDER = [
    "Gen I",
    "Gen II",
    "Gen III",
    "Spl I",
    "Spl II",
    "Spl III",
    "Spl IV"
]

# =================================================
# MAIN ENTRY
# =================================================

def process_supplier_aql(
    supplier,
    start_date,
    end_date,
    min_threshold,
    max_threshold
):
    """
    Create or update Supplier AQL Performance Report (UPSERT)
    using regime-safe, trend-aware AQL logic.
    """

    start_date = getdate(start_date)
    end_date = getdate(end_date)

    # ---------------------------------------
    # Aggregate Quality Inspections
    # ---------------------------------------
    result = frappe.db.sql("""
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
    """, (supplier, start_date, end_date), as_dict=True)[0]

    if not result.total:
        return

    acceptance_pct = (result.accepted / result.total) * 100
    rejection_pct = (result.rejected / result.total) * 100

    # ---------------------------------------
    # Fetch previous snapshot (LEVEL + %)
    # ---------------------------------------
    prev = get_previous_aql_snapshot(supplier)

    previous_level = (
        prev.current_aql_level if prev and prev.current_aql_level else "Gen II"
    )
    previous_rejection_pct = (
        prev.rejection_percentage if prev else None
    )

    # ---------------------------------------
    # TREND-AWARE, REGIME-SAFE DECISION
    # ---------------------------------------
    current_level, decision = decide_aql_with_trend(
        prev_level=previous_level,
        prev_rejection_pct=previous_rejection_pct,
        current_rejection_pct=rejection_pct,
        min_threshold=min_threshold,
        max_threshold=max_threshold
    )

    # ---------------------------------------
    # Update Supplier Master
    # ---------------------------------------
    update_supplier_master_aql_level(
        supplier=supplier,
        previous_level=previous_level,
        current_level=current_level,
        decision=decision
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
        pluck="name"
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
        "last_decision": decision,
        "last_decision_on": now(),
        "reject_min_pct_used": min_threshold,
        "reject_max_pct_used": max_threshold,
        "decision_reason": build_decision_reason(
            supplier=supplier,
            total=result.total,
            accepted=result.accepted,
            rejected=result.rejected,
            prev_pct=previous_rejection_pct,
            curr_pct=rejection_pct,
            decision=decision
        ),
    }

    if existing:
        doc = frappe.get_doc("Supplier AQL Performance Report", existing[0])
        doc.update(values)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "Supplier AQL Performance Report",
            "reference_type": "Supplier",
            "aql_party_names": supplier,
            "inspection_start_from": start_date,
            "inspection_end_to": end_date,
            **values
        })
        doc.insert(ignore_permissions=True)


# =================================================
# DECISION ENGINE (REGIME-SAFE)
# =================================================

def decide_aql_with_trend(
    prev_level,
    prev_rejection_pct,
    current_rejection_pct,
    min_threshold,
    max_threshold
):
    """
    Regime-safe, trend-aware AQL decision logic.
    """

    if prev_level not in AQL_ORDER:
        prev_level = "Gen II"

    idx = AQL_ORDER.index(prev_level)

    # -------------------------
    # GOOD QUALITY
    # -------------------------
    if current_rejection_pct <= min_threshold:
        if is_gen(prev_level) and prev_level != "Gen I":
            return AQL_ORDER[idx - 1], "Upgraded"
        if is_spl(prev_level) and prev_level != "Spl I":
            return AQL_ORDER[idx - 1], "Upgraded"
        return prev_level, "Hold (Regime Floor)"

    # -------------------------
    # BORDERLINE QUALITY
    # -------------------------
    if min_threshold < current_rejection_pct <= max_threshold:
        return prev_level, "No Change"

    # -------------------------
    # BAD QUALITY (> max)
    # -------------------------
    if current_rejection_pct > max_threshold:

        # Improving trend → HOLD
        if (
            prev_rejection_pct is not None
            and current_rejection_pct < prev_rejection_pct
        ):
            return prev_level, "Hold (Improving)"

        # Worsening trend → degrade WITHIN regime only
        if is_gen(prev_level):
            if prev_level == "Gen III":
                return prev_level, "Hold (Gen Regime Limit)"
            return AQL_ORDER[idx + 1], "Downgraded"

        if is_spl(prev_level):
            return AQL_ORDER[min(idx + 1, len(AQL_ORDER) - 1)], "Downgraded"

    return prev_level, "No Change"


# =================================================
# HELPERS
# =================================================

def get_previous_aql_snapshot(supplier):
    """
    Fetch last AQL level + rejection % for trend comparison.
    """
    return frappe.db.get_value(
        "Supplier AQL Performance Report",
        {"aql_party_names": supplier},
        ["current_aql_level", "rejection_percentage"],
        order_by="creation desc",
        as_dict=True
    )


def build_decision_reason(
    supplier,
    total,
    accepted,
    rejected,
    prev_pct,
    curr_pct,
    decision
):
    trend = (
        "improving" if prev_pct is not None and curr_pct < prev_pct
        else "worsening" if prev_pct is not None and curr_pct > prev_pct
        else "stable"
    )

    return (
        f"Supplier {supplier} | Total: {total}, "
        f"Accepted: {accepted}, Rejected: {rejected}. "
        f"Rejection % changed from {prev_pct}% to {curr_pct}%. "
        f"Trend: {trend}. Decision: {decision}."
    )


def update_supplier_master_aql_level(
    supplier,
    previous_level,
    current_level,
    decision
):
    """
    Update Supplier master AQL level only if level changed.
    """

    if previous_level == current_level:
        return

    frappe.db.set_value(
        "Supplier",
        supplier,
        "custom_aql_inspection_level",
        current_level
    )

    frappe.logger("aql").info(
        f"SUPPLIER AQL LEVEL UPDATED → {supplier}: "
        f"{previous_level} → {current_level} ({decision})"
    )


def is_gen(level):
    return level.startswith("Gen")


def is_spl(level):
    return level.startswith("Spl")
