# Copyright (c) 2026, HavaraTech and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    # -------------------------------------------------
    # Read global dashboard date range (Single DocType)
    # -------------------------------------------------
    settings = frappe.get_single("AQL Settings")

    conditions = ""
    params = {}

    if settings.dashboard_from_date:
        conditions += " AND report_date >= %(from_date)s"
        params["from_date"] = settings.dashboard_from_date

    if settings.dashboard_to_date:
        conditions += " AND report_date <= %(to_date)s"
        params["to_date"] = settings.dashboard_to_date

    # -------------------------------------------------
    # Aggregate Quality Inspection data
    # -------------------------------------------------
    result = frappe.db.sql(f"""
        SELECT
            COUNT(*) AS total,
            SUM(status = 'Accepted') AS accepted,
            SUM(status = 'Rejected') AS rejected,
            SUM(status = 'Pending') AS pending,
            SUM(status = 'On Hold') AS on_hold
        FROM `tabQuality Inspection`
        WHERE docstatus != 2
        AND custom_aql_party_type = 'Supplier'                   
        {conditions}
    """, params, as_dict=True)[0]

    total = result.total or 0
    accepted = result.accepted or 0
    rejected = result.rejected or 0
    pending = result.pending or 0
    on_hold = result.on_hold or 0

    # -------------------------------------------------
    # Table data (single KPI row)
    # -------------------------------------------------
    data = [{
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
        "pending": pending,
        "on_hold": on_hold,
        "accepted_pct": round((accepted / total * 100), 2) if total else 0,
        "rejected_pct": round((rejected / total * 100), 2) if total else 0,
    }]

    columns = [
        {"label": "Total QI", "fieldname": "total", "fieldtype": "Int"},
        {"label": "Accepted", "fieldname": "accepted", "fieldtype": "Int"},
        {"label": "Rejected", "fieldname": "rejected", "fieldtype": "Int"},
        {"label": "Pending", "fieldname": "pending", "fieldtype": "Int"},
        {"label": "On Hold", "fieldname": "on_hold", "fieldtype": "Int"},
        {"label": "Accepted %", "fieldname": "accepted_pct", "fieldtype": "Percent"},
        {"label": "Rejected %", "fieldname": "rejected_pct", "fieldtype": "Percent"},
    ]

    # -------------------------------------------------
    # Donut chart with semantic colors
    # -------------------------------------------------
    chart = {
        "data": {
            "labels": ["Accepted", "Rejected", "Pending", "On Hold"],
            "datasets": [{
                "values": [accepted, rejected, pending, on_hold]
            }]
        },
        "type": "donut",
        "colors": [
            "#2ecc71",  # Accepted - Green
            "#e74c3c",  # Rejected - Red
            "#f1c40f",  # Pending - Yellow
            "#e67e22",  # On Hold - Orange
        ],
    }

    return columns, data, None, chart

