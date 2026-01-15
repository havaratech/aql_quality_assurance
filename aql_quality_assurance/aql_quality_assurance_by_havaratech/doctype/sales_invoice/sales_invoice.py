import frappe
from frappe.utils import flt
import json
from frappe.model.document import Document
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice as ERPNextSalesInvoice
from frappe.utils import cint

class SalesInvoice(ERPNextSalesInvoice):
    def onload(self):
        super().onload()
        self.copy_aql_from_customer()

    def validate(self):
        super().validate()    
        self.copy_aql_from_customer()

    def copy_aql_from_customer(self):
        if not self.customer:
            return

        customer = frappe.get_doc("Customer", self.customer)

        self.custom_aql_inspection_level = customer.custom_aql_inspection_level
        self.custom_aql_critical_scale = customer.custom_aql_critical_scale
        self.custom_aql_major_scale = customer.custom_aql_major_scale
        self.custom_aql_minor_scale = customer.custom_aql_minor_scale
    
@frappe.whitelist()
def fetch_aql_from_customer(customer):
    if not customer:
        return {}

    c = frappe.get_doc("Customer", customer)

    return {
        "custom_aql_inspection_level": c.custom_aql_inspection_level,
        "custom_aql_critical_scale": c.custom_aql_critical_scale,
        "custom_aql_major_scale": c.custom_aql_major_scale,
        "custom_aql_minor_scale": c.custom_aql_minor_scale
    }
