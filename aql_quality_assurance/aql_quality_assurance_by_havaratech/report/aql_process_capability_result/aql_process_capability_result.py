# from aql_quality_assurance.aql_quality_assurance_by_havaratech.report.aql_process_capability_report.aql_process_capability_report import (
#     execute,
#     get_filter_options,
#     get_histogram_data,
# )

import frappe
import math
import re


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


# ✅ Columns
def get_columns():
    return [
        {"label": "Parameter", "fieldname": "parameter", "fieldtype": "Data", "width": 200},
        {"label": "Inspection Template", "fieldname": "inspection_template", "fieldtype": "Data", "width": 180},
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Data", "width": 140},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Data", "width": 180},
        {"label": "Sample Size", "fieldname": "sample_size", "fieldtype": "Int", "width": 120},
        {"label": "Mean", "fieldname": "mean", "fieldtype": "Float", "width": 120},
        {"label": "Std Dev", "fieldname": "std_dev", "fieldtype": "Float", "width": 120},
        {"label": "USL", "fieldname": "usl", "fieldtype": "Float", "width": 100},
        {"label": "LSL", "fieldname": "lsl", "fieldtype": "Float", "width": 100},
        {"label": "Cp", "fieldname": "cp", "fieldtype": "Float", "width": 100},
        {"label": "Cpk", "fieldname": "cpk", "fieldtype": "Float", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 150},
        {"label": "Chart", "fieldname": "chart_action", "fieldtype": "HTML", "width": 110},
    ]


# ✅ Safe Float Conversion
def safe_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        match = re.search(r"[-+]?\d*\.?\d+", str(value))
        if match:
            try:
                return float(match.group())
            except:
                return None
    return None


def parse_multi_value_filter(value):
    if not value:
        return []

    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v and v.strip()]

    if isinstance(value, (list, tuple)):
        parsed = []
        for item in value:
            if isinstance(item, str) and item.strip():
                parsed.append(item.strip())
            elif isinstance(item, dict) and item.get("value"):
                parsed.append(str(item.get("value")).strip())
        return parsed

    return []


def add_in_filter(filters, fieldname, sql_field, conditions, values):
    selected_values = parse_multi_value_filter(filters.get(fieldname))
    if selected_values:
        conditions.append(f"{sql_field} IN %({fieldname})s")
        values[fieldname] = tuple(selected_values)


def build_group_key(row):
    return "||".join([
        str(row.get("parameter") or ""),
        str(row.get("inspection_template") or ""),
        str(row.get("item_code") or ""),
        str(row.get("supplier") or ""),
    ])


def calculate_stats(values_list, lsl, usl):
    if len(values_list) < 2:
        return None

    mean = sum(values_list) / len(values_list)
    variance = sum((x - mean) ** 2 for x in values_list) / (len(values_list) - 1)
    std_dev = math.sqrt(variance)

    cp = None
    cpk = None
    status = "Insufficient Data"

    if std_dev > 0 and usl is not None and lsl is not None:
        cp = (usl - lsl) / (6 * std_dev)
        cpu = (usl - mean) / (3 * std_dev)
        cpl = (mean - lsl) / (3 * std_dev)
        cpk = min(cpu, cpl)

        if cpk >= 1.33:
            status = "Capable"
        elif cpk >= 1.0:
            status = "Marginal"
        else:
            status = "Not Capable"

    return {
        "sample_size": len(values_list),
        "mean": round(mean, 3),
        "std_dev": round(std_dev, 3),
        "usl": usl,
        "lsl": lsl,
        "cp": round(cp, 3) if cp is not None else None,
        "cpk": round(cpk, 3) if cpk is not None else None,
        "status": status,
    }


