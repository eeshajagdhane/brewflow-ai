"""Staffing gap calculator automation for BrewFlow AI.

Deterministic — no LLM calls.
Reads staff_schedule.csv and calculates the staffing gap for a given
store, date, and hour.

Usage::

    from automations.staffing_gap_calculator.run_staffing_gap_calculator import run_staffing_gap_calculator
    result = run_staffing_gap_calculator("SD001", "2024-01-15", 8)
"""

from __future__ import annotations

import pandas as pd

from utils.data_loader import load_staff_schedule
from utils.workflow_common import make_tool_response


def _shift_covers_hour(shift_start: str, shift_end: str, hour: int) -> bool:
    """Return True if a shift [shift_start, shift_end) covers the given hour."""
    try:
        start_h = int(str(shift_start).split(":")[0])
        end_h = int(str(shift_end).split(":")[0])
        return start_h <= hour < end_h
    except (ValueError, IndexError):
        return False


def run_staffing_gap_calculator(store_id: str, date: str, hour: int) -> dict:
    """Calculate staffing gap for a store at a specific date and hour.

    Args:
        store_id: Store identifier (e.g. "SD001").
        date: Date string "YYYY-MM-DD".
        hour: Integer hour (0–23).

    Returns:
        Tool response with required_staff, scheduled_staff, staffing_gap,
        staffing_status, risk_level, callout_count, expected_orders_per_hour.
    """
    df = load_staff_schedule()

    store_df = df[(df["store_id"] == store_id) & (df["date"] == date)].copy()
    if store_df.empty:
        return make_tool_response(
            status="warning",
            warnings=[f"No staff schedule found for store {store_id} on {date}."],
            data={"store_id": store_id, "date": date, "hour": hour, "scheduled_staff": 0},
        )

    active = store_df[
        store_df.apply(
            lambda r: _shift_covers_hour(r["shift_start"], r["shift_end"], hour),
            axis=1,
        )
    ]

    if active.empty:
        return make_tool_response(
            status="warning",
            warnings=[f"No shifts cover hour {hour:02d}:00 at store {store_id} on {date}."],
            data={"store_id": store_id, "date": date, "hour": hour, "scheduled_staff": 0},
        )

    # Use precomputed columns from the CSV for required_staff and staffing_status
    # (these are per-shift-window values; take from the first active row as reference)
    ref_row = active.iloc[0]
    required_staff = int(ref_row.get("required_staff", 0))
    staffing_gap_csv = int(ref_row.get("staffing_gap", 0))
    staffing_status = str(ref_row.get("staffing_status", ""))
    expected_orders = int(ref_row.get("expected_orders_per_hour", 0))
    shift_start = str(ref_row.get("shift_start", ""))
    shift_end = str(ref_row.get("shift_end", ""))

    # Count unique scheduled employees actually covering this hour
    scheduled_staff = int(active["employee_id"].nunique())

    # Callouts: employees with callout_flag == "Yes" during this window
    callouts = active[active["callout_flag"].astype(str).str.upper() == "YES"]
    callout_count = len(callouts)

    # Effective gap: negative = understaffed, 0 = balanced, positive = overstaffed
    effective_gap = scheduled_staff - required_staff

    if effective_gap < -1:
        risk_level = "high"
    elif effective_gap < 0:
        risk_level = "medium"
    elif effective_gap == 0:
        risk_level = "low"
    else:
        risk_level = "low"

    warnings: list[str] = []
    if callout_count > 0:
        warnings.append(f"{callout_count} callout(s) recorded for shifts covering hour {hour:02d}:00.")
    if effective_gap < 0:
        warnings.append(
            f"Understaffed by {abs(effective_gap)} at hour {hour:02d}:00 "
            f"({scheduled_staff} scheduled, {required_staff} required)."
        )

    return make_tool_response(
        status="warning" if effective_gap < 0 or callout_count > 0 else "success",
        data={
            "store_id": store_id,
            "date": date,
            "hour": hour,
            "shift_start": shift_start,
            "shift_end": shift_end,
            "required_staff": required_staff,
            "scheduled_staff": scheduled_staff,
            "staffing_gap": effective_gap,
            "staffing_gap_csv": staffing_gap_csv,
            "staffing_status": staffing_status,
            "risk_level": risk_level,
            "callout_count": callout_count,
            "expected_orders_per_hour": expected_orders,
        },
        evidence=[{"source": "staff_schedule.csv", "store_id": store_id, "date": date, "hour": hour}],
        warnings=warnings,
    )
