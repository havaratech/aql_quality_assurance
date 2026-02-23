# Copyright (c) 2026, HavaraTech and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    # ---------------------------------------------
    # Read dashboard date range
    # ---------------------------------------------
    settings = frappe.get_single("AQL Settings")

    conditions = ""
    params = {}

    if settings.dashboard_from_date:
        conditions += " AND DATE(report_date) >= %(from_date)s"
        params["from_date"] = settings.dashboard_from_date

    if settings.dashboard_to_date:
        conditions += " AND DATE(report_date) <= %(to_date)s"
        params["to_date"] = settings.dashboard_to_date

    # ---------------------------------------------
    # DAILY aggregation (KEY CHANGE)
    # ---------------------------------------------
    data = frappe.db.sql(
        f"""
        SELECT
            DATE(report_date) AS report_day,
            SUM(status = 'Accepted') / COUNT(*) * 100 AS accepted_pct,
            SUM(status = 'Rejected') / COUNT(*) * 100 AS rejected_pct
        FROM `tabQuality Inspection`
        WHERE
            docstatus = 1
            AND custom_aql_party_type = 'Supplier'
            {conditions}
        GROUP BY DATE(report_date)
        ORDER BY DATE(report_date)
        """,
        params,
        as_dict=True,
    )

    if not data:
        return [], [], None, None

    # ---------------------------------------------
    # Moving average (DAILY)
    # ---------------------------------------------
    window_size = frappe.get_single("AQL Settings").average_window_size

    def moving_average(values, window=window_size):
        result = []
        for i in range(len(values)):
            subset = values[max(0, i - window + 1): i + 1]
            result.append(round(sum(subset) / len(subset), 2))
        return result

    accepted_vals = [round(d.accepted_pct, 2) for d in data]
    rejected_vals = [round(d.rejected_pct, 2) for d in data]
    accepted_trend = moving_average(accepted_vals)

    # ---------------------------------------------
    # Inject trend back into rows
    # ---------------------------------------------
    for i, row in enumerate(data):
        row["accepted_trend"] = accepted_trend[i]

    # ---------------------------------------------
    # Columns
    # ---------------------------------------------
    columns = [
        {
            "label": "Date",
            "fieldname": "report_day",
            "fieldtype": "Date",
        },
        {
            "label": "Accepted %",
            "fieldname": "accepted_pct",
            "fieldtype": "Percent",
        },
        {
            "label": "Accepted % (Trend)",
            "fieldname": "accepted_trend",
            "fieldtype": "Percent",
        },
        {
            "label": "Rejected %",
            "fieldname": "rejected_pct",
            "fieldtype": "Percent",
        },
    ]

    # ---------------------------------------------
    # Chart (TRUE DAILY TREND)
    # ---------------------------------------------
    chart = {
        "data": {
            "labels": [str(d.report_day) for d in data],
            "datasets": [
                {
                    "name": "Accepted %",
                    "values": accepted_vals,
                },
                {
                    "name": "Accepted % (Trend)",
                    "values": accepted_trend,
                },
                {
                    "name": "Rejected %",
                    "values": rejected_vals,
                },
            ],
        },
        "type": "line",
        "colors": [
            "#2ecc71",  # Accepted
            "#1abc9c",  # Trend
            "#e74c3c",  # Rejected
        ],
        "lineOptions": {
            "hideDots": 1,
            "regionFill": 0,
        },
    }

    return columns, data, None, chart
