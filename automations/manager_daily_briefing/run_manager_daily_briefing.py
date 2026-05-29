"""Manager daily briefing automation for BrewFlow AI.

Deterministic — no LLM calls.
Combines demand_rush_detection, staffing_gap_calculator, inventory_monitoring,
and promotion_margins to produce a structured pre-shift manager readiness report.

The output includes:
  - Readiness summary (overall_status, demand_risk, staffing_gap, inventory_alerts)
  - Demand detail, staffing detail, inventory alerts
  - Active promotions with risk flags
  - Recommended manager actions (prioritized list)
  - barista_guidance dict — consumed by the recommendation workflow step

Usage::

    from automations.manager_daily_briefing.run_manager_daily_briefing import run_manager_daily_briefing
    result = run_manager_daily_briefing("SD001", "2024-01-15", 8)
"""

from __future__ import annotations

import pandas as pd

from automations.demand_rush_detection.run_demand_rush_detection import run_demand_rush_detection
from automations.inventory_monitoring.run_inventory_monitoring import run_inventory_monitoring
from automations.staffing_gap_calculator.run_staffing_gap_calculator import run_staffing_gap_calculator
from utils.data_loader import load_promotion_margins
from utils.workflow_common import make_tool_response, now_iso


def run_manager_daily_briefing(store_id: str, date: str, hour: int) -> dict:
    """Generate a structured pre-shift manager briefing.

    Args:
        store_id: Store identifier (e.g. "SD001").
        date: Date string "YYYY-MM-DD".
        hour: Current hour (0–23) for contextualising demand and staffing.

    Returns:
        Tool response with readiness_summary, demand_detail, staffing_detail,
        inventory alerts, active_promotions, recommended_manager_actions,
        and barista_guidance.
    """
    demand = run_demand_rush_detection(store_id, date, hour)
    staffing = run_staffing_gap_calculator(store_id, date, hour)
    inventory = run_inventory_monitoring(store_id, date)

    # Active promotions for this store on this date
    promos_df = load_promotion_margins()
    active_promos_df = promos_df[
        (promos_df["store_id"] == store_id)
        & (promos_df["start_date"] <= date)
        & (promos_df["end_date"] >= date)
    ]

    active_promotions: list[dict] = []
    promo_warnings: list[str] = []
    for _, p in active_promos_df.iterrows():
        inv_risk = str(p.get("inventory_risk", "")).strip()
        entry = {
            "item": str(p["item_name"]),
            "promo_name": str(p["promo_name"]),
            "promo_type": str(p["promo_type"]),
            "discount_pct": float(p["discount_pct"]),
            "gross_margin_pct": float(p["gross_margin_pct"]),
            "inventory_risk": inv_risk,
            "recommended_action": str(p.get("recommended_action", "")),
        }
        active_promotions.append(entry)
        if inv_risk.lower() == "high":
            promo_warnings.append(f"High inventory-risk promo '{p['promo_name']}' on '{p['item_name']}'.")

    # Extract key signals
    demand_data = demand.get("data", {})
    staffing_data = staffing.get("data", {})
    inventory_data = inventory.get("data", {})

    rush_risk = demand_data.get("rush_risk", "unknown")
    staffing_gap = staffing_data.get("staffing_gap", 0)
    staffing_status = staffing_data.get("staffing_status", "")
    inventory_unavailable: list[dict] = inventory_data.get("unavailable", [])
    inventory_low: list[dict] = inventory_data.get("low_stock", [])
    callout_count = staffing_data.get("callout_count", 0)

    # Build prioritized recommended actions
    recommended_actions: list[str] = []

    if inventory_unavailable:
        names = ", ".join(i["ingredient"] for i in inventory_unavailable)
        recommended_actions.append(
            f"[CRITICAL] Remove unavailable ingredients from service: {names}. "
            "Update baristas before shift begins."
        )

    if staffing_gap < -1 and rush_risk == "high":
        recommended_actions.append(
            f"[CRITICAL] Understaffed by {abs(staffing_gap)} during high-demand period. "
            "Call backup staff or activate contingency plan."
        )
    elif staffing_gap < 0:
        recommended_actions.append(
            f"[WARNING] Staffing gap of {abs(staffing_gap)}. "
            "Consider simplifying menu complexity or pre-staging popular items."
        )

    if callout_count > 0:
        recommended_actions.append(
            f"[WARNING] {callout_count} callout(s) on record. Verify coverage before peak window."
        )

    if rush_risk == "high":
        recommended_actions.append(
            "[ACTION] High rush expected. Ensure espresso station is stocked and ready. "
            "Brief baristas to keep recommendations concise."
        )

    if inventory_low:
        names = ", ".join(i["ingredient"] for i in inventory_low[:5])
        suffix = "..." if len(inventory_low) > 5 else ""
        recommended_actions.append(
            f"[MONITOR] Low stock on {names}{suffix}. Reorder if possible; inform baristas."
        )

    if promo_warnings:
        recommended_actions.append(
            "[REVIEW] Active promotions with high inventory risk detected. "
            "Verify stock levels before endorsing. See promotion detail."
        )

    if not recommended_actions:
        recommended_actions.append(
            "[OK] No critical alerts. Proceed with standard pre-shift checklist."
        )

    # Barista guidance block — consumed by the recommendation workflow step
    barista_guidance = {
        "rush_level": rush_risk,
        "service_mode": "concise" if rush_risk == "high" else "standard",
        "avoid_ingredients": [i["ingredient"] for i in inventory_unavailable],
        "caution_ingredients": [i["ingredient"] for i in inventory_low[:5]],
        "promotion_items": [p["item"] for p in active_promotions],
        "staffing_note": staffing_status,
    }

    # Overall readiness status
    if inventory_unavailable or (staffing_gap < -1 and rush_risk == "high"):
        overall_status = "needs_review"
    elif inventory_low or staffing_gap < 0 or rush_risk == "high":
        overall_status = "warning"
    else:
        overall_status = "success"

    all_warnings = (
        demand.get("warnings", [])
        + staffing.get("warnings", [])
        + inventory.get("warnings", [])
        + promo_warnings
    )

    return make_tool_response(
        status=overall_status,
        data={
            "store_id": store_id,
            "date": date,
            "hour": hour,
            "generated_at": now_iso(),
            "readiness_summary": {
                "overall_status": overall_status,
                "demand_risk": rush_risk,
                "demand_level": demand_data.get("demand_level", ""),
                "staffing_gap": staffing_gap,
                "staffing_status": staffing_status,
                "inventory_unavailable_count": len(inventory_unavailable),
                "inventory_low_count": len(inventory_low),
                "active_promotions_count": len(active_promotions),
                "forecast_orders": demand_data.get("forecast_orders", 0),
            },
            "demand_detail": demand_data,
            "staffing_detail": staffing_data,
            "inventory_low_stock": inventory_low,
            "inventory_unavailable": inventory_unavailable,
            "active_promotions": active_promotions,
            "recommended_manager_actions": recommended_actions,
            "barista_guidance": barista_guidance,
        },
        evidence=[
            {"source": "daily_sales_forecast.csv"},
            {"source": "staff_schedule.csv"},
            {"source": "store_inventory.csv"},
            {"source": "promotion_margins.csv"},
        ],
        warnings=all_warnings,
        human_review_required=overall_status == "needs_review",
    )
