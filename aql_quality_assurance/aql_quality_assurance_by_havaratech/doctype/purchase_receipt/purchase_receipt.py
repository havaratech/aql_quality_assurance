import frappe
from frappe.utils import flt
import json
from frappe.model.document import Document
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt as ERPNextPurchaseReceipt
from frappe.utils import cint


class PurchaseReceipt(ERPNextPurchaseReceipt):

    def onload(self):
        super().onload()
        self.copy_aql_from_supplier()

    def validate(self):
        super().validate()
        self.copy_aql_from_supplier()    

    def copy_aql_from_supplier(self):
        if not self.supplier:
            return
        aql_global_settings = frappe.get_single("AQL Classification Quality Inspection Setting")
        s_master = frappe.get_doc("Supplier", self.supplier)

        if s_master.get("custom_aql_inspection_level") == "Select":
            self.custom_aql_inspection_level = aql_global_settings.get("aql_inspection_level")
        if s_master.get("custom_aql_critical_scale") == "Select":
            self.custom_aql_critical_scale = aql_global_settings.get("aql_critical_scale")
        if s_master.get("custom_aql_major_scale")== "Select":
            self.custom_aql_major_scale = aql_global_settings.get("aql_major_scale")
        if s_master.get("custom_aql_minor_scale") == "Select":
            self.custom_aql_minor_scale = aql_global_settings.get("aql_minor_scale")
        

@frappe.whitelist()
def fetch_aql_from_supplier(supplier):
    if not supplier:
        return {}

    # Fetch Supplier
    s_master = frappe.get_doc("Supplier", supplier)

    # Fetch Global AQL Settings
    aql_global_settings = frappe.get_single(
        "AQL Classification Quality Inspection Setting"
    )

    def get_value(supplier_value, global_value):
        # Handle None, empty, or string "None"
        if not supplier_value or supplier_value == "Select":
            return global_value
        return supplier_value

    return {
        "custom_aql_inspection_level": get_value(
            s_master.custom_aql_inspection_level,
            aql_global_settings.aql_inspection_level
        ),
        "custom_aql_critical_scale": get_value(
            s_master.custom_aql_critical_scale,
            aql_global_settings.aql_critical_scale
        ),
        "custom_aql_major_scale": get_value(
            s_master.custom_aql_major_scale,
            aql_global_settings.aql_major_scale
        ),
        "custom_aql_minor_scale": get_value(
            s_master.custom_aql_minor_scale,
            aql_global_settings.aql_minor_scale
        )
    }

    