import frappe
from frappe.utils import flt
import json
from frappe.model.document import Document

@frappe.whitelist()
def set_aql_parameters(doc, method=None):
    # if called from JS, 'doc' is a JSON string. must convert it to a doc object
    if isinstance(doc, str):
        doc = frappe.get_doc(json.loads(doc))

    # --- TRACE 1: Check if hook is working ---# If you see this message when saving, the hook is connected.# If you DON'T see it, the problem is in your hooks.py path.
    #frappe.msgprint("DEBUG: set_aql_parameters started")

    if not doc.reference_type or not doc.reference_name:
        frappe.msgprint("DEBUG: Missing Reference Type or Name")
        return doc.as_dict()    

    # --- TRACE 2: Verify Reference Doc Loading ---
    try:
        ref_doc = frappe.get_doc(doc.reference_type, doc.reference_name)
    #    frappe.msgprint(f"DEBUG: Successfully loaded {doc.reference_type}: {doc.reference_name}")
    except Exception as e:
    #    frappe.msgprint(f"DEBUG: Error loading reference: {e}")
        return doc.as_dict()

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
            doc.custom_aql_inspection_level = s_master.get("custom_aql_inspection_level")
            doc.custom_aql_critical_scale = s_master.get("custom_aql_critical_scale")
            doc.custom_aql_major_scale = s_master.get("custom_aql_major_scale")
            doc.custom_aql_minor_scale = s_master.get("custom_aql_minor_scale")             
    #        frappe.msgprint(f"DEBUG: Found Supplier {s_master.supplier_name}")
    #    else:
    #        frappe.msgprint("DEBUG: No Supplier ID found in reference doc")

    # --- TRACE 4: Process Customer Documents ---
    elif doc.reference_type in ["Delivery Note", "Sales Invoice"]:
        c_id = ref_doc.get("customer")
        if c_id:
            c_master = frappe.get_doc("Customer", c_id)
            doc.custom_aql_party_name = c_master.customer_name
            doc.custom_aql_party_type = c_master.customer_type
            doc.custom_aql_inspection_level = c_master.get("custom_aql_inspection_level")
            doc.custom_aql_critical_scale = c_master.get("custom_aql_critical_scale")
            doc.custom_aql_major_scale = c_master.get("custom_aql_major_scale")
            doc.custom_aql_minor_scale = c_master.get("custom_aql_minor_scale")
    #frappe.msgprint(f"DEBUG: Found Customer {c_master.customer_name}")

    # Lot size logic
    if doc.item_code:
        qty = sum([flt(i.qty) for i in ref_doc.get("items") if i.item_code == doc.item_code])
        doc.custom_aql_lot_size = qty

    return doc.as_dict()


class QualityInspection(Document):
    def validate(self):
        set_aql_parameters(self)
        """Ensure AQL is calculated on save/submit"""
        self.calculate_aql_server()

    def calculate_aql_server(self):
        """
        Server-side AQL calculation: sample_size, critical, major, minor
        """
        lot = self.custom_aql_lot_size
        level = self.custom_aql_inspection_level
        critical_scale = self.custom_aql_critical_scale
        major_scale = self.custom_aql_major_scale
        minor_scale = self.custom_aql_minor_scale

        if not lot or not level:
            frappe.throw("Lot size or Inspection Level is missing")

        # Normalize inspection level for internal lookup
        level_code = normalize_inspection_level(level)

        # Calculate sample size first
        sample_size = calculate_sample_size(lot, level_code)  
        self.sample_size = sample_size

        # Calculate AQL for critical, major, minor
        critical = calculate_aql_value(lot, level_code, critical_scale)
        major = calculate_aql_value(lot, level_code, major_scale)
        minor = calculate_aql_value(lot, level_code, minor_scale)

        self.custom_aql_critical_acceptable_limit = int(critical["accept"])
        self.custom_aql_major_acceptable_limit = int(major["accept"])
        self.custom_aql_minor_acceptable_limit = int(minor["accept"])   
        
        frappe.msgprint("Server-side AQL calculated successfully")

