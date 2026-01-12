import frappe
from frappe.utils import cint
from erpnext.stock.doctype.quality_inspection.quality_inspection import QualityInspection

_original = QualityInspection.inspect_and_set_status

def patched_inspect_and_set_status(self):
    frappe.log_error("AQL Patch Active", "AQL Patch")
    # Run ERPNext default status logic
    _original(self)

    # If override checkbox is NOT checked → enforce AQL
    if cint(self.custom_aql_status_override) == 0:
        if self.custom_aql_status:
            self.status = self.custom_aql_status
    # Else (override = 1) → user status is kept

# Inject patch
QualityInspection.inspect_and_set_status = patched_inspect_and_set_status
