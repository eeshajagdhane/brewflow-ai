"""Menu item name resolution for BrewFlow AI.

All item name resolution goes through item_name_mapping.csv.
Never perform raw direct string comparison against the menu when
a mapping lookup can answer the question instead.
"""

from __future__ import annotations

import re
from typing import Optional

import pandas as pd

from utils.data_loader import load_item_name_mapping, load_menu


def normalize_text(value: str) -> str:
    """Lowercase, strip, collapse whitespace, remove apostrophes."""
    value = str(value).lower().strip()
    value = re.sub(r"[''`\"]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def resolve_item_name(source_item_name: str) -> dict:
    """Resolve an arbitrary item name to its canonical menu name via the mapping table.

    Resolution order:
      1. Exact case-insensitive match in source_item_name column.
      2. Exact case-insensitive match in canonical_menu_item column.
      3. Partial substring match in either column.
      4. No match → needs_review with empty candidates.

    Returns a dict with keys:
      status, canonical_menu_item, confidence, match_type, candidates, warnings.
    """
    mapping = load_item_name_mapping()
    normalized = normalize_text(source_item_name)

    # 1. exact match on source side
    mask_src = mapping["source_item_name"].apply(normalize_text) == normalized
    exact_src = mapping[mask_src]
    if not exact_src.empty:
        row = exact_src.iloc[0]
        warnings: list[str] = []
        if row["confidence"] != "high":
            warnings.append(
                f"Mapping confidence for '{source_item_name}' is '{row['confidence']}': {row.get('notes', '')}"
            )
        return {
            "status": "success",
            "canonical_menu_item": row["canonical_menu_item"],
            "confidence": row["confidence"],
            "match_type": row["match_type"],
            "candidates": [],
            "warnings": warnings,
        }

    # 2. exact match on canonical side
    mask_can = mapping["canonical_menu_item"].apply(normalize_text) == normalized
    exact_can = mapping[mask_can]
    if not exact_can.empty:
        row = exact_can.iloc[0]
        return {
            "status": "success",
            "canonical_menu_item": row["canonical_menu_item"],
            "confidence": row["confidence"],
            "match_type": row["match_type"],
            "candidates": [],
            "warnings": [],
        }

    # 3. partial match (query is a substring of source or canonical)
    partial_mask = mapping["source_item_name"].apply(normalize_text).str.contains(normalized, regex=False) | mapping[
        "canonical_menu_item"
    ].apply(normalize_text).str.contains(normalized, regex=False)
    partial = mapping[partial_mask]

    # Also try: each token in the query appears somewhere
    if partial.empty and " " in normalized:
        tokens = normalized.split()
        token_mask = pd.Series([True] * len(mapping), index=mapping.index)
        for t in tokens:
            token_mask &= (
                mapping["source_item_name"].apply(normalize_text).str.contains(t, regex=False)
                | mapping["canonical_menu_item"].apply(normalize_text).str.contains(t, regex=False)
            )
        partial = mapping[token_mask]

    if not partial.empty:
        candidates = partial[["source_item_name", "canonical_menu_item", "confidence"]].to_dict("records")
        return {
            "status": "warning",
            "canonical_menu_item": None,
            "confidence": "low",
            "match_type": "partial_match",
            "candidates": candidates,
            "warnings": [f"Ambiguous item name '{source_item_name}'. Review candidates and clarify."],
        }

    # 4. no match
    return {
        "status": "needs_review",
        "canonical_menu_item": None,
        "confidence": "none",
        "match_type": "no_match",
        "candidates": [],
        "warnings": [f"No item found matching '{source_item_name}'. Please clarify the item name."],
    }


def get_menu_item(canonical_or_source_name: str) -> dict:
    """Return all menu rows for an item name (may have multiple size rows).

    Resolves the name through the mapping table first, then looks up the menu.

    Returns dict with status, item (list of row dicts), canonical_name, warnings, candidates.
    """
    resolution = resolve_item_name(canonical_or_source_name)

    if resolution["status"] == "needs_review":
        return {
            "status": "needs_review",
            "item": None,
            "canonical_name": None,
            "warnings": resolution["warnings"],
            "candidates": resolution.get("candidates", []),
        }

    canonical = resolution["canonical_menu_item"]
    if canonical is None:
        return {
            "status": "warning",
            "item": None,
            "canonical_name": None,
            "warnings": resolution["warnings"],
            "candidates": resolution.get("candidates", []),
        }

    menu = load_menu()
    rows = menu[menu["Item"].apply(normalize_text) == normalize_text(canonical)]
    if rows.empty:
        # Fallback: direct menu search in case mapping is out of date
        rows = menu[menu["Item"].apply(normalize_text).str.contains(normalize_text(canonical), regex=False)]

    if rows.empty:
        return {
            "status": "needs_review",
            "item": None,
            "canonical_name": canonical,
            "warnings": [f"Canonical name '{canonical}' not found in menu. Data may be out of sync."],
            "candidates": [],
        }

    return {
        "status": "success",
        "item": rows.to_dict("records"),
        "canonical_name": canonical,
        "resolution": resolution,
        "warnings": resolution.get("warnings", []),
        "candidates": [],
    }


def find_menu_candidates(query: str, limit: int = 5) -> list[dict]:
    """Find menu items whose names contain query tokens.

    Returns a list of dicts: {item, category, subcategory, score}.
    Score = number of query tokens found in the item name.
    """
    menu = load_menu()
    normalized = normalize_text(query)
    terms = [t for t in normalized.split() if len(t) > 2]  # skip very short tokens

    seen: dict[str, dict] = {}
    for _, row in menu.iterrows():
        item_lower = normalize_text(row["Item"])
        score = sum(1 for t in terms if t in item_lower)
        if score > 0 and row["Item"] not in seen:
            seen[row["Item"]] = {
                "item": row["Item"],
                "category": row.get("Category", ""),
                "subcategory": row.get("Subcategory", ""),
                "score": score,
            }

    ranked = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:limit]