# 🔥 WHITELISTED WRAPPER (THIS IS WHAT JS CALLS)
@frappe.whitelist()
def calculate_aql_server(name):
    """
    Button-triggered AQL calculation
    """
    doc = frappe.get_doc("Quality Inspection", name)
    doc.calculate_aql_server()
    doc.save()
    return {
        "status": "success",
    }

# -------------------------
# SERVER-SIDE HELPER FUNCTIONS
# -------------------------

def normalize_inspection_level(level):
    """
    Convert ERPNext values to ANSI lookup code:
    Gen I -> I, Gen II -> II, Spl III -> S3, etc.
    """
    level = level.strip()

    if level.startswith("Gen"):
        return level.replace("Gen", "").strip()

    if level.startswith("Spl"):
        roman = level.replace("Spl", "").strip()
        roman_map = {"I": "1", "II": "2", "III": "3", "IV": "4"}
        return "S" + roman_map[roman]

    return level


def normalize_lot_size(qty):
    """
    Round lot size to nearest ANSI range
    """
    qty = int(qty)
    if qty <= 8: return 8
    if qty <= 15: return 15
    if qty <= 25: return 25
    if qty <= 50: return 50
    if qty <= 90: return 90
    if qty <= 150: return 150
    if qty <= 280: return 280
    if qty <= 500: return 500
    if qty <= 1200: return 1200
    if qty <= 3200: return 3200
    if qty <= 10000: return 10000
    if qty <= 35000: return 35000
    if qty <= 150000: return 150000
    if qty <= 500000: return 500000
    return 500001


# -------------------------
# AQL LETTER TABLES
# -------------------------

AQLLetters = {
    # General levels
    "I-8":"A","I-15":"A","I-25":"B","I-50":"C","I-90":"C","I-150":"D",
    "I-280":"E","I-500":"F","I-1200":"G","I-3200":"H","I-10000":"J",
    "I-35000":"K","I-150000":"L","I-500000":"M","I-500001":"N",

    "II-8":"A","II-15":"B","II-25":"C","II-50":"D","II-90":"E","II-150":"F",
    "II-280":"G","II-500":"H","II-1200":"J","II-3200":"K","II-10000":"L",
    "II-35000":"M","II-150000":"N","II-500000":"P","II-500001":"Q",

    "III-8":"B","III-15":"C","III-25":"D","III-50":"E","III-90":"F",
    "III-150":"G","III-280":"H","III-500":"J","III-1200":"K",
    "III-3200":"L","III-10000":"M","III-35000":"N","III-150000":"P",
    "III-500000":"Q","III-500001":"R",

    # Special levels
    "S1-8":"A","S1-15":"A","S1-25":"A","S1-50":"A","S1-90":"B","S1-150":"B",
    "S1-280":"B","S1-500":"B","S1-1200":"C","S1-3200":"C","S1-10000":"C",
    "S1-35000":"C","S1-150000":"D","S1-500000":"D","S1-500001":"D",

    "S2-8":"A","S2-15":"A","S2-25":"A","S2-50":"B","S2-90":"B","S2-150":"B",
    "S2-280":"C","S2-500":"C","S2-1200":"C","S2-3200":"D","S2-10000":"D",
    "S2-35000":"D","S2-150000":"E","S2-500000":"E","S2-500001":"E",

    "S3-8":"A","S3-15":"A","S3-25":"B","S3-50":"B","S3-90":"C","S3-150":"C",
    "S3-280":"D","S3-500":"D","S3-1200":"E","S3-3200":"E","S3-10000":"F",
    "S3-35000":"F","S3-150000":"G","S3-500000":"G","S3-500001":"H",

    "S4-8":"A","S4-15":"A","S4-25":"B","S4-50":"C","S4-90":"C","S4-150":"D",
    "S4-280":"E","S4-500":"E","S4-1200":"F","S4-3200":"G","S4-10000":"G",
    "S4-35000":"H","S4-150000":"J","S4-500000":"J","S4-500001":"K"
}

# Default sample size per letter (fallback)
AQLSampleSizeByLetter = {
    "A": 2,"B": 3,"C": 5,"D": 8,"E": 13,"F": 20,"G": 32,"H": 50,
    "J": 80,"K": 125,"L": 200,"M": 315,"N": 500,"P": 800,"Q": 1250,"R": 2000
}

