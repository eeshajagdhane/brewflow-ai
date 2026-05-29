"""Inventory matching and availability utilities for BrewFlow AI.

Connects menu ingredient terms to store_inventory.csv entries
via ingredient_mapping.csv.

Snapshot lookup policy:
  1. Exact match: store_id + date.
  2. If unavailable: latest prior inventory snapshot where date <= requested date.
  3. If no prior snapshot exists: return an error.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from utils.data_loader import load_ingredient_mapping, load_inventory

# Canonical status values produced by classify_inventory_status
STATUS_UNAVAILABLE = "unavailable"
STATUS_LOW_STOCK = "low_stock"
STATUS_HEALTHY = "healthy"
STATUS_OVERSTOCK = "overstock"

# stock_status strings that map to each internal status
_UNAVAILABLE_TERMS = ("critical low", "out of stock", "unavailable")
_LOW_TERMS = ("low",)
_OVERSTOCK_TERMS = ("overstocked", "overstock")


def classify_inventory_status(row: pd.Series) -> str:
    """Map a store_inventory row's stock_status field to an internal status string."""
    raw = str(row.get("stock_status", "")).strip().lower()

    for term in _UNAVAILABLE_TERMS:
        if term in raw:
            return STATUS_UNAVAILABLE

    for term in _LOW_TERMS:
        if raw == term or raw.startswith(term + " "):
            return STATUS_LOW_STOCK

    for term in _OVERSTOCK_TERMS:
        if term in raw:
            return STATUS_OVERSTOCK

    # Fallback: compare closing stock to reorder point
    try:
        closing = float(row.get("closing_stock_units", 0))
        reorder = float(row.get("reorder_point", 0))
        if closing <= 0:
            return STATUS_UNAVAILABLE
        if closing <= reorder:
            return STATUS_LOW_STOCK
    except (TypeError, ValueError):
        pass

    return STATUS_HEALTHY


def map_menu_ingredient_to_inventory(menu_ingredient_term: str) -> dict:
    """Translate a menu-side ingredient term to its inventory-side ingredient name.

    Returns dict with inventory_ingredient, mapping_type, required_for_availability,
    substitution_group, not_tracked flag, and warnings.
    """
    mapping = load_ingredient_mapping()
    term_lower = menu_ingredient_term.strip().lower()

    exact = mapping[mapping["menu_ingredient_term"].str.lower() == term_lower]
    if not exact.empty:
        row = exact.iloc[0]
        not_tracked = str(row["inventory_ingredient"]).strip().lower() == "not_tracked"
        return {
            "status": "success",
            "inventory_ingredient": row["inventory_ingredient"],
            "mapping_type": row["mapping_type"],
            "required_for_availability": str(row["required_for_availability"]).strip().lower() == "yes",
            "substitution_group": row.get("substitution_group", None),
            "not_tracked": not_tracked,
            "warnings": [] if not not_tracked else [f"'{menu_ingredient_term}' is not tracked in inventory."],
        }

    # Partial match
    partial = mapping[mapping["menu_ingredient_term"].str.lower().str.contains(term_lower, regex=False)]
    if not partial.empty:
        row = partial.iloc[0]
        not_tracked = str(row["inventory_ingredient"]).strip().lower() == "not_tracked"
        return {
            "status": "warning",
            "inventory_ingredient": row["inventory_ingredient"],
            "mapping_type": "partial_match",
            "required_for_availability": str(row["required_for_availability"]).strip().lower() == "yes",
            "substitution_group": row.get("substitution_group", None),
            "not_tracked": not_tracked,
            "warnings": [f"Partial match used for '{menu_ingredient_term}' → '{row['inventory_ingredient']}'."],
        }

    return {
        "status": "not_found",
        "inventory_ingredient": None,
        "mapping_type": "no_match",
        "required_for_availability": False,
        "substitution_group": None,
        "not_tracked": True,
        "warnings": [f"No ingredient mapping found for '{menu_ingredient_term}'. Treated as not_tracked."],
    }


def get_inventory_snapshot(store_id: str, date: str) -> dict:
    """Return the inventory snapshot for store_id on the given date.

    Implements the latest-prior fallback: if no exact match for date, returns
    the most recent snapshot where inventory date <= requested date.

    Returns dict with status, data (DataFrame), snapshot_date, warnings.
    """
    inv = load_inventory()

    exact = inv[(inv["store_id"] == store_id) & (inv["date"] == date)]
    if not exact.empty:
        return {
            "status": "success",
            "data": exact.copy(),
            "snapshot_date": date,
            "warnings": [],
        }

    # Latest prior snapshot
    store_inv = inv[inv["store_id"] == store_id].copy()
    store_inv = store_inv[store_inv["date"] <= date]
    if store_inv.empty:
        return {
            "status": "error",
            "data": pd.DataFrame(),
            "snapshot_date": None,
            "message": f"No inventory data found for store {store_id} on or before {date}.",
        }

    latest_date = store_inv["date"].max()
    snapshot = store_inv[store_inv["date"] == latest_date].copy()
    return {
        "status": "success",
        "data": snapshot,
        "snapshot_date": latest_date,
        "warnings": [f"No inventory for {date}; using latest prior snapshot from {latest_date}."],
    }


