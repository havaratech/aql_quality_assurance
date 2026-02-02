import frappe
from frappe.utils import getdate, today, now

from aql_quality_assurance.aql_quality_assurance_by_havaratech.services.supplier_aql_service import (
    process_supplier_aql
)

# ---------------------------------------
# Scheduler Lock Configuration
# ---------------------------------------
LOCK_TTL = 6 * 60  # 6 minutes


def run_supplier_aql_scheduler():
    """
    Cron-safe Supplier AQL Scheduler.

    - Runs every 5 minutes
    - Redis lock protected (no parallel execution)
    - Idempotent (UPSERT logic)
    """

    if frappe.flags.in_test:
        return

    site = frappe.local.site
    cache = frappe.cache()

    lock_key = f"supplier_aql_scheduler_running::{site}"
    start_ts = now()

    # ---------------------------------------
    # Atomic Redis lock (no race condition)
    # ---------------------------------------
    if not cache.add_value(lock_key, start_ts, expires_in_sec=LOCK_TTL):
        frappe.logger("aql").warning(
            "Supplier AQL Scheduler skipped (already running)"
        )
        return

    # ---------------------------------------
    # HEARTBEAT (only if lock acquired)
    # ---------------------------------------
    frappe.log_error(
        message=f"Supplier AQL Scheduler executed at {start_ts}",
        method="supplier_aql_scheduler_heartbeat"
    )

    frappe.logger("aql").info("Supplier AQL Scheduler STARTED")

    try:
        # --------------------------------
        # Load global configuration
        # --------------------------------
        config = frappe.get_single(
            "AQL Classification Quality Inspection Setting"
        )

        if not config.inspection_start_from:
            frappe.logger("aql").warning(
                "Scheduler aborted: inspection_start_from not set"
            )
            return

        start_date = getdate(config.inspection_start_from)
        end_date = (
            getdate(config.inspection_end_to)
            if config.inspection_end_to
            else getdate(today())
        )

        # --------------------------------
        # Fetch suppliers with submitted QI
        # --------------------------------
        suppliers = frappe.db.sql("""
            SELECT DISTINCT custom_aql_party_names
            FROM `tabQuality Inspection`
            WHERE
                docstatus = 1
                AND custom_aql_party_type = 'Supplier'
                AND report_date BETWEEN %s AND %s
        """, (start_date, end_date), as_list=True)

        frappe.logger("aql").info(
            f"Supplier AQL Scheduler found {len(suppliers)} suppliers"
        )

        # --------------------------------
        # Process suppliers
        # --------------------------------
        for (supplier,) in suppliers:
            if not supplier:
                continue

            # Supplier-level override
            if frappe.db.get_value(
                "Supplier",
                supplier,
                "custom_aql_logic_override"
            ):
                frappe.logger("aql").info(
                    f"Supplier {supplier} skipped (override enabled)"
                )
                continue

            process_supplier_aql(
                supplier=supplier,
                start_date=start_date,
                end_date=end_date,
                min_threshold=config.supplier_min_threshold,
                max_threshold=config.supplier_max_threshold
            )

        frappe.logger("aql").info("Supplier AQL Scheduler FINISHED")

    except Exception:
        frappe.log_error(
            title="Supplier AQL Scheduler Failed",
            message=frappe.get_traceback()
        )
        raise

    finally:
        # --------------------------------
        # Always release lock
        # --------------------------------
        cache.delete_value(lock_key)

        frappe.logger("aql").info(
            f"Supplier AQL Scheduler completed in {now()}"
        )
