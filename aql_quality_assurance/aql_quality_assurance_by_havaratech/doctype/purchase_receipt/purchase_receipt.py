import frappe

def copy_aql_from_supplier(doc, method):
    if not doc.supplier:
        return

    supplier = frappe.get_doc("Supplier", doc.supplier)

    doc.custom_aql_inspection_level = supplier.custom_aql_inspection_level
    doc.custom_aql_critical_scale = supplier.custom_aql_critical_scale
    doc.custom_aql_major_scale = supplier.custom_aql_major_scale
    doc.custom_aql_minor_scale = supplier.custom_aql_minor_scale
    