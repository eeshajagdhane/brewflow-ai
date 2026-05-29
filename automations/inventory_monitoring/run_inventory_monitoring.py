"""Inventory monitoring automation for BrewFlow AI.

Deterministic — no LLM calls.
Reads store_inventory.csv via inventory_matching utilities and classifies
each ingredient into: low_stock, healthy, overstock, or unavailable.

Usage::

    from automations.inventory_monitoring.run_inventory_monitoring import run_inventory_monitoring
    result = run_inventory_monitoring("SD001", "2024-01-15")
"""

from __future__ import annotations

from typing import Optional

from utils.inventory_matching import (
    STATUS_HEALTHY,
    STATUS_LOW_STOCK,
    STATUS_OVERSTOCK,
    STATUS_UNAVAILABLE,
    classify_inventory_status,
    get_inventory_snapshot,
)
from utils.workflow_common import make_tool_response


def run_inventory_monitoring(
    store_id: str,
    date: str,
    ingredient_filter: Optional[list[str]] = None,
) -> dict:
    """Check inventory status for a store on a given date.

    Args:
        store_id: Store identifier (e.g. "SD001").
        date: Target date string "YYYY-MM-DD".
        ingredient_filter: Optional list of ingredient names to limit results to.
                           If None, checks all ingredients in the snapshot.

    Returns:
        Tool response with data.low_stock, data.overstock, data.unavailable,
        data.healthy_count, snapshot_date_used.
        status is "needs_review" if any unavailable items exist,
        "warning" if any low_stock items exist, "success" otherwise.
    """
    snapshot_result = get_inventory_snapshot(store_id, date)

    if snapshot_result["status"] == "error":
        return make_tool_response(
            status="error",
            errors=[snapshot_result.get("message", "Inventory snapshot unavailable.")],
            data={"store_id": store_id, "requested_date": date},
        )

    df = snapshot_result["data"]
    snapshot_date = snapshot_result["snapshot_date"]
    base_warnings = snapshot_result.get("warnings", [])

    # Optional ingredient filter (case-insensitive)
    if ingredient_filter:
        filter_lower = [i.lower() for i in ingredient_filter]
        df = df[df["ingredient"].str.lower().isin(filter_lower)].copy()

    low_stock: list[dict] = []
    overstock: list[dict] = []
    healthy_count = 0
    unavailable: list[dict] = []

    for _, row in df.iterrows():
        status = classify_inventory_status(row)
        entry = {
            "ingredient": row["ingredient"],
            "ingredient_category": row.get("ingredient_category", ""),
            "closing_stock_units": float(row.get("closing_stock_units", 0)),
            "reorder_point": float(row.get("reorder_point", 0)),
            "stock_status": str(row.get("stock_status", "")),
            "inventory_flag": str(row.get("inventory_flag", "")),
            "supplier_delay_flag": str(row.get("supplier_delay_flag", "")),
        }
        if status == STATUS_UNAVAILABLE:
            unavailable.append(entry)
        elif status == STATUS_LOW_STOCK:
            low_stock.append(entry)
        elif status == STATUS_OVERSTOCK:
            overstock.append(entry)
        else:
            healthy_count += 1

    alert_warnings = []
    if unavailable:
        names = [i["ingredient"] for i in unavailable]
        alert_warnings.append(f"Unavailable ingredients: {', '.join(names)}.")
    if low_stock:
        names = [i["ingredient"] for i in low_stock]
        alert_warnings.append(f"Low stock: {', '.join(names[:5])}{'...' if len(names) > 5 else ''}.")

    overall_status = "success"
    if unavailable:
        overall_status = "needs_review"
    elif low_stock:
        overall_status = "warning"

    return make_tool_response(
        status=overall_status,
        data={
            "store_id": store_id,
            "requested_date": date,
            "snapshot_date_used": snapshot_date,
            "low_stock": low_stock,
            "overstock": overstock,
            "healthy_count": healthy_count,
            "unavailable": unavailable,
            "total_ingredients_checked": len(df),
        },
        evidence=[
            {
                "source": "store_inventory.csv",
                "store_id": store_id,
                "snapshot_date": snapshot_date,
            }
        ],
        warnings=base_warnings + alert_warnings,
        human_review_required=bool(unavailable),
    )
