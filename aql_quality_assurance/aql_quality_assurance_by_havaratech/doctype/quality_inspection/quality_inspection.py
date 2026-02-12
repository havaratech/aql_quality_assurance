import frappe
from frappe.utils import flt
import json
from frappe.model.document import Document
from erpnext.stock.doctype.quality_inspection.quality_inspection import QualityInspection as ERPNextQualityInspection, _
from frappe.utils import cint

class QualityInspection(ERPNextQualityInspection):

    def before_submit(self):
        if cint(self.custom_aql_inspection_skip) == 1:
            self.status = "Accepted"
            return        
        if self.status not in ("Accepted", "Rejected"):
            frappe.throw("Status should be <b>Accepted</b> or <b>Rejected</b>.", title="Invalid Status")        
        """ Prevent submission if any reading is not Accepted or Rejected """
        invalid_rows = []
        for row in self.readings:
            if row.status not in ("Accepted", "Rejected"):
                invalid_rows.append(
                    f"Row {row.idx}: {row.specification} → Status = {row.status or 'Blank'}"
                )
        if invalid_rows:
            frappe.throw(
                "Cannot submit Quality Inspection.<br><br>"
                "All readings must be <b>Accepted</b> or <b>Rejected</b>.<br><br>"
                + "<br>".join(invalid_rows),
                title="Invalid Reading Status"
            )

    def validate(self):
        self._capture_user_hold_status()
        super().validate()
        # UI / FIELD RESTRICTIONS ONLY
        self._apply_reading_field_restrictions()
        if self.readings and not frappe.flags.in_patch:
            for row in self.readings or []:
                # IF THIS ROW ALREADY EXISTS IN DB
                #if row.name and not row.is_new():
                before = row.get("_doc_before_save")
                    # PREVENT CHANGING AQL-DEFINING FIELDS
                if not before:
                    continue

                if (
                    row.specification != before.specification
                    or row.parameter_group != before.parameter_group
                    or row.custom_aql_classification != before.custom_aql_classification
                    or row.custom_aql_item_sample_no != before.custom_aql_item_sample_no
                ):
                    frappe.throw(
                        _("AQL parameters cannot be modified manually. "
                            "Change Template or Sample size to regenerate.")
                    )
                # MAKE READING_1 AND READING_VALUE READ-ONLY BASED ON NUMBERIC FLAG
                    if row.numeric:
                        row.reading_1_read_only = True
                        row.reading_value_read_only = False
                    else:
                        row.reading_1_read_only = False
                        row.reading_value_read_only = True
        # BASE AQL PARMS (NO STATUS YET)
        set_aql_parameters(self)
        # REGENERATE + CALCULATE AQL (CORE ENGINE)
        self._handle_aql_regeneration()
        # COPY CLASSIFICATION FROM TEMPLATE TO READINGS
        self.copy_aql_classification()
        # CALCULATE AQL RESULTS( COUNTS, STATUS)
        self.calculate_aql_server()
        # POST-PROCESS AQL LOGIC
        self._apply_optional_parameter_logic()
        # RESTORE HOLD STATE
        self._restore_hold_status()
        # CALCULATE STATUS COUNTS FOR CRITICAL, MAJOR, MINOR
        self.calculate_aql_status_counts()
        # CALCULATE AQL STATUS
        self.update_custom_aql_status()
        # FINAL STATUS DICISIONS (ONLY ONE PLACE) -- # Override parent status based on AQL results
        self.manual_inspection = 1
        if cint(self.custom_aql_inspection_skip) == 1:
            self.status = "Accepted"
        self.manual_inspection = 1    
        if cint(self.custom_aql_status_override) == 0:
            self.status = self.custom_aql_status         

        
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    #
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------

    def set_aql_parameters(doc):
        # ---------------- BASIC SAFETY ----------------
        if isinstance(doc, str):
            doc = frappe.get_doc(json.loads(doc))

        if not doc.reference_type or not doc.reference_name:
            frappe.msgprint("DEBUG: Missing Reference Type or Name")
            return doc.as_dict()

        ref_doc = frappe.get_doc(doc.reference_type, doc.reference_name)
        aql_global = frappe.get_single("AQL Settings")

        VALID_LEVELS = ['Gen I', 'Gen II', 'Gen III', 'Spl I', 'Spl II', 'Spl III', 'Spl IV']
        VALID_SCALES = ['0.065', '0.1', '0.15', '0.25', '0.4', '0.65', '1.0', '1.5', '2.5', '4', '6.5']

        # ---------------- PARTY SOURCE ----------------
        party_doc = None

        if doc.reference_type in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
            if ref_doc.get("supplier"):
                party_doc = frappe.get_doc("Supplier", ref_doc.supplier)
                doc.custom_aql_party_name =  ref_doc.supplier
                doc.custom_aql_party_type = "Supplier"

        elif doc.reference_type in ["Delivery Note", "Sales Invoice"]:
            if ref_doc.get("customer"):
                party_doc = frappe.get_doc("Customer", ref_doc.customer)
                doc.custom_aql_party_name = ref_doc.customer
                doc.custom_aql_party_type = "Customer"
        elif doc.reference_type == "Stock Entry":
            # INTERNAL transaction
            doc.custom_aql_party_name = ref_doc.company
            doc.custom_aql_party_type = "Company"
            party_doc = None   # explicitly no party source        
                

        # ---------------- ITEM SOURCE ----------------
        item_doc = frappe.get_doc("Item", doc.item_code) if doc.item_code else None

        # ---------------- FIELD-WISE RESOLUTION ----------------
        def resolve(field, valid_values, global_value):
            if party_doc and party_doc.get(field) in valid_values:
                return party_doc.get(field)
            if item_doc and item_doc.get(field) in valid_values:
                return item_doc.get(field)
            return global_value

        doc.custom_aql_inspection_level = resolve(
            "custom_aql_inspection_level",
            VALID_LEVELS,
            aql_global.aql_inspection_level
        )

        doc.custom_aql_critical_scale = resolve(
            "custom_aql_critical_scale",
            VALID_SCALES,
            aql_global.aql_critical_scale
        )

        doc.custom_aql_major_scale = resolve(
            "custom_aql_major_scale",
            VALID_SCALES,
            aql_global.aql_major_scale
        )

        doc.custom_aql_minor_scale = resolve(
            "custom_aql_minor_scale",
            VALID_SCALES,
            aql_global.aql_minor_scale
        )

        # ---------------- LOT SIZE ----------------
        if doc.item_code:
            if doc.reference_type == "Stock Entry":
                qty = sum(
                    flt(i.transfer_qty or i.qty)
                    for i in ref_doc.items
                    if i.item_code == doc.item_code
                )
            else:
                qty = sum(
                    flt(i.qty)
                    for i in ref_doc.items
                    if i.item_code == doc.item_code
                )
            doc.custom_aql_lot_size = int(qty)

        return doc.as_dict()

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    # OPTIONAL PARAMETER LOGIC
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _apply_optional_parameter_logic(self):
        """ If optional_parameter is enabled and no reading is provided, force status = Accepted """
        for row in self.readings:
            
            if not cint(row.get("custom_aql_optional_parameter")) == 1:
                continue
            # Check if ANY value is entered
            has_input = False

            if row.get("reading_value") and str(row.get("reading_value")).strip():
                has_input = True

            for i in range(1, 11):
                val = row.get(f"reading_{i}")
                if val is not None and str(val).strip():
                    has_input = True
                    break

            # If optional + no input → Accepted
            if not has_input:
                row.status = "Accepted"
                

    from frappe.utils import cint   
    
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    # DERIVE CUSTOM AQL STATUS
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def _row_has_input(self, row):
    # Non-numeric
        if row.get("reading_value") and str(row.get("reading_value")).strip():
            return True
    # Numeric
        for i in range(1, 11):
            val = row.get(f"reading_{i}")
            if val is not None and str(val).strip():
                return True
        return False

    def _capture_user_hold_status(self):
        self._hold_map = {}
        for row in self.readings:
            if cint(row.custom_aql_optional_parameter) == 1:
                continue
            if row.status in ("Pending", "On Hold") and not self._row_has_input(row):
                self._hold_map[row.name] = row.status


    def _restore_hold_status(self):
        for row in self.readings:
            if cint(row.custom_aql_optional_parameter) == 1:
                continue
            if row.name in getattr(self, "_hold_map", {}):
                # If user entered data now, do NOT restore
                if self._row_has_input(row):
                    continue
                row.status = self._hold_map[row.name]


    # ***********************************************************************************************************************************************************************
    # CALCULATE AQL STATUS COUNTS
    # ***********************************************************************************************************************************************************************   
    def calculate_aql_status_counts(self):
        """ Count rejected readings by classification and update actual result fields """

        critical_rejected = 0
        major_rejected = 0
        minor_rejected = 0

        for row in self.readings or []:
            if row.status != "Rejected":
                continue

            if row.custom_aql_classification == "Critical":
                critical_rejected += 1
            elif row.custom_aql_classification == "Major":
                major_rejected += 1
            elif row.custom_aql_classification == "Minor":
                minor_rejected += 1

        self.custom_aql_actual_critical_result = int(critical_rejected)
        self.custom_aql_actual_major_result = int(major_rejected)
        self.custom_aql_actual_minor_result = int(minor_rejected)

        

    def update_custom_aql_status(self):
        """ Update custom_aql_status based on actual results vs acceptable limits """

        critical_actual = int(self.custom_aql_actual_critical_result or 0)
        major_actual = int(self.custom_aql_actual_major_result or 0)
        minor_actual = int(self.custom_aql_actual_minor_result or 0)

        critical_limit = int(self.custom_aql_critical_acceptable_limit or 0)
        major_limit = int(self.custom_aql_major_acceptable_limit or 0)
        minor_limit = int(self.custom_aql_minor_acceptable_limit or 0)

        # Default
        self.custom_aql_status = "Accepted"

        if (
            critical_actual > critical_limit
            or major_actual > major_limit
            or minor_actual > minor_limit
        ):
            self.custom_aql_status = "Rejected"
            return
        
        has_on_hold = False
        has_pending = False

        for row in self.readings:
            if row.status == "On Hold":
                has_on_hold = True
            elif row.status == "Pending":
                has_pending = True

        if has_on_hold:
            self.custom_aql_status = "On Hold"
        elif has_pending:
            self.custom_aql_status = "Pending"
        else:
            self.custom_aql_status = "Accepted"        

        
        frappe.msgprint(
        f"AQL FINAL → Critical {critical_actual}/{critical_limit}, "
        f"Major {major_actual}/{major_limit}, Minor {minor_actual}/{minor_limit}, "
        f"Status = {self.custom_aql_status}"
        )

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

        self.custom_aql_critical_acceptable_limit = critical.get("accept", 0) 
        self.custom_aql_major_acceptable_limit = major.get("accept", 0)
        self.custom_aql_minor_acceptable_limit = minor.get("accept", 0)   

    def copy_aql_classification(self):
        """
        Copy custom_aql_classification from
        Quality Inspection Template -> Quality Inspection Readings
        (works for NEW / UNSAVED documents)
        """
        if not self.quality_inspection_template:
            return

        # Load template
        template = frappe.get_doc(
            "Quality Inspection Template",
            self.quality_inspection_template
        )

        # CORRECT child table
        template_rows = template.item_quality_inspection_parameter

        if not template_rows:
            frappe.throw("No Quality Inspection Parameters found in template")

        # Build map: specification → classification
        template_map = {
            p.specification: p.custom_aql_classification
            for p in template_rows
        }

        # Apply to readings
        for r in self.readings:
            if r.specification in template_map:
                r.custom_aql_classification = template_map[r.specification]
        # Build map: specification -> Optional Parameter
        template_optional_map = {
            p.specification: p.custom_aql_optional_parameter
            for p in template_rows
        } 

        # Apply to readings
        for r in self.readings:
            if r.specification in template_optional_map:
                r.custom_aql_optional_parameter = template_optional_map[r.specification]


    def _handle_aql_regeneration(self):
        """ Regenerate AQL readings ONLY when structure changes. Safe for new + existing documents.  """

        # -------- CASE 1: NEW DOCUMENT --------
        if not self.readings:
            self._generate_aql_readings()
            return

        # -------- CASE 2: EXISTING DOCUMENT --------
        old = self.get_doc_before_save()

        if not old:
            self.readings = []
            self._generate_aql_readings()   
            return

        structure_changed = (
            old.quality_inspection_template != self.quality_inspection_template
            or old.sample_size != self.sample_size
            or old.custom_aql_inspection_level != self.custom_aql_inspection_level
        )

        if not structure_changed:
            return

        # -------- PERMISSION CHECK --------
        if structure_changed:
            if not any(role in frappe.get_roles() for role in ("System Manager", "Administrator")):
                frappe.throw(
                    "Only System Manager / Administrator can regenerate AQL readings after structural changes."
            )

        # -------- REGENERATE --------
            self.readings = []
        self._generate_aql_readings()
 
    def _generate_aql_readings(self):
        """  Create readings as: Sample Size x Parameters (each with its own classification)   """
        if not self.quality_inspection_template:
            return

        if not self.sample_size or int(self.sample_size) <= 0:
            return

        template = frappe.get_doc(
            "Quality Inspection Template",
            self.quality_inspection_template
        )

        parameters = template.item_quality_inspection_parameter
        if not parameters:
            frappe.throw("No Quality Inspection Parameters found in template")
            

        ref = self.reference_name or "REF"
        item = self.item_code or "ITEM"
        total_sample_size = int(self.sample_size)

        # Index existing rows by (sample_no, param_key)
        existing_map = {
            (r.custom_aql_item_sample_no, r.specification, r.parameter_group, r.custom_aql_classification): r
            for r in self.readings
        }        

        for sample_no in range(1, total_sample_size + 1):
            sample_id = f"{ref}-{item}-S{sample_no}"

            for p in parameters:
                key = (
                    p.specification,
                    p.parameter_group,
                    p.custom_aql_classification
                )

                map_key = (sample_id, *key)

                if map_key in existing_map:
                    continue  # already exists

                # Create new row
                row = self.append("readings", {})
                row.specification = p.specification
                row.parameter_group = p.parameter_group
                row.custom_aql_classification = p.custom_aql_classification
                row.custom_aql_item_sample_no = sample_id
                row.numeric = p.numeric
                row.min_value = p.min_value
                row.max_value = p.max_value
                #row.manual_inspection = p.manual_inspection
                row.formula_based_criteria = p.formula_based_criteria
                row.status = "Pending"
                row.value = p.value
                row.custom_aql_optional_parameter = p.custom_aql_optional_parameter                

    def _lock_readings_for_non_admin(self):
        """ Lock readings table for non-admin users """
        if not any(role in frappe.get_roles() for role in ("System Manager", "Administrator")):
            return

        if not self.is_new():
            old = self.get_doc_before_save()
            if not old:
                return
            
            if len(self.readings) != len(old.readings):
                frappe.throw("Only Administrator or System Manager can modify Quality Inspection Readings.")

            for i, row in enumerate(self.readings):
                old_row = old.readings[i]

                # Allow only status and remarks to be changed
                protected_fields = [
                    "specification",
                    "parameter_group",
                    "custom_aql_classification",
                    "custom_aql_item_sample_no",
                    "numeric",
                    "min_value",
                    "max_value",
                    "formula_based_criteria"
                ]
                for field in protected_fields:
                    if row.get(field) != old_row.get(field):
                        frappe.throw("Only Administrator or System Manager can modify Quality Inspection Readings.")

    def on_trash(self):
        if not any(role in frappe.get_roles() for role in ("System Manager", "Administrator")):
            frappe.throw("Only Administrator or System Manager can delete Quality Inspections.")     

    # def _is_restricted_reading_mode(self):
    #     return frappe.db.get_single_value(
    #         "AQL Settings",
    #         "quality_inspection_reading_settings"
    #     ) == 1

    def _apply_reading_field_restrictions(self):
        """
        When restricted mode is ON:
        - All fields in Readings table are read-only
        - Except reading_1 … reading_10 and reading_value
        """

        # if not self._is_restricted_reading_mode():
        #     return

        allowed = {"reading_value"} | {f"reading_{i}" for i in range(1, 11)}

        for row in self.readings:
            for field in row.meta.fields:
                fname = field.fieldname

                if fname in allowed:
                    row.set(f"{fname}_read_only", 0)
                else:
                    row.set(f"{fname}_read_only", 1)

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# AQL CALCULATION HELPERS - SERVER-SIDE HELPER FUNCTIONS
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------

