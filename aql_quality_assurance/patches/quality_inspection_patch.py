import frappe
frappe.logger("aql_patch").warning(" AQL Patch Applied ")

from erpnext.stock.doctype.quality_inspection.quality_inspection import QualityInspection    

_original = QualityInspection.set_status_based_on_acceptance_values

def patched_set_status(self, reading):
    if reading.custom_aql_optional_parameter:
        has_input = reading.reading_1 or reading.reading_value
        if not has_input:
            reading.status = "Accepted"
            return
    return _original(self, reading)

    QualityInspection.set_status_based_on_acceptance_values = patched_set_status