"""Demand and rush detection automation for BrewFlow AI.

Deterministic — no LLM calls.
Reads daily_sales_forecast.csv (simulated forecast data) and returns the
demand level, rush risk, and contextual factors for a given store/date/hour.

This automation reads simulated forecast data; it does not produce its own
forecasts. Use "forecast lookup" terminology when labeling results.

Usage::

    from automations.demand_rush_detection.run_demand_rush_detection import run_demand_rush_detection
    result = run_demand_rush_detection("SD001", "2024-01-15", 8)
"""

from __future__ import annotations

import math

import pandas as pd

from utils.data_loader import load_sales_forecast
from utils.workflow_common import make_tool_response

# Map demand_level string → numeric rush risk bucket
_DEMAND_RISK_MAP = {
    "low": "low",
    "moderate": "low",
    "high": "medium",
    "very high": "high",
    "extreme": "high",
}


def run_demand_rush_detection(store_id: str, date: str, hour: int) -> dict:
    """Return demand level and rush risk for a store at a given date/hour.

    Args:
        store_id: Store identifier (e.g. "SD001").
        date: Date string "YYYY-MM-DD".
        hour: Integer hour (0–23).

    Returns:
        Tool response with demand_level, rush_risk, forecast_orders,
        actual_orders (if present), weather_condition, local_event_flag,
        event_type (if present).
    """
    df = load_sales_forecast()

    row_df = df[(df["store_id"] == store_id) & (df["date"] == date) & (df["hour"] == hour)]

    if row_df.empty:
        return make_tool_response(
            status="warning",
            warnings=[f"No forecast data for store {store_id} on {date} at hour {hour:02d}:00."],
            data={"store_id": store_id, "date": date, "hour": hour},
        )

    r = row_df.iloc[0]
    demand_level = str(r.get("demand_level", "Unknown"))
    rush_risk = _DEMAND_RISK_MAP.get(demand_level.lower(), "unknown")
    forecast_orders = int(r.get("forecast_orders", 0))
    weather = str(r.get("weather_condition", "Unknown"))
    local_event_flag = str(r.get("local_event_flag", "No"))

    data: dict = {
        "store_id": store_id,
        "date": date,
        "hour": hour,
        "demand_level": demand_level,
        "rush_risk": rush_risk,
        "forecast_orders": forecast_orders,
        "forecast_drinks": int(r.get("forecast_drinks", 0)),
        "weather_condition": weather,
        "local_event_flag": local_event_flag,
        "season": str(r.get("season", "")),
    }

    actual_orders = r.get("actual_orders")
    if actual_orders is not None and not (isinstance(actual_orders, float) and math.isnan(actual_orders)):
        data["actual_orders"] = int(actual_orders)

    event_type = r.get("event_type")
    if event_type is not None and str(event_type) not in ("", "nan", "NaN"):
        data["event_type"] = str(event_type)

    warnings: list[str] = []
    if rush_risk == "high":
        warnings.append(f"HIGH rush risk at hour {hour:02d}:00 — forecast {forecast_orders} orders.")
    if local_event_flag == "Yes":
        warnings.append(f"Local event: {data.get('event_type', 'type unknown')}.")
    if weather.lower() in ("rain", "heavy rain", "storm"):
        warnings.append(f"Weather may affect foot traffic: {weather}.")

    return make_tool_response(
        status="warning" if rush_risk == "high" else "success",
        data=data,
        evidence=[
            {
                "source": "daily_sales_forecast.csv",
                "store_id": store_id,
                "date": date,
                "hour": hour,
            }
        ],
        warnings=warnings,
    )