def get_filtered_rows(filters, extra_conditions=None, extra_values=None):
    conditions = ["r.numeric = 1", "qi.docstatus = 1"]
    values = {}

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("qi.report_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = filters.get("from_date")
        values["to_date"] = filters.get("to_date")

    add_in_filter(filters, "parameter", "r.specification", conditions, values)
    add_in_filter(filters, "inspection_template", "qi.quality_inspection_template", conditions, values)
    add_in_filter(filters, "item_code", "qi.item_code", conditions, values)
    add_in_filter(filters, "supplier", "qi.custom_aql_party_name", conditions, values)

    if extra_conditions:
        conditions.extend(extra_conditions)
    if extra_values:
        values.update(extra_values)
# Frappe Review fix - 12-05-2026
    sql = """
        SELECT
            r.specification AS parameter,
            qi.quality_inspection_template AS inspection_template,
            qi.item_code,
            qi.custom_aql_party_name AS supplier,
            r.reading_1, r.reading_2, r.reading_3,
            r.reading_4, r.reading_5, r.reading_6,
            r.reading_7, r.reading_8, r.reading_9,
            r.reading_10,
            r.min_value AS lsl,
            r.max_value AS usl
        FROM `tabQuality Inspection` qi
        JOIN `tabQuality Inspection Reading` r
            ON r.parent = qi.name
        WHERE """ + " AND ".join(conditions)

    return frappe.db.sql(sql, values, as_dict=True)


# ✅ Fetch + Process Data
def get_data(filters):
    rows = get_filtered_rows(filters)

    grouped_rows = {}

    for row in rows:
        readings = [
            row.reading_1, row.reading_2, row.reading_3,
            row.reading_4, row.reading_5, row.reading_6,
            row.reading_7, row.reading_8, row.reading_9,
            row.reading_10
        ]

        values_list = []

        for r in readings:
            val = safe_float(r)

            if val is not None:
                values_list.append(val)
            else:
                if r not in (None, "", 0):
                    frappe.logger().warning(f"[SPC] Invalid numeric value ignored: {r}")

        if not values_list:
            continue

        row["lsl"] = safe_float(row.lsl)
        row["usl"] = safe_float(row.usl)
        group_key = build_group_key(row)

        if group_key not in grouped_rows:
            grouped_rows[group_key] = {
                "parameter": row.parameter,
                "inspection_template": row.inspection_template,
                "item_code": row.item_code,
                "supplier": row.supplier,
                "values": [],
                "lsl": row.lsl,
                "usl": row.usl,
            }

        grouped_rows[group_key]["values"].extend(values_list)

    result = []

    for group_key, details in grouped_rows.items():
        vals = details["values"]
        stats = calculate_stats(vals, details["lsl"], details["usl"])
        if not stats:
            continue

        result.append({
            "row_key": group_key,
            "parameter": details["parameter"],
            "inspection_template": details["inspection_template"],
            "item_code": details["item_code"],
            "supplier": details["supplier"],
            "chart_action": "Show Chart",
            **stats,
        })

    result.sort(key=lambda d: (
        d.get("parameter") or "",
        d.get("inspection_template") or "",
        d.get("item_code") or "",
        d.get("supplier") or "",
    ))

    return result


@frappe.whitelist()
def get_histogram_data(filters=None):
    filters = frappe._dict(frappe.parse_json(filters) or {})
    extra_conditions = []
    extra_values = {}

    row_key = filters.get("row_key")
    if row_key:
        row_parts = row_key.split("||")
        while len(row_parts) < 4:
            row_parts.append("")

        extra_conditions.extend([
            "r.specification = %(selected_parameter)s",
            "IFNULL(qi.quality_inspection_template, '') = %(selected_template)s",
            "IFNULL(qi.item_code, '') = %(selected_item_code)s",
            "IFNULL(qi.custom_aql_party_name, '') = %(selected_supplier)s",
        ])
        extra_values.update({
            "selected_parameter": row_parts[0],
            "selected_template": row_parts[1],
            "selected_item_code": row_parts[2],
            "selected_supplier": row_parts[3],
        })

    rows = get_filtered_rows(filters, extra_conditions=extra_conditions, extra_values=extra_values)
    all_values = []
    meta = None

    for row in rows:
        readings = [
            row.reading_1, row.reading_2, row.reading_3,
            row.reading_4, row.reading_5, row.reading_6,
            row.reading_7, row.reading_8, row.reading_9,
            row.reading_10,
        ]

        values_list = [safe_float(r) for r in readings]
        values_list = [v for v in values_list if v is not None]
        if not values_list:
            continue

        row["lsl"] = safe_float(row.lsl)
        row["usl"] = safe_float(row.usl)
        meta = row
        all_values.extend(values_list)

    if not meta or len(all_values) < 2:
        return {}

    stats = calculate_stats(all_values, meta["lsl"], meta["usl"])
    if not stats:
        return {}

    return {
        "row_key": build_group_key(meta),
        "parameter": meta["parameter"],
        "inspection_template": meta["inspection_template"],
        "item_code": meta["item_code"],
        "supplier": meta["supplier"],
        "values": all_values,
        **stats,
    }

# Frappe Review - 12-05-2026
@frappe.whitelist()
def get_filter_options(fieldname, txt=None):
    txt = txt or ""

    if fieldname == "parameter":
        sql = """
            SELECT DISTINCT specification AS value
            FROM `tabQuality Inspection Reading`
            JOIN `tabQuality Inspection` qi ON qi.name = `tabQuality Inspection Reading`.parent
            WHERE IFNULL(specification, '') != ''
              AND IFNULL(`numeric`, 0) = 1
              AND qi.docstatus = 1
              AND specification LIKE %(txt)s
            ORDER BY specification
            LIMIT 20
        """
    elif fieldname == "inspection_template":
        sql = """
            SELECT DISTINCT quality_inspection_template AS value
            FROM `tabQuality Inspection`
            WHERE IFNULL(quality_inspection_template, '') != ''
              AND docstatus = 1
              AND quality_inspection_template LIKE %(txt)s
            ORDER BY quality_inspection_template
            LIMIT 20
        """
    elif fieldname == "item_code":
        sql = """
            SELECT DISTINCT item_code AS value
            FROM `tabQuality Inspection`
            WHERE IFNULL(item_code, '') != ''
              AND docstatus = 1
              AND item_code LIKE %(txt)s
            ORDER BY item_code
            LIMIT 20
        """
    elif fieldname == "supplier":
        sql = """
            SELECT DISTINCT custom_aql_party_name AS value
            FROM `tabQuality Inspection`
            WHERE IFNULL(custom_aql_party_name, '') != ''
              AND docstatus = 1
              AND custom_aql_party_name LIKE %(txt)s
            ORDER BY custom_aql_party_name
            LIMIT 20
        """
    else:
        return []

    return frappe.db.sql(sql, {"txt": f"%{txt}%"}, as_dict=True)
