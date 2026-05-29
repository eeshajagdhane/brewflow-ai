"""Data loading utilities for BrewFlow AI.

Loads all CSVs from data/raw/ using repo-relative paths.
All functions return pandas DataFrames.
Do not modify returned DataFrames in place — always copy if you need to mutate.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

REQUIRED_FILES = [
    "starbucks_menu_full.csv",
    "order_history.csv",
    "store_inventory.csv",
    "staff_schedule.csv",
    "daily_sales_forecast.csv",
    "promotion_margins.csv",
    "item_name_mapping.csv",
    "ingredient_mapping.csv",
    "demo_scenarios.csv",
]


def load_menu() -> pd.DataFrame:
    """Load starbucks_menu_full.csv.  Size_oz is float so dtype inference is relaxed."""
    return pd.read_csv(_RAW_DIR / "starbucks_menu_full.csv", dtype={"Size_oz": float})


def load_order_history() -> pd.DataFrame:
    """Load order_history.csv."""
    return pd.read_csv(_RAW_DIR / "order_history.csv")


def load_inventory() -> pd.DataFrame:
    """Load store_inventory.csv."""
    return pd.read_csv(_RAW_DIR / "store_inventory.csv")


def load_staff_schedule() -> pd.DataFrame:
    """Load staff_schedule.csv."""
    return pd.read_csv(_RAW_DIR / "staff_schedule.csv")


def load_sales_forecast() -> pd.DataFrame:
    """Load daily_sales_forecast.csv."""
    return pd.read_csv(_RAW_DIR / "daily_sales_forecast.csv")


def load_promotion_margins() -> pd.DataFrame:
    """Load promotion_margins.csv."""
    return pd.read_csv(_RAW_DIR / "promotion_margins.csv")


def load_item_name_mapping() -> pd.DataFrame:
    """Load item_name_mapping.csv."""
    return pd.read_csv(_RAW_DIR / "item_name_mapping.csv")


def load_ingredient_mapping() -> pd.DataFrame:
    """Load ingredient_mapping.csv."""
    return pd.read_csv(_RAW_DIR / "ingredient_mapping.csv")


def load_demo_scenarios() -> pd.DataFrame:
    """Load demo_scenarios.csv.  keep_default_na=False preserves 'N/A' as string."""
    return pd.read_csv(_RAW_DIR / "demo_scenarios.csv", keep_default_na=False)


def validate_required_data_files() -> dict:
    """Check that all required CSV files exist under data/raw/.

    Returns a dict with status, found list, and missing list.
    """
    found: list[str] = []
    missing: list[str] = []
    for fname in REQUIRED_FILES:
        if (_RAW_DIR / fname).exists():
            found.append(fname)
        else:
            missing.append(fname)
    return {
        "status": "success" if not missing else "error",
        "found": found,
        "missing": missing,
        "data_dir": str(_RAW_DIR),
    }
