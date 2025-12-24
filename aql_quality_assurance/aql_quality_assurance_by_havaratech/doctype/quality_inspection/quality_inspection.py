import frappe

def set_aql_parameters(doc, method):
    """ 
    Auto populate key fields from respective DocTypes - Supplier, Customer & Item.
    """

    #1. Reset fields if reference is missing.
    if not doc.reference_type or not doc.reference_name:
        doc.custom_aql_party_name = None
        doc.custom_aql_party_type = None
        doc.custom_aql_lot_size = 0
        return

    #2. Fetch the reference document from (Purchase Receipt, )    
    try:
        ref_doc = frappe.get_cached_doc(doc.reference_type, doc.reference_name)
    except frappe.DoesNotExistError:
        return

    party_name = None
    party_type = None
    lot_size = 0
    
            