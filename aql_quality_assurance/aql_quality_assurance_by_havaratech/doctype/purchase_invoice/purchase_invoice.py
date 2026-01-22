import frappe
from frappe.utils import flt
import json
from frappe.model.document import Document
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice as ERPNextPurchaseInvoice
from frappe.utils import cint

# class PurchaseInvoice(ERPNextPurchaseInvoice):

#     def onload(self):
#         super().onload()
#         self.copy_aql_from_supplier()

#     def validate(self):
#         super().validate()
#         self.copy_aql_from_supplier()    

#     def copy_aql_from_supplier(self):
#         if not self.supplier:
#             return
#         aql_global_settings = frappe.get_single("AQL Classification Quality Inspection Setting")
#         s_master = frappe.get_doc("Supplier", self.supplier)

#         if s_master.get("custom_aql_inspection_level") == "Select":
#             self.custom_aql_inspection_level = aql_global_settings.get("aql_inspection_level")
#         if s_master.get("custom_aql_critical_scale") == "Select":
#             self.custom_aql_critical_scale = aql_global_settings.get("aql_critical_scale")
#         if s_master.get("custom_aql_major_scale")== "Select":
#             self.custom_aql_major_scale = aql_global_settings.get("aql_major_scale")
#         if s_master.get("custom_aql_minor_scale") == "Select":
#             self.custom_aql_minor_scale = aql_global_settings.get("aql_minor_scale")
        

# @frappe.whitelist()
# def fetch_aql_from_supplier(supplier):
#     if not supplier:
#         return {}

#     # Fetch Supplier
#     s_master = frappe.get_doc("Supplier", supplier)

#     # Fetch Global AQL Settings
#     aql_global_settings = frappe.get_single(
#         "AQL Classification Quality Inspection Setting"
#     )

#     def get_value(supplier_value, global_value):
#         # Handle None, empty, or string "None"
#         if not supplier_value or supplier_value == "Select":
#             return global_value
#         return supplier_value

#     return {
#         "custom_aql_inspection_level": get_value(
#             s_master.custom_aql_inspection_level,
#             aql_global_settings.aql_inspection_level
#         ),
#         "custom_aql_critical_scale": get_value(
#             s_master.custom_aql_critical_scale,
#             aql_global_settings.aql_critical_scale
#         ),
#         "custom_aql_major_scale": get_value(
#             s_master.custom_aql_major_scale,
#             aql_global_settings.aql_major_scale
#         ),
#         "custom_aql_minor_scale": get_value(
#             s_master.custom_aql_minor_scale,
#             aql_global_settings.aql_minor_scale
#         )
#     }

class PurchaseInvoice(ERPNextPurchaseInvoice):

    def onload(self):
        super().onload()
        self.set_aql_parameters()

    def validate(self):
        super().validate()
        self.set_aql_parameters()

    def set_aql_parameters(self):
        if not self.supplier or not self.items:
            return

        supplier_doc = frappe.get_doc("Supplier", self.supplier)
        item_doc = frappe.get_doc("Item", self.items[0].item_code)

        aql_global = frappe.get_single(
            "AQL Classification Quality Inspection Setting"
        )

        VALID_LEVELS = ['Gen I', 'Gen II', 'Gen III', 'Spl I', 'Spl II', 'Spl III', 'Spl IV']
        VALID_SCALES = ['0.065', '0.1', '0.15', '0.25', '0.4',
                        '0.65', '1.0', '1.5', '2.5', '4', '6.5']

        def resolve(field, valid_values):
            if supplier_doc.get(field) in valid_values:
                return supplier_doc.get(field)
            if item_doc.get(field) in valid_values:
                return item_doc.get(field)
            return aql_global.get(field.replace("custom_", ""))

        self.custom_aql_inspection_level = resolve(
            "custom_aql_inspection_level", VALID_LEVELS
        )
        self.custom_aql_critical_scale = resolve(
            "custom_aql_critical_scale", VALID_SCALES
        )
        self.custom_aql_major_scale = resolve(
            "custom_aql_major_scale", VALID_SCALES
        )
        self.custom_aql_minor_scale = resolve(
            "custom_aql_minor_scale", VALID_SCALES
        )


# ============================================================
# WHITELIST METHOD (SAFE)
# ============================================================

@frappe.whitelist()
def fetch_aql_from_supplier(supplier, item_code=None):
    """
    Field-wise resolution:
    Supplier → Item → Global
    """

    if not supplier:
        return {}

    aql_global = frappe.get_single(
        "AQL Classification Quality Inspection Setting"
    )

    supplier_doc = frappe.get_doc("Supplier", supplier)
    item_doc = frappe.get_doc("Item", item_code) if item_code else None

    VALID_LEVELS = ['Gen I', 'Gen II', 'Gen III', 'Spl I', 'Spl II', 'Spl III', 'Spl IV']
    VALID_SCALES = ['0.065', '0.1', '0.15', '0.25', '0.4',
                    '0.65', '1.0', '1.5', '2.5', '4', '6.5']

    def resolve(field, valid_values):
        if supplier_doc.get(field) in valid_values:
            return supplier_doc.get(field)
        if item_doc and item_doc.get(field) in valid_values:
            return item_doc.get(field)
        return aql_global.get(field.replace("custom_", ""))

    return {
        "custom_aql_inspection_level": resolve(
            "custom_aql_inspection_level", VALID_LEVELS
        ),
        "custom_aql_critical_scale": resolve(
            "custom_aql_critical_scale", VALID_SCALES
        ),
        "custom_aql_major_scale": resolve(
            "custom_aql_major_scale", VALID_SCALES
        ),
        "custom_aql_minor_scale": resolve(
            "custom_aql_minor_scale", VALID_SCALES
        )
    }
   