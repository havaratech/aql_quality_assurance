import frappe
from frappe.utils import flt
import json

@frappe.whitelist()
def set_aql_parameters(doc, method=None):
    # if called from JS, 'doc' is a JSON string. must convert it to a doc object
    if isinstance(doc, str):
        doc = frappe.get_doc(json.loads(doc))

    # --- TRACE 1: Check if hook is working ---
    # If you see this message when saving, the hook is connected.
    # If you DON'T see it, the problem is in your hooks.py path.
    frappe.msgprint("DEBUG: set_aql_parameters started")

    if not doc.reference_type or not doc.reference_name:
        frappe.msgprint("DEBUG: Missing Reference Type or Name")
        return

    # --- TRACE 2: Verify Reference Doc Loading ---
    try:
        ref_doc = frappe.get_doc(doc.reference_type, doc.reference_name)
        frappe.msgprint(f"DEBUG: Successfully loaded {doc.reference_type}: {doc.reference_name}")
    except Exception as e:
        frappe.msgprint(f"DEBUG: Error loading reference: {e}")
        return

    # --- TRACE 3: Process Supplier Documents ---
    if doc.reference_type in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
        # Get the ID from the PR
        s_id = ref_doc.get("supplier")
        if s_id:
            # Fetch the actual Supplier master record
            s_master = frappe.get_doc("Supplier", s_id)
            
            # Map values
            doc.custom_aql_party_name = s_master.supplier_name
            doc.custom_aql_party_type = s_master.supplier_type
            doc.custom_aql_inspection_level = s_master.custom_aql_inspection_level
            doc.custom_aql_critical_scale = s_master.custom_aql_critical_scale
            doc.custom_aql_major_scale = s_master.custom_aql_major_scale
            doc.custom_aql_minor_scale = s_master.custom_aql_minor_scale            
            frappe.msgprint(f"DEBUG: Found Supplier {s_master.supplier_name}")
        else:
            frappe.msgprint("DEBUG: No Supplier ID found in reference doc")

    # --- TRACE 4: Process Customer Documents ---
    elif doc.reference_type in ["Delivery Note", "Sales Invoice"]:
        c_id = ref_doc.get("customer")
        if c_id:
            c_master = frappe.get_doc("Customer", c_id)
            doc.custom_aql_party_name = c_master.customer_name
            doc.custom_aql_party_type = c_master.customer_type
            doc.custom_aql_inspection_level = s_master.custom_aql_inspection_level
            doc.custom_aql_critical_scale = s_master.custom_aql_critical_scale
            doc.custom_aql_major_scale = s_master.custom_aql_major_scale
            doc.custom_aql_minor_scale = s_master.custom_aql_minor_scale
            frappe.msgprint(f"DEBUG: Found Customer {c_master.customer_name}")

    # Lot size logic
    if doc.item_code:
        qty = sum([flt(i.qty) for i in ref_doc.get("items") if i.item_code == doc.item_code])
        doc.custom_aql_lot_size = qty

    return doc