# Minimal AQL Sample table, extend as needed
# Full AQL sample size mapping
AQLSampleSize = {
    "A0.065": (200,0,1),"A0.10": (125,0,1),"A0.15": (80,0,1),"A0.25": (50,0,1),"A0.40": (32,0,1),"A0.65": (20,0,1),"A1.0": (13,0,1),"A1.5": (8,0,1),"A2.5": (5,0,1),"A4.0": (3,0,1),"A6.5": (2,0,1),
    "B0.065": (200,0,1),"B0.10": (125,0,1),"B0.15": (80,0,1),"B0.25": (50,0,1),"B0.40": (32,0,1),"B0.65": (20,0,1),"B1.0": (13,0,1),"B1.5": (8,0,1),"B2.5": (5,0,1),"B4.0": (3,0,1),"B6.5": (2,0,1),
    "C0.065": (200,0,1),"C0.10": (125,0,1),"C0.15": (80,0,1),"C0.25": (50,0,1),"C0.40": (32,0,1),"C0.65": (20,0,1),"C1.0": (13,0,1),"C1.5": (8,0,1),"C2.5": (5,0,1),"C4.0": (3,0,1),"C6.5": (8,1,2),
    "D0.065": (200,0,1),"D0.10": (125,0,1),"D0.15": (80,0,1),"D0.25": (50,0,1),"D0.40": (32,0,1),"D0.65": (20,0,1),"D1.0": (13,0,1),"D1.5": (8,0,1),"D2.5": (5,0,1),"D4.0": (13,1,2),"D6.5": (8,1,2),
    "E0.065": (200,0,1),"E0.10": (125,0,1),"E0.15": (80,0,1),"E0.25": (50,0,1),"E0.40": (32,0,1),"E0.65": (20,0,1),"E1.0": (13,0,1),"E1.5": (8,0,1),"E2.5": (20,1,2),"E4.0": (13,1,2),"E6.5": (13,2,3),
    "F0.065": (200,0,1),"F0.10": (125,0,1),"F0.15": (80,0,1),"F0.25": (50,0,1),"F0.40": (32,0,1),"F0.65": (20,0,1),"F1.0": (13,0,1),"F1.5": (32,1,2),"F2.5": (20,1,2),"F4.0": (20,2,3),"F6.5": (20,3,4),
    "G0.065": (200,0,1),"G0.10": (125,0,1),"G0.15": (80,0,1),"G0.25": (50,0,1),"G0.40": (32,0,1),"G0.65": (20,0,1),"G1.0": (50,1,2),"G1.5": (32,1,2),"G2.5": (32,2,3),"G4.0": (32,3,4),"G6.5": (32,5,6),
    "H0.065": (200,0,1),"H0.10": (125,0,1),"H0.15": (80,0,1),"H0.25": (50,0,1),"H0.40": (32,0,1),"H0.65": (80,1,2),"H1.0": (50,1,2),"H1.5": (50,2,3),"H2.5": (50,3,4),"H4.0": (50,5,6),"H6.5": (50,7,8),
    "J0.065": (200,0,1),"J0.10": (125,0,1),"J0.15": (80,0,1),"J0.25": (50,0,1),"J0.40": (125,1,2),"J0.65": (80,1,2),"J1.0": (80,2,3),"J1.5": (80,3,4),"J2.5": (80,5,6),"J4.0": (80,7,8),"J6.5": (80,10,11),
    "K0.065": (200,0,1),"K0.10": (125,0,1),"K0.15": (80,0,1),"K0.25": (200,1,2),"K0.40": (125,1,2),"K0.65": (125,2,3),"K1.0": (125,3,4),"K1.5": (125,5,6),"K2.5": (125,7,8),"K4.0": (125,10,11),"K6.5": (125,14,15),
    "L0.065": (200,0,1),"L0.10": (125,0,1),"L0.15": (315,1,2),"L0.25": (200,1,2),"L0.40": (200,2,3),"L0.65": (200,3,4),"L1.0": (200,5,6),"L1.5": (200,7,8),"L2.5": (200,10,11),"L4.0": (200,14,15),"L6.5": (200,21,22),
    "M0.065": (200,0,1),"M0.10": (500,1,2),"M0.15": (315,1,2),"M0.25": (315,2,3),"M0.40": (315,3,4),"M0.65": (315,5,6),"M1.0": (315,7,8),"M1.5": (315,10,11),"M2.5": (315,14,15),"M4.0": (315,21,22),"M6.5": (200,21,22),
    "N0.065": (800,1,2),"N0.10": (500,1,2),"N0.15": (500,2,3),"N0.25": (500,3,4),"N0.40": (500,5,6),"N0.65": (500,7,8),"N1.0": (500,10,11),"N1.5": (500,14,15),"N2.5": (500,21,22),"N4.0": (315,21,22),"N6.5": (200,21,22),
    "P0.065": (800,1,2),"P0.10": (800,2,3),"P0.15": (800,3,4),"P0.25": (800,5,6),"P0.40": (800,7,8),"P0.65": (800,10,11),"P1.0": (800,14,15),"P1.5": (800,21,22),"P2.5": (500,21,22),"P4.0": (315,21,22),"P6.5": (200,21,22),
    "Q0.065": (1250,2,3),"Q0.10": (1250,3,4),"Q0.15": (1250,5,6),"Q0.25": (1250,7,8),"Q0.40": (1250,10,11),"Q0.65": (1250,14,15),"Q1.0": (1250,21,22),"Q1.5": (800,21,22),"Q2.5": (500,21,22),"Q4.0": (315,21,22),"Q6.5": (200,21,22),
    "R0.065": (2000,3,4),"R0.10": (2000,5,6),"R0.15": (2000,7,8),"R0.25": (2000,10,11),"R0.40": (2000,14,15),"R0.65": (2000,21,22),"R1.0": (1250,21,22),"R1.5": (800,21,22),"R2.5": (500,21,22),"R4.0": (315,21,22),"R6.5": (200,21,22)
}

