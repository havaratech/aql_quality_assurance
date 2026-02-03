import frappe
from frappe.utils import getdate, today, now

from aql_quality_assurance.aql_quality_assurance_by_havaratech.services.supplier_aql_service import (
    process_supplier_aql
)

LOCK_TIMEOUT = 0  # do not wait


def _acquire_db_lock(lock_name):
    return frappe.db.sql(
        "SELECT GET_LOCK(%s, %s)",
        (lock_name, LOCK_TIMEOUT),
    )[0][0] == 1


def _release_db_lock(lock_name):
    try:
        frappe.db.sql("SELECT RELEASE_LOCK(%s)", (lock_name,))
    except Exception:
        pass


def run_supplier_aql_scheduler():
    """
    Cron-safe Supplier AQL Scheduler
    (DB advisory lock based – fully compatible)
    """

    if frappe.flags.in_test:
        return

    site = frappe.local.site
    lock_name = f"supplier_aql_scheduler::{site}"
    start_ts = now()

    # ---------------------------------------
    # Acquire DB lock
    # ---------------------------------------
    if not _acquire_db_lock(lock_name):
        frappe.logger("aql").warning(
            "Supplier AQL Scheduler skipped (already running)"
        )
        return

    # ---------------------------------------
    # HEARTBEAT (COMPATIBLE)
    # ---------------------------------------
    frappe.log_error(
        title="Supplier AQL Scheduler Heartbeat",
        message=f"Executed at {start_ts}"
    )

    frappe.logger("aql").info("Supplier AQL Scheduler STARTED")

    try:
        # --------------------------------
        # Load configuration
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
        # Fetch suppliers
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

            if frappe.db.get_value(
                "Supplier",
                supplier,
                "custom_aql_logic_override"
            ):
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
        _release_db_lock(lock_name)
        frappe.logger("aql").info(
            f"Supplier AQL Scheduler completed at {now()}"
        )