def normalize_inspection_level(level):
    """ Convert ERPNext values to ANSI lookup code: Gen I -> I, Gen II -> II, Spl III -> S3, etc. """
    level = level.strip()

    if level.startswith("Gen"):
        return level.replace("Gen", "").strip()

    if level.startswith("Spl"):
        roman = level.replace("Spl", "").strip()
        roman_map = {"I": "1", "II": "2", "III": "3", "IV": "4"}
        return "S" + roman_map[roman]

    return level


def normalize_lot_size(qty):
    """ Round lot size to nearest ANSI range """
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


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# SAMPLE SIZE CALCULATION - AQL LETTER TABLES
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# CALCULATION LOGIC
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------

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
    
# WHITELISTED FUNCTION FOR CUSTOM BUTTON
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
    
    # Refresh AQL parameters from supplier/customer
    doc.set_aql_parameters()
    # Calculate sample size & accept/reject limits
    doc.calculate_aql_server()
    # Get classification copied
    doc.copy_aql_classification()
    # readings calc
    doc._handle_aql_regeneration()


    return doc.as_dict()



@frappe.whitelist()
def calculate_aql_status_counts(doc):
    """Calculate AQL status counts and return updated values"""

    if isinstance(doc, str):
        doc = frappe.get_doc(json.loads(doc))

    if not isinstance(doc, QualityInspection):
        doc.__class__ = QualityInspection

    # Calculate counts
    doc.calculate_aql_status_counts()

    # Return everything
    return {
        "custom_aql_actual_critical_result": doc.custom_aql_actual_critical_result,
        "custom_aql_actual_major_result": doc.custom_aql_actual_major_result,
        "custom_aql_actual_minor_result": doc.custom_aql_actual_minor_result
    }

