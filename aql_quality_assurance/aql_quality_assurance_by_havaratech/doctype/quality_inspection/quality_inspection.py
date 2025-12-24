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

    #3. Determine party details based on reference type.
    if doc.reference_type in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
        supplier_id =  ref_doc.supplier
        if supplier_id:
            #Fetch details directly from Supplier DocType
            supplier_doc = frappe.get_cached_doc("Supplier", supplier_id)
            party_name = supplier_doc.supplier_name
            party_type = supplier_doc.supplier_type

        lot_size = sum([item.qty for item in ref_doc.items if item.item_code == doc.item_code])    

        doc.custom_aql_party_name = party_name
        doc.custom_aql_party_type = party_type
        doc.custom_aql_lot_size = lot_size