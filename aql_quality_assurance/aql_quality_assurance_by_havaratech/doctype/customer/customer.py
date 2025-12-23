import frappe

def set_aql_defaults_from_config(doc, method):
    """
    AQL Inspection Level logic for Customer:
    - Override OFF → force values from global config
    - Override ON  → user must select valid values
    """

    # -------------------------------
    # CASE 1: Override ENABLED
    # -------------------------------
    if doc.custom_aql_default_override:

        if (
            doc.custom_aql_inspection_level == "Select"
            or doc.custom_aql_critical_scale == "Select"
            or doc.custom_aql_major_scale == "Select"
            or doc.custom_aql_minor_scale == "Select"
        ):
            frappe.throw(
                "Please select all AQL values when Override is enabled."
            )

        return  # respect user selection

    # -------------------------------
    # CASE 2: Override DISABLED
    # -------------------------------
    config = frappe.get_single(
        "AQL Classification Quality Inspection Setting"
    )

    #Validate CONFIG, not Supplier
    if (
        not config.aql_inspection_level
        or config.aql_inspection_level == "Select"
        or config.aql_critical_scale == "Select"
        or config.aql_major_scale == "Select"
        or config.aql_minor_scale == "Select"
    ):
        frappe.throw(
            "Please configure valid AQL values in AQL Classification Quality Inspection Setting."
        )

    #Force values from config
    doc.custom_aql_inspection_level = config.aql_inspection_level
    doc.custom_aql_critical_scale = config.aql_critical_scale
    doc.custom_aql_major_scale = config.aql_major_scale
    doc.custom_aql_minor_scale = config.aql_minor_scale
