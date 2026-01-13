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

        supplier = frappe.get_doc("Supplier", self.supplier)

        self.custom_aql_inspection_level = supplier.custom_aql_inspection_level
        self.custom_aql_critical_scale = supplier.custom_aql_critical_scale
        self.custom_aql_major_scale = supplier.custom_aql_major_scale
        self.custom_aql_minor_scale = supplier.custom_aql_minor_scale
        

@frappe.whitelist()
def fetch_aql_from_supplier(supplier):
    if not supplier:
        return {}

    s = frappe.get_doc("Supplier", supplier)

    return {
        "custom_aql_inspection_level": s.custom_aql_inspection_level,
        "custom_aql_critical_scale": s.custom_aql_critical_scale,
        "custom_aql_major_scale": s.custom_aql_major_scale,
        "custom_aql_minor_scale": s.custom_aql_minor_scale
    }

    