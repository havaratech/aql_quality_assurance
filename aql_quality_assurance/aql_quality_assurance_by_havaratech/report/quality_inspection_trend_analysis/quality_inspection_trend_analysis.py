# Copyright (c) 2026, HavaraTech and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    # ---------------------------------------------
    # Read global dashboard date range (Single DocType)
    # ---------------------------------------------
    settings = frappe.get_single("AQL Classification Quality Inspection Setting")

    conditions = ""
    params = {}

    if settings.dashboard_from_date:
        conditions += " AND report_date >= %(from_date)s"
        params["from_date"] = settings.dashboard_from_date

    if settings.dashboard_to_date:
        conditions += " AND report_date <= %(to_date)s"
        params["to_date"] = settings.dashboard_to_date

    # ---------------------------------------------
    # Month-wise trend calculation
    # ---------------------------------------------
    data = frappe.db.sql(f"""
        SELECT
            CONCAT(
                YEAR(report_date), '-',
                LPAD(MONTH(report_date), 2, '0')
            ) AS month,
            AVG(status = 'Accepted') * 100 AS accepted_pct,
            AVG(status = 'Rejected') * 100 AS rejected_pct
        FROM `tabQuality Inspection`
        WHERE
            docstatus = 1
            {conditions}
        GROUP BY YEAR(report_date), MONTH(report_date)
        ORDER BY YEAR(report_date), MONTH(report_date)
    """, params, as_dict=True)

    # ---------------------------------------------
    # Columns
    # ---------------------------------------------
    columns = [
        {"label": "Month", "fieldname": "month", "fieldtype": "Data"},
        {"label": "Accepted %", "fieldname": "accepted_pct", "fieldtype": "Percent"},
        {"label": "Rejected %", "fieldname": "rejected_pct", "fieldtype": "Percent"},
    ]

    # ---------------------------------------------
    # Line chart with semantic colors
    # ---------------------------------------------
    chart = {
        "data": {
            "labels": [d.month for d in data],
            "datasets": [
                {
                    "name": "Accepted %",
                    "values": [round(d.accepted_pct, 2) for d in data],
                },
                {
                    "name": "Rejected %",
                    "values": [round(d.rejected_pct, 2) for d in data],
                }
            ]
        },
        "type": "line",
        "colors": [
            "#27ae60",  # Accepted – Dark Green
            "#c0392b",  # Rejected – Dark Red
        ]
    }

    return columns, data, None, chart

