import frappe

def copy_aql_from_supplier(doc, method):
    if not doc.supplier:
        return

    customer = frappe.get_doc("Customer", doc.customer)

    doc.custom_aql_inspection_level = customer.custom_aql_inspection_level
    doc.custom_aql_critical_scale = customer.custom_aql_critical_scale
    doc.custom_aql_major_scale = customer.custom_aql_major_scale
    doc.custom_aql_minor_scale = customer.custom_aql_minor_scale
    