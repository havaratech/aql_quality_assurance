# Copyright (c) 2026, HavaraTech and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    # -------------------------------------------------
    # Read global dashboard date range (Single DocType)
    # -------------------------------------------------
    settings = frappe.get_single("AQL Settings")

    conditions = """
        AND custom_aql_party_type = 'Supplier'
        AND custom_aql_party_name IS NOT NULL
    """
    params = {}

    if settings.dashboard_from_date:
        conditions += " AND report_date >= %(from_date)s"
        params["from_date"] = settings.dashboard_from_date

    if settings.dashboard_to_date:
        conditions += " AND report_date <= %(to_date)s"
        params["to_date"] = settings.dashboard_to_date

    # -------------------------------------------------
    # Supplier-wise aggregation
    # -------------------------------------------------
    rows = frappe.db.sql(f"""
        SELECT
            custom_aql_party_name AS supplier,
            COUNT(*) AS total_qi,
            SUM(status = 'Accepted') AS accepted_qi,
            SUM(status = 'Rejected') AS rejected_qi
        FROM `tabQuality Inspection`
        WHERE
            docstatus = 1
            AND  custom_aql_party_type = 'Supplier'
            {conditions}
        GROUP BY custom_aql_party_name
        HAVING COUNT(*) > 0
    """, params, as_dict=True)

    data = []
    for r in rows:
        total = r.total_qi or 0
        accepted = r.accepted_qi or 0
        rejected = r.rejected_qi or 0

        accepted_pct = (accepted / total * 100) if total else 0
        rejected_pct = (rejected / total * 100) if total else 0

        data.append({
            "supplier": r.supplier,
            "total_qi": total,
            "accepted_pct": round(accepted_pct, 2),
            "rejected_pct": round(rejected_pct, 2),
        })

    # -------------------------------------------------
    # Sort by BEST suppliers & take Top 50
    # -------------------------------------------------
    data.sort(
        key=lambda x: (-x["accepted_pct"], x["rejected_pct"], -x["total_qi"])
    )
    data = data[:1000]

    # -------------------------------------------------
    # Columns
    # -------------------------------------------------
    columns = [
        {
            "label": "Supplier",
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 220,
        },
        {
            "label": "Total QI",
            "fieldname": "total_qi",
            "fieldtype": "Int",
            "width": 110,
        },
        {
            "label": "Accepted %",
            "fieldname": "accepted_pct",
            "fieldtype": "Percent",
            "width": 120,
        },
        {
            "label": "Rejected %",
            "fieldname": "rejected_pct",
            "fieldtype": "Percent",
            "width": 120,
        },
    ]

    # -------------------------------------------------
    # Per-supplier color logic (performance-based)
    # -------------------------------------------------
    def get_color(accepted_pct):
        if accepted_pct >= 95:
            return "#2ecc71"   # Green – Excellent
        elif accepted_pct >= 90:
            return "#f1c40f"   # Yellow – Average
        else:
            return "#e74c3c"   # Red – Needs attention

    # -------------------------------------------------
    # Chart: Accepted % (Top 50) with per-bar colors
    # -------------------------------------------------
    chart = {
        "data": {
            "labels": [d["supplier"] for d in data],
            "datasets": [
                {
                    "name": "Accepted %",
                    "values": [d["accepted_pct"] for d in data],
                    "colors": [get_color(d["accepted_pct"]) for d in data],
                }
            ],
        },
        "type": "bar",
    }

    return columns, data, None, chart


