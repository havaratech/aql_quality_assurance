# Copyright (c) 2026, HavaraTech and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    # ---------------------------------------------
    # Read dashboard date range
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
    # Month-wise aggregation
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
    # Moving average (stock-style smoothing)
    # ---------------------------------------------
    def moving_average(values, window=3):
        result = []
        for i in range(len(values)):
            subset = values[max(0, i - window + 1): i + 1]
            result.append(round(sum(subset) / len(subset), 2))
        return result

    accepted_vals = [round(d.accepted_pct, 2) for d in data]
    rejected_vals = [round(d.rejected_pct, 2) for d in data]
    accepted_ma = moving_average(accepted_vals)

    # ---------------------------------------------
    # Columns
    # ---------------------------------------------
    columns = [
        {"label": "Month", "fieldname": "month", "fieldtype": "Data"},
        {"label": "Accepted %", "fieldname": "accepted_pct", "fieldtype": "Percent"},
        {"label": "Rejected %", "fieldname": "rejected_pct", "fieldtype": "Percent"},
    ]

    # ---------------------------------------------
    # Stock-market style line chart
    # ---------------------------------------------
    chart = {
        "data": {
            "labels": [d.month for d in data],
            "datasets": [
                {
                    "name": "Accepted %",
                    "values": accepted_vals,
                },
                {
                    "name": "Accepted % (Trend)",
                    "values": accepted_ma,
                },
                {
                    "name": "Rejected %",
                    "values": rejected_vals,
                },
            ],
        },
        "type": "line",
        "colors": [
            "#2ecc71",  # Accepted – main price line
            "#1abc9c",  # Moving average – smooth trend
            "#e74c3c",  # Rejected – risk signal
        ],
        "lineOptions": {
            "hideDots": 1,      # 🔑 no markers
            "regionFill": 0,    # 🔑 no area fill
        },
    }

    return columns, data, None, chart