@frappe.whitelist()
def update_custom_aql_status(doc):
    """ update aql calc status """    
    if isinstance(doc, str):
        doc = frappe.get_doc(json.loads(doc))

    if not isinstance(doc, QualityInspection):
        doc.__class__ = QualityInspection

    doc.update_custom_aql_status()

    return {
        "custom_aql_status": doc.custom_aql_status
    }        
    
@frappe.whitelist()
def run_copy_aql_classification(doc):
    """
    Copy custom_aql_classification from
    Quality Inspection Template -> Quality Inspection Readings
    (works for NEW / UNSAVED documents)
    """
    import json

    # Handle JS-passed doc
    if isinstance(doc, str):
        doc = frappe.get_doc(json.loads(doc))

    if not doc.quality_inspection_template:
        return doc.as_dict()

    # Load template
    template = frappe.get_doc(
        "Quality Inspection Template",
        doc.quality_inspection_template
    )

    # CORRECT child table
    template_rows = template.item_quality_inspection_parameter

    if not template_rows:
        frappe.throw("No Quality Inspection Parameters found in template")

    # Build map: specification → classification
    template_map = {
        p.specification: p.custom_aql_classification
        for p in template_rows
    }

    # Apply to readings
    for r in doc.readings:
        if r.specification in template_map:
            r.custom_aql_classification = template_map[r.specification]

    return doc.as_dict()

