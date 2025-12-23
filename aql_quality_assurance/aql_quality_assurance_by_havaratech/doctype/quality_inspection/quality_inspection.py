import frappe


def set_aql_fields_from_reference(doc, method):
    """
    Server-side auto population of AQL fields in Quality Inspection
    based on reference_type & reference_name.
    """

    # -------------------------------------------------
    # CLEAR AQL FIELDS IF REFERENCE IS REMOVED / CHANGED
    # -------------------------------------------------
    if not doc.reference_type or not doc.reference_name:
        doc.custom_aql_lot_size = 0
        doc.custom_aql_party_name = None
        doc.custom_aql_party_type = None
        return

    # -------------------------------------------------
    # DISPATCHER
    # -------------------------------------------------
    handlers = {
        "Purchase Receipt": _from_purchase_receipt,
        "Purchase Invoice": _from_purchase_invoice,
        "Subcontracting Receipt": _from_subcontracting_receipt,
        "Delivery Note": _from_delivery_note,
        "Sales Invoice": _from_sales_invoice,
        "Stock Entry": _from_stock_entry,
        "Job Card": _from_job_card,
    }

    handler = handlers.get(doc.reference_type)
    if handler:
        handler(doc)


# =====================================================
# COMMON LOT SIZE RESOLVER
# =====================================================
def _get_lot_size_from_items(doc, items, qty_field):
    """
    Resolve lot size:
    1. Item-specific match
    2. Fallback → sum of quantities
    """

    lot_size = 0

    # Item-wise inspection
    if doc.item_code:
        for row in items:
            if row.item_code == doc.item_code:
                lot_size = row.get(qty_field) or 0
                break

    # Fallback → sum
    if not lot_size:
        lot_size = sum([(row.get(qty_field) or 0) for row in items])

    return lot_size


# =====================================================
# PURCHASE RECEIPT
# =====================================================
def _from_purchase_receipt(doc):
    pr = frappe.get_doc("Purchase Receipt", doc.reference_name)

    if not doc.custom_aql_party_name:
        doc.custom_aql_party_name = pr.supplier_name

    if not doc.custom_aql_party_type:
        doc.custom_aql_party_type = pr.supplier_type
        
    calculated_lot_size = _get_lot_size_from_items(
        doc, pr.items, "qty"
    )

    if not doc.custom_aql_lot_size:
        doc.custom_aql_lot_size = calculated_lot_size

# =====================================================
# PURCHASE INVOICE
# =====================================================
# def _from_purchase_invoice(doc):
#     pi = frappe.get_doc("Purchase Invoice", doc.reference_name)

#     if not doc.aql_party:
#         doc.aql_party = pi.supplier

#     if not doc.aql_party_type:
#         doc.aql_party_type = pi.supplier_type

#     calculated_lot_size = _get_lot_size_from_items(
#         doc, pi.items, "qty"
#     )

#     if not doc.lot_size:
#         doc.lot_size = calculated_lot_size


# =====================================================
# SUBCONTRACTING RECEIPT
# =====================================================
# def _from_subcontracting_receipt(doc):
#     scr = frappe.get_doc("Subcontracting Receipt", doc.reference_name)

#     if not doc.aql_party:
#         doc.aql_party = scr.supplier

#     if not doc.aql_party_type:
#         doc.aql_party_type = scr.supplier_type

#     calculated_lot_size = _get_lot_size_from_items(
#         doc, scr.items, "qty"
#     )

#     if not doc.lot_size:
#         doc.lot_size = calculated_lot_size


# =====================================================
# DELIVERY NOTE
# =====================================================
# def _from_delivery_note(doc):
#     dn = frappe.get_doc("Delivery Note", doc.reference_name)

#     if not doc.aql_party:
#         doc.aql_party = dn.customer

#     if not doc.aql_party_type:
#         doc.aql_party_type = "Customer"

#     calculated_lot_size = _get_lot_size_from_items(
#         doc, dn.items, "qty"
#     )

#     if not doc.lot_size:
#         doc.lot_size = calculated_lot_size


# =====================================================
# SALES INVOICE
# =====================================================
# def _from_sales_invoice(doc):
#     si = frappe.get_doc("Sales Invoice", doc.reference_name)

#     if not doc.aql_party:
#         doc.aql_party = si.customer

#     if not doc.aql_party_type:
#         doc.aql_party_type = "Customer"

#     calculated_lot_size = _get_lot_size_from_items(
#         doc, si.items, "qty"
#     )

#     if not doc.lot_size:
#         doc.lot_size = calculated_lot_size


# =====================================================
# STOCK ENTRY
# =====================================================
# def _from_stock_entry(doc):
#     se = frappe.get_doc("Stock Entry", doc.reference_name)

#     if not doc.aql_party:
#         doc.aql_party = se.company

#     if not doc.aql_party_type:
#         doc.aql_party_type = "Company"

#     lot_size = 0

#     if doc.item_code:
#         for row in se.items:
#             if row.item_code == doc.item_code:
#                 lot_size = row.transfer_qty or row.qty or 0
#                 break

#     if not lot_size:
#         lot_size = sum([
#             (row.transfer_qty or row.qty or 0)
#             for row in se.items
#         ])

#     if not doc.lot_size:
#         doc.lot_size = lot_size


# =====================================================
# JOB CARD
# =====================================================
# def _from_job_card(doc):
#     jc = frappe.get_doc("Job Card", doc.reference_name)

#     if not doc.aql_party:
#         doc.aql_party = jc.workstation

#     if not doc.aql_party_type:
#         doc.aql_party_type = "Workstation"

#     calculated_lot_size = (
#         jc.for_quantity
#         or jc.total_completed_qty
#         or 0
#     )

#     if not doc.lot_size:
#         doc.lot_size = calculated_lot_size
