"""BrewFlow AI — MCP tool tests.

All tests run locally with no external API keys.
Tests use real data from data/raw/ CSV files.

Test data anchor:
  store_id = "SD001"
  date     = "2024-01-15"  (has inventory, forecast, and staff data)
  hour     = 8
"""

from __future__ import annotations

import pytest

from mcp_servers.brewflow_mcp_server import (
    build_and_validate_order,
    calculate_staffing_gap,
    check_inventory_status,
    detect_rush_period,
    get_menu_item_info,
    search_menu_by_preferences,
)
from utils.data_loader import validate_required_data_files

STORE = "SD001"
DATE = "2024-01-15"
HOUR = 8


# ---------------------------------------------------------------------------
# Data file sanity checks
# ---------------------------------------------------------------------------


def test_required_data_files_exist():
    result = validate_required_data_files()
    assert result["status"] == "success", f"Missing CSV files: {result['missing']}"
    assert result["missing"] == []


# ---------------------------------------------------------------------------
# get_menu_item_info
# ---------------------------------------------------------------------------


def test_get_menu_item_info_exact_match():
    r = get_menu_item_info("Caramel Macchiato")
    assert r["status"] == "success"
    assert r["data"]["canonical_name"] == "Caramel Macchiato"
    assert "sizes_available" in r["data"]
    assert len(r["data"]["size_nutrition"]) > 0


def test_get_menu_item_info_mapped_name():
    """Item name from item_name_mapping.csv resolves correctly."""
    r = get_menu_item_info("Cappuccino")
    assert r["status"] == "success"
    assert r["data"]["canonical_name"] == "Cappuccino"


def test_get_menu_item_info_unknown_returns_needs_review():
    r = get_menu_item_info("xyzzy_drink_2099")
    assert r["status"] in ("needs_review", "warning")


def test_get_menu_item_info_response_structure():
    r = get_menu_item_info("Caffe Latte")
    assert "status" in r
    assert "data" in r
    assert "evidence" in r
    assert "warnings" in r


# ---------------------------------------------------------------------------
# search_menu_by_preferences
# ---------------------------------------------------------------------------


def test_search_menu_dairy_free_returns_candidates():
    r = search_menu_by_preferences({"dairy_free": True}, store_id=STORE, date=DATE)
    assert r["status"] in ("success", "warning")
    candidates = r["data"]["candidates"]
    assert len(candidates) > 0
    # All returned items should be vegan (dairy-free proxy)
    for c in candidates:
        assert c["vegan"] is True, f"{c['item']} not marked vegan"


def test_search_menu_no_coffee():
    r = search_menu_by_preferences({"non_coffee": True, "temperature": "hot"})
    assert r["status"] in ("success", "warning")
    candidates = r["data"]["candidates"]
    coffee_terms = ("coffee", "espresso", "latte", "americano", "mocha", "macchiato", "cappuccino")
    for c in candidates:
        assert not any(t in c["item"].lower() for t in coffee_terms), \
            f"Coffee item returned for non-coffee request: {c['item']}"


def test_search_menu_low_calorie():
    r = search_menu_by_preferences({"low_calorie": True})
    assert r["status"] in ("success", "warning")
    candidates = r["data"]["candidates"]
    assert len(candidates) > 0
    # Top candidates should be low-calorie
    top = candidates[0]
    assert top["calories"] <= 150 or "low_calorie" in top["reason_codes"]


def test_search_menu_returns_ranked_structure():
    r = search_menu_by_preferences({"temperature": "cold", "flavor": "caramel"}, store_id=STORE, date=DATE)
    assert r["status"] in ("success", "warning")
    candidates = r["data"]["candidates"]
    if len(candidates) > 1:
        assert candidates[0]["score"] >= candidates[1]["score"]


def test_search_menu_empty_prefs_returns_results():
    """With no hard filters, should still return candidate drinks."""
    r = search_menu_by_preferences({})
    assert r["status"] in ("success", "warning")
    assert len(r["data"]["candidates"]) > 0


# ---------------------------------------------------------------------------
# check_inventory_status
# ---------------------------------------------------------------------------


def test_check_inventory_exact_date():
    r = check_inventory_status(STORE, DATE)
    assert r["status"] in ("success", "warning", "needs_review")
    assert r["data"]["snapshot_date_used"] is not None
    assert isinstance(r["data"]["ingredients"], list)


def test_check_inventory_specific_ingredients():
    r = check_inventory_status(STORE, DATE, ["espresso beans", "oat milk"])
    assert r["status"] in ("success", "warning", "needs_review")
    assert len(r["data"]["ingredients"]) == 2