# -------------------------
# CALCULATION LOGIC
# -------------------------

def calculate_sample_size(lot, level_code):
    """
    Calculate sample size from ANSI tables; fallback to letter if missing
    """
    normalized_lot = normalize_lot_size(lot)
    letter_key = f"{level_code}-{normalized_lot}"
    letter = AQLLetters.get(letter_key)

    if not letter:
        frappe.throw(f"AQL Letter not found for {letter_key}")

        # Sample size comes ONLY from letter
    sample_size = AQLSampleSizeByLetter.get(letter)

    if sample_size is None:
        frappe.throw(f"Sample size not defined for AQL letter {letter}")

    return int(sample_size)


def calculate_aql_value(lot, level_code, aql_value):
    """
    Return dict with sample, accept, reject
    """
    normalized_lot = normalize_lot_size(lot)
    letter_key = f"{level_code}-{normalized_lot}"
    letter = AQLLetters.get(letter_key)

    if not letter:
        return {"sample": 0, "accept": 0, "reject": 0}

    key = f"{letter}{aql_value}"
    row = AQLSampleSize.get(key)

    if row:
        #sample_size, accept_limit, reject_limit = map(int, row.split(","))
        sample_size, accept_limit, reject_limit = row
        return {"sample": sample_size, "accept": accept_limit, "reject": reject_limit}
    else:
        # fallback to default accept/reject = 0
        return {"sample": AQLSampleSizeByLetter.get(letter, normalized_lot), "accept": 0, "reject": 0}
    
# 🔥 WHITELISTED FUNCTION FOR CUSTOM BUTTON
@frappe.whitelist()
def refresh_aql_logic(doc):
    """
    Refreshes AQL parameters, calculates sample size and limits.
    Called from JS custom button.
    """
    if isinstance(doc, str):
        doc_dist = json.loads(doc)
    else:
        doc_dist = doc

    doc = frappe.get_doc({
        **doc_dist, "doctype": "Quality Inspection"
    })
    
    if not isinstance(doc, QualityInspection):
        doc.__class__ = QualityInspection
    
    # 1️⃣ Refresh AQL parameters from supplier/customer
    set_aql_parameters(doc)
    # 2️⃣ Calculate sample size & accept/reject limits
    doc.calculate_aql_server()
    # 3️⃣ Return updated doc (do not save automatically)
    return doc.as_dict()
    
   