def check_ingredients_availability(
    store_id: str,
    date: str,
    ingredients: Optional[list[str]] = None,
) -> dict:
    """Check availability of ingredients for a store on a given date.

    Args:
        store_id: Store identifier.
        date: Target date string YYYY-MM-DD.
        ingredients: List of menu-side ingredient terms to check.
                     If None, checks all ingredients in the snapshot.

    Returns structured dict with per-ingredient availability results.
    """
    snapshot_result = get_inventory_snapshot(store_id, date)
    if snapshot_result["status"] == "error":
        return {
            "status": "error",
            "snapshot_date_used": None,
            "ingredients": [],
            "recommendation_safe": False,
            "availability_flag": False,
            "warnings": [snapshot_result.get("message", "Inventory data unavailable.")],
            "errors": [snapshot_result.get("message", "")],
        }

    df: pd.DataFrame = snapshot_result["data"]
    snapshot_date = snapshot_result["snapshot_date"]
    base_warnings = snapshot_result.get("warnings", [])

    results: list[dict] = []
    overall_available = True
    overall_recommendation_safe = True

    if ingredients:
        for ing_term in ingredients:
            mapping_result = map_menu_ingredient_to_inventory(ing_term)
            inv_name = mapping_result.get("inventory_ingredient")
            not_tracked = mapping_result.get("not_tracked", False)
            required = mapping_result.get("required_for_availability", False)

            if not_tracked or inv_name is None:
                results.append(
                    {
                        "menu_ingredient": ing_term,
                        "inventory_ingredient": inv_name,
                        "status": "not_tracked",
                        "stock_status": "not_tracked",
                        "closing_stock_units": None,
                        "reorder_point": None,
                        "recommendation_safe": True,
                        "availability_flag": True,
                        "warnings": mapping_result.get("warnings", []),
                    }
                )
                continue

            # Find in snapshot (case-insensitive)
            inv_rows = df[df["ingredient"].str.lower() == inv_name.strip().lower()]
            if inv_rows.empty:
                # Ingredient not in snapshot — treat as not tracked
                results.append(
                    {
                        "menu_ingredient": ing_term,
                        "inventory_ingredient": inv_name,
                        "status": "not_tracked",
                        "stock_status": "not_in_snapshot",
                        "closing_stock_units": None,
                        "reorder_point": None,
                        "recommendation_safe": True,
                        "availability_flag": True,
                        "warnings": [f"'{inv_name}' not found in inventory snapshot for {snapshot_date}."],
                    }
                )
                continue

            inv_row = inv_rows.iloc[0]
            item_status = classify_inventory_status(inv_row)
            available = item_status != STATUS_UNAVAILABLE
            rec_safe = item_status == STATUS_HEALTHY or item_status == STATUS_OVERSTOCK

            if required and not available:
                overall_available = False
            if not rec_safe:
                overall_recommendation_safe = False

            results.append(
                {
                    "menu_ingredient": ing_term,
                    "inventory_ingredient": inv_name,
                    "status": item_status,
                    "stock_status": str(inv_row.get("stock_status", "")),
                    "closing_stock_units": float(inv_row.get("closing_stock_units", 0)),
                    "reorder_point": float(inv_row.get("reorder_point", 0)),
                    "recommendation_safe": rec_safe,
                    "availability_flag": available,
                    "warnings": [] if available else [f"'{inv_name}' is {item_status}."],
                }
            )
    else:
        # Check all ingredients in the snapshot
        for _, row in df.iterrows():
            item_status = classify_inventory_status(row)
            available = item_status != STATUS_UNAVAILABLE
            rec_safe = item_status in (STATUS_HEALTHY, STATUS_OVERSTOCK)
            if not available:
                overall_available = False
            if not rec_safe:
                overall_recommendation_safe = False
            results.append(
                {
                    "menu_ingredient": row["ingredient"],
                    "inventory_ingredient": row["ingredient"],
                    "status": item_status,
                    "stock_status": str(row.get("stock_status", "")),
                    "closing_stock_units": float(row.get("closing_stock_units", 0)),
                    "reorder_point": float(row.get("reorder_point", 0)),
                    "recommendation_safe": rec_safe,
                    "availability_flag": available,
                    "warnings": [],
                }
            )

    warnings = base_warnings + [w for r in results for w in r.get("warnings", [])]
    overall_status = "success"
    if not overall_available:
        overall_status = "needs_review"
    elif not overall_recommendation_safe:
        overall_status = "warning"

    return {
        "status": overall_status,
        "store_id": store_id,
        "requested_date": date,
        "snapshot_date_used": snapshot_date,
        "ingredients": results,
        "recommendation_safe": overall_recommendation_safe,
        "availability_flag": overall_available,
        "warnings": warnings,
    }