def test_check_inventory_latest_prior_fallback():
    """A date with no exact snapshot should use latest prior."""
    r = check_inventory_status(STORE, "2024-01-16")  # likely no exact snapshot
    assert r["status"] in ("success", "warning", "needs_review", "error")
    if r["status"] != "error":
        assert r["data"]["snapshot_date_used"] is not None
        assert r["data"]["snapshot_date_used"] <= "2024-01-16"


def test_check_inventory_response_structure():
    r = check_inventory_status(STORE, DATE)
    assert "status" in r
    assert "data" in r
    assert "recommendation_safe" in r["data"]
    assert "availability_flag" in r["data"]
    assert "snapshot_date_used" in r["data"]


# ---------------------------------------------------------------------------
# detect_rush_period
# ---------------------------------------------------------------------------


def test_detect_rush_period_known_date_hour():
    r = detect_rush_period(STORE, DATE, HOUR)
    assert r["status"] in ("success", "warning")
    assert "demand_level" in r["data"]
    assert "rush_risk" in r["data"]
    assert r["data"]["rush_risk"] in ("low", "medium", "high")


def test_detect_rush_period_returns_forecast_orders():
    r = detect_rush_period(STORE, DATE, HOUR)
    assert "forecast_orders" in r["data"]
    assert isinstance(r["data"]["forecast_orders"], int)


def test_detect_rush_period_missing_data_returns_warning():
    r = detect_rush_period(STORE, "1900-01-01", 8)
    assert r["status"] == "warning"
    assert len(r["warnings"]) > 0


def test_detect_rush_period_response_structure():
    r = detect_rush_period(STORE, DATE, HOUR)
    assert "status" in r
    assert "data" in r
    assert "evidence" in r
    assert "warnings" in r


# ---------------------------------------------------------------------------
# calculate_staffing_gap
# ---------------------------------------------------------------------------


def test_calculate_staffing_gap_known_date_hour():
    r = calculate_staffing_gap(STORE, DATE, HOUR)
    assert r["status"] in ("success", "warning")
    assert "staffing_gap" in r["data"]
    assert "risk_level" in r["data"]
    assert r["data"]["risk_level"] in ("low", "medium", "high")


def test_calculate_staffing_gap_fields():
    r = calculate_staffing_gap(STORE, DATE, HOUR)
    d = r["data"]
    assert "required_staff" in d
    assert "scheduled_staff" in d
    assert "staffing_status" in d
    assert isinstance(d["staffing_gap"], int)


def test_calculate_staffing_gap_no_data_returns_warning():
    r = calculate_staffing_gap(STORE, "1900-01-01", 8)
    assert r["status"] == "warning"


# ---------------------------------------------------------------------------
# build_and_validate_order
# ---------------------------------------------------------------------------


def test_build_and_validate_order_normal():
    r = build_and_validate_order("Grande iced caramel macchiato with oat milk", STORE, DATE)
    assert r["status"] in ("success", "warning", "needs_review")
    so = r["data"]["structured_order"]
    assert so["size"] == "Grande"
    assert so["temperature"] == "Iced"
    assert so["milk_type"] == "Oat Milk"


def test_build_and_validate_order_missing_size():
    r = build_and_validate_order("I want a hot caramel macchiato", STORE, DATE)
    assert "size" in r["data"]["missing_fields"]
    assert r["data"]["follow_up_question"] is not None
    assert r["status"] == "needs_review"


def test_build_and_validate_order_allergy_triggers_review():
    r = build_and_validate_order("Grande latte please, I have a nut allergy")
    assert r["human_review_required"] is True
    assert any("allerg" in w.lower() for w in r["warnings"])


def test_build_and_validate_order_prep_notes_individual():
    r = build_and_validate_order("Venti hot latte", STORE, DATE)
    prep_notes_text = " ".join(r["data"].get("prep_notes", []))
    assert "individually" in prep_notes_text.lower()


def test_build_and_validate_order_response_structure():
    r = build_and_validate_order("Tall iced coffee")
    assert "status" in r
    assert "data" in r
    d = r["data"]
    assert "structured_order" in d
    assert "missing_fields" in d
    assert "inventory_warnings" in d
    assert "prep_notes" in d


def test_build_and_validate_order_item_name_mapping():
    """Item from item_name_mapping.csv is resolved to canonical name."""
    r = build_and_validate_order("Grande Cold Brew Coffee")
    so = r["data"]["structured_order"]
    assert so["item"] is not None
    assert so["size"] == "Grande"