@frappe.whitelist()
def set_aql_parameters(doc):
    # ---------------- BASIC SAFETY -----------------------------------------------------------------------------------------------------------------------
    if isinstance(doc, str):
        doc = frappe.get_doc(json.loads(doc))

    if not doc.reference_type or not doc.reference_name:
        frappe.msgprint("DEBUG: Missing Reference Type or Name")
        return doc.as_dict()

    ref_doc = frappe.get_doc(doc.reference_type, doc.reference_name)
    aql_global = frappe.get_single("AQL Settings")

    VALID_LEVELS = ['Gen I', 'Gen II', 'Gen III', 'Spl I', 'Spl II', 'Spl III', 'Spl IV']
    VALID_SCALES = ['0.065', '0.1', '0.15', '0.25', '0.4', '0.65', '1.0', '1.5', '2.5', '4', '6.5']

    # ---------------- PARTY SOURCE -------------------------------------------------------------------------------------------------------------------------
    party_doc = None

    if doc.reference_type in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]:
        if ref_doc.get("supplier"):
            party_doc = frappe.get_doc("Supplier", ref_doc.supplier)
            doc.custom_aql_party_name = ref_doc.supplier
            doc.custom_aql_party_type = "Supplier"

    elif doc.reference_type in ["Delivery Note", "Sales Invoice"]:
        if ref_doc.get("customer"):
            party_doc = frappe.get_doc("Customer", ref_doc.customer)
            doc.custom_aql_party_name = ref_doc.customer
            doc.custom_aql_party_type = "Customer"
    elif doc.reference_type == "Stock Entry":
        # INTERNAL transaction
        doc.custom_aql_party_name = ref_doc.company
        doc.custom_aql_party_type = "Company"
        party_doc = None   # explicitly no party source        

    # ---------------- ITEM SOURCE ---------------------------------------------------------------------------------------------------------------------------
    item_doc = frappe.get_doc("Item", doc.item_code) if doc.item_code else None

    # ---------------- FIELD-WISE RESOLUTION ------------------------------------------------------------------------------------------------------------------
    def resolve(field, valid_values, global_value):
        if party_doc and party_doc.get(field) in valid_values:
            return party_doc.get(field)
        if item_doc and item_doc.get(field) in valid_values:
            return item_doc.get(field)
        return global_value

    doc.custom_aql_inspection_level = resolve(
        "custom_aql_inspection_level",
        VALID_LEVELS,
        aql_global.aql_inspection_level
    )

    doc.custom_aql_critical_scale = resolve(
        "custom_aql_critical_scale",
        VALID_SCALES,
        aql_global.aql_critical_scale
    )

    doc.custom_aql_major_scale = resolve(
        "custom_aql_major_scale",
        VALID_SCALES,
        aql_global.aql_major_scale
    )

    doc.custom_aql_minor_scale = resolve(
        "custom_aql_minor_scale",
        VALID_SCALES,
        aql_global.aql_minor_scale
    )

    # ---------------- LOT SIZE ---------------------------------------------------------------------------------------------------------------------------------
    if doc.item_code:
        if doc.reference_type == "Stock Entry":
            qty = sum(
                flt(i.transfer_qty or i.qty)
                for i in ref_doc.items
                if i.item_code == doc.item_code
            )
        else:
            qty = sum(
                flt(i.qty)
                for i in ref_doc.items
                if i.item_code == doc.item_code
            )
        doc.custom_aql_lot_size = int(qty)

    return doc.as_dict()

# -------------------------            
# WHITELISTED WRAPPER (THIS IS WHAT JS CALLS)
# -------------------------
@frappe.whitelist()
def run_calculate_aql_server(name):
    """ Button-triggered AQL calculation -Sample size """
    doc = frappe.get_doc("Quality Inspection", name)
    doc.calculate_aql_server()
    doc.save()
    return {
        "status": "success",
    }


