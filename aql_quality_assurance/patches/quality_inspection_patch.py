import frappe
frappe.logger("aql_patch").warning(" AQL Patch Applied ")

from erpnext.stock.doctype.quality_inspection.quality_inspection import (
    QualityInspection    
)

def execute():
    frappe.logger("aql_patch").warning(" Patching Quality Inspection set_status_based_on_acceptance_values Method ")
_original = QualityInspection.set_status_based_on_acceptance_values

def patched_set_status(self, reading):
    if reading.custom_aql_optional_parameter:
        has_input = reading.reading_1 or reading.reading_value
        if not has_input:
            reading.status = "Accepted"
            return
    return _original(self, reading)

QualityInspection.set_status_based_on_acceptance_values = patched_set_status

def custom_inspect_and_set_status(self):
    """Custom implementation to enforce AQL rules and handle default Pending status."""
    for reading in self.readings:
        if not reading.manual_inspection:  # don't auto set status if manual
            if not (reading.reading_1 or reading.reading_value):
                # Default to Pending if no values are provided
                reading.status = "Pending"
            elif reading.formula_based_criteria:
                self.set_status_based_on_acceptance_formula(reading)
            else:
                # if not formula-based, check acceptance values set
                self.set_status_based_on_acceptance_values(reading)

    # Custom logic to enforce Pending or Accepted status
    all_readings_filled = all(
        row.reading_1 or row.reading_value for row in self.readings
    )

    if not all_readings_filled:
        self.status = "Pending"
        frappe.msgprint("Status set to Pending due to incomplete readings.", alert=True)
        return

    # Default to Accepted unless any reading is Rejected
    self.status = "Accepted"
    for reading in self.readings:
        if reading.status == "Rejected":
            self.status = "Rejected"
            frappe.msgprint(
                _("Status set to Rejected as there are one or more rejected readings."), alert=True
            )
            break

# Monkey patch the method
QualityInspection.inspect_and_set_status = custom_inspect_and_set_status