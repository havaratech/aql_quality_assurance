import frappe
from frappe.utils import flt
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
    PurchaseReceipt as ERPNextPurchaseReceipt
)


class PurchaseReceipt(ERPNextPurchaseReceipt):

    # ---------------------------------------------------------
    # VALIDATE
    # ---------------------------------------------------------
    def validate(self):

        # apply qty movement before validation
        self.apply_qi_result()

        # run normal ERP validation
        super().validate()

    # ---------------------------------------------------------
    # APPLY QUALITY INSPECTION RESULT
    # ---------------------------------------------------------
    def apply_qi_result(self):

        for item in self.items:

            if not item.quality_inspection:
                continue

            qi_status = frappe.db.get_value(
                "Quality Inspection",
                item.quality_inspection,
                "status"
            )

            # -----------------------------
            # ACCEPTED → do nothing
            # -----------------------------
            if qi_status == "Accepted":
                continue

            # -----------------------------
            # REJECTED → move qty
            # -----------------------------
            if qi_status == "Rejected":

                total_received = flt(item.received_qty)

                item.qty = 0
                item.rejected_qty = total_received

                if not item.rejected_warehouse:
                    item.rejected_warehouse = item.warehouse

                if item.batch_no and not item.rejected_batch_no:
                    item.rejected_batch_no = item.batch_no

    def validate_inspection(self):

        # ⭐ IMPORTANT
        # run inspection check ONLY during submit
        if self.docstatus == 0:
            return

        errors = []

        for row in self.items:

            if not row.quality_inspection:
                errors.append(
                    f"Row #{row.idx}: Quality Inspection required for item {row.item_code}"
                )
                continue

            qi = frappe.db.get_value(
                "Quality Inspection",
                row.quality_inspection,
                ["docstatus", "status"],
                as_dict=True
            )

            if not qi:
                errors.append(
                    f"Row #{row.idx}: Quality Inspection not found"
                )
                continue

            if qi.docstatus != 1:
                errors.append(
                    f"Row #{row.idx}: Quality Inspection not submitted for item {row.item_code}"
                )
                continue

            # ⭐ YOUR RULE
            if qi.status == "Rejected":
                continue

        if errors:
            frappe.throw("<br>".join(errors))



