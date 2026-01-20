import frappe
from frappe.utils import flt
import json
from frappe.model.document import Document
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote as ERPNextDeliveryNote
from frappe.utils import cint

class DeliveryNote(ERPNextDeliveryNote):

    def onload(self):
        super().onload()
        self.copy_aql_from_customer()

    def validate(self):
        super().validate()
        self.copy_aql_from_customer()    

    def copy_aql_from_customer(self):
        if not self.customer:
            return
        aql_global_settings = frappe.get_single("AQL Classification Quality Inspection Setting")
        c_master = frappe.get_doc("Customer", self.customer)

        if c_master.get("custom_aql_inspection_level") == "Select":
            self.custom_aql_inspection_level = aql_global_settings.get("aql_inspection_level")
        if c_master.get("custom_aql_critical_scale") == "Select":
            self.custom_aql_critical_scale = aql_global_settings.get("aql_critical_scale")
        if c_master.get("custom_aql_major_scale")== "Select":
            self.custom_aql_major_scale = aql_global_settings.get("aql_major_scale")
        if c_master.get("custom_aql_minor_scale") == "Select":
            self.custom_aql_minor_scale = aql_global_settings.get("aql_minor_scale")
        

@frappe.whitelist()
def fetch_aql_from_customer(customer):
    if not customer:
        return {}

    # Fetch Supplier
    c_master = frappe.get_doc("Customer", customer)

    # Fetch Global AQL Settings
    aql_global_settings = frappe.get_single(
        "AQL Classification Quality Inspection Setting"
    )

    def get_value(customer_value, global_value):
        # Handle None, empty, or string "Select"
        if not customer_value or customer_value == "Select":
            return global_value
        return customer_value

    return {
        "custom_aql_inspection_level": get_value(
            c_master.custom_aql_inspection_level,
            aql_global_settings.aql_inspection_level
        ),
        "custom_aql_critical_scale": get_value(
            c_master.custom_aql_critical_scale,
            aql_global_settings.aql_critical_scale
        ),
        "custom_aql_major_scale": get_value(
            c_master.custom_aql_major_scale,
            aql_global_settings.aql_major_scale
        ),
        "custom_aql_minor_scale": get_value(
            c_master.custom_aql_minor_scale,
            aql_global_settings.aql_minor_scale
        )
    }

    