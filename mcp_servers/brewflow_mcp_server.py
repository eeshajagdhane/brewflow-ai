"""BrewFlow AI MCP-style tools.

These functions are implemented as plain callable Python functions with
JSON-serializable inputs and outputs.  They can be registered with the MCP
framework when needed, but can also be imported and called directly by the
orchestrator and tests with no MCP runtime required.

All functions follow the standard BrewFlow tool response envelope:
  {status, data, evidence, warnings, errors, next_actions, human_review_required}

Do NOT call these functions with external APIs.  They are fully local.

Available tools:
  1. get_menu_item_info(item_name)
  2. search_menu_by_preferences(preferences, store_id, date, hour)
  3. check_inventory_status(store_id, date, ingredients)
  4. detect_rush_period(store_id, date, hour)
  5. calculate_staffing_gap(store_id, date, hour)
  6. build_and_validate_order(raw_order, store_id, date)
"""

from __future__ import annotations

import re
from typing import Optional

import pandas as pd

from automations.demand_rush_detection.run_demand_rush_detection import run_demand_rush_detection
from automations.staffing_gap_calculator.run_staffing_gap_calculator import run_staffing_gap_calculator
from utils.data_loader import load_ingredient_mapping, load_item_name_mapping, load_menu, load_order_history, load_promotion_margins
from utils.inventory_matching import check_ingredients_availability, get_inventory_snapshot
from utils.menu_matching import find_menu_candidates, get_menu_item, normalize_text, resolve_item_name
from utils.workflow_common import make_tool_response

# ---------------------------------------------------------------------------
# 1. get_menu_item_info
# ---------------------------------------------------------------------------


def get_menu_item_info(item_name: str) -> dict:
    """Return full menu item information for a given item name.

    Resolves the name through item_name_mapping.csv first.
    Returns all size variants, nutrition, dietary flags, ingredients,
    and customization notes.

    If the item name is ambiguous, returns status="warning" with candidates.
    If no item is found, returns status="needs_review" with closest menu candidates.
    """
    result = get_menu_item(item_name)

    if result["status"] == "needs_review":
        # Try a broader menu search to surface candidates
        candidates = find_menu_candidates(item_name, limit=5)
        return make_tool_response(
            status="needs_review",
            data={"item_name": item_name, "candidates": candidates},
            warnings=result.get("warnings", []),
            next_actions=["clarify_item_name"],
            human_review_required=True,
        )

    if result["status"] == "warning":
        return make_tool_response(
            status="warning",
            data={"item_name": item_name, "candidates": result.get("candidates", [])},
            warnings=result.get("warnings", []),
            next_actions=["clarify_item_name"],
        )

    items = result["item"]
    canonical = result["canonical_name"]

    # Build sizes/nutrition summary
    sizes = []
    for row in items:
        sizes.append(
            {
                "size": row.get("Size", ""),
                "size_oz": row.get("Size_oz", None),
                "calories": row.get("Calories", None),
                "fat_g": row.get("Fat_g", None),
                "carbs_g": row.get("Carbs_g", None),
                "protein_g": row.get("Protein_g", None),
                "caffeine_mg": row.get("Caffeine_mg", None),
                "sodium_mg": row.get("Sodium_mg", None),
            }
        )

    # Use the first row for item-level fields
    ref = items[0]

    return make_tool_response(
        status="success",
        data={
            "canonical_name": canonical,
            "category": ref.get("Category", ""),
            "subcategory": ref.get("Subcategory", ""),
            "seasonal": str(ref.get("Seasonal", "No")),
            "key_ingredients": str(ref.get("Key_Ingredients", "")),
            "vegan": str(ref.get("Vegan", "No")) == "Yes",
            "gluten_free": str(ref.get("Gluten_Free", "No")) == "Yes",
            "notes": str(ref.get("Notes", "")),
            "sizes_available": [s["size"] for s in sizes if s["size"]],
            "size_nutrition": sizes,
            "resolution": result.get("resolution", {}),
        },
        evidence=[
            {"source": "starbucks_menu_full.csv", "item": canonical},
            {"source": "item_name_mapping.csv"},
        ],
        warnings=result.get("warnings", []),
    )


# ---------------------------------------------------------------------------
# 2. search_menu_by_preferences
# ---------------------------------------------------------------------------


_CAFFEINE_HIGH_TERMS = {"high", "medium", "yes", "caffeinated", "regular", "true", "med"}
_CAFFEINE_LOW_TERMS = {"low", "none", "no", "decaf", "decaffeinated", "caffeine-free", "caffeine free", "false"}
_DAIRY_FREE_TERMS = {"dairy-free", "dairy free", "non-dairy", "non dairy", "plant-based",
                     "plant based", "vegan", "no dairy", "lactose-free", "lactose free"}
_NON_COFFEE_TERMS = {"non-coffee", "non coffee", "no coffee", "no-coffee", "without coffee",
                     "tea", "refresher", "non_coffee"}
_SWEETNESS_TERMS = {"sweet", "very sweet", "extra sweet", "sugary"}


def _normalize_preferences(prefs: dict) -> dict:
    """Translate loose preference keys to the canonical keys this tool consumes.

    Accepts aliases without overriding explicit canonical keys.
      caffeine: "high"/"medium"/"low"/"none"/True/False → canonical bool or None
      milk_preference: "dairy-free"/"non-dairy"/...     → dairy_free=True
      coffee_preference: "non-coffee"/"tea"/...         → non_coffee=True
      sweetness: "sweet"                                → flavor="sweet" (only if flavor unset)
    """
    if "caffeine" in prefs:
        val = prefs["caffeine"]
        if isinstance(val, str):
            v = val.lower().strip()
            if v in _CAFFEINE_HIGH_TERMS:
                prefs["caffeine"] = True
            elif v in _CAFFEINE_LOW_TERMS:
                prefs["caffeine"] = False
            else:
                prefs["caffeine"] = None

    if "milk_preference" in prefs and not prefs.get("dairy_free"):
        v = str(prefs["milk_preference"]).lower().strip()
        if v in _DAIRY_FREE_TERMS:
            prefs["dairy_free"] = True

    if "coffee_preference" in prefs and not prefs.get("non_coffee"):
        v = str(prefs["coffee_preference"]).lower().strip()
        if v in _NON_COFFEE_TERMS:
            prefs["non_coffee"] = True

    if "sweetness" in prefs and not prefs.get("flavor"):
        v = str(prefs["sweetness"]).lower().strip()
        if v in _SWEETNESS_TERMS:
            prefs["flavor"] = "sweet"

    return prefs


def search_menu_by_preferences(
    preferences: dict,
    store_id: Optional[str] = None,
    date: Optional[str] = None,
    hour: Optional[int] = None,
) -> dict:
    """Return ranked menu candidates matching customer preferences.

    Preferences dict may include:
      temperature: "hot" | "cold" | "iced" | "any"
      dairy_free: bool
      vegan: bool
      gluten_free: bool
      caffeine: bool (True = wants caffeine, False = wants no/low caffeine)
      non_coffee: bool
      low_calorie: bool  (prefer items <= 150 kcal per size)
      flavor: str  (e.g. "sweet", "fruity", "chocolate", "caramel", "vanilla")
      keywords: list[str]
      food: bool  (True = include food, default False)

    If store_id + date are provided, down-ranks items with low-stock ingredients.
    Uses order_history popularity as a tiebreaker.
    Uses promotion_margins as an optional scoring boost.

    Returns ranked list with score and reason_codes per candidate.
    Does NOT produce natural-language recommendations; that is the skill's job.
    """
    menu = load_menu()
    warnings: list[str] = []

    # Normalize loose preference keys so the tool accepts both canonical and
    # natural-form keys (milk_preference, coffee_preference, sweetness, etc.).
    preferences = _normalize_preferences(dict(preferences))

    temp_pref = str(preferences.get("temperature", "any")).lower()
    dairy_free = bool(preferences.get("dairy_free", False))
    vegan = bool(preferences.get("vegan", False))
    gluten_free = bool(preferences.get("gluten_free", False))
    wants_caffeine = preferences.get("caffeine", None)  # None = no preference; True/False = explicit
    non_coffee = bool(preferences.get("non_coffee", False))
    low_calorie = bool(preferences.get("low_calorie", False))
    flavor_pref = str(preferences.get("flavor", "")).lower().strip()
    keywords = [k.lower() for k in preferences.get("keywords", [])]
    include_food = bool(preferences.get("food", False))

    # Food categories to exclude unless explicitly requested
    food_categories = {"Bakery", "Breakfast", "Lunch", "Snacks & Sweets"}
    drink_categories = {
        "Hot Coffee", "Cold Coffee", "Cold Drinks", "Frappuccino",
        "Iced Tea", "Hot Tea", "Hot Drinks", "Bottled Beverages",
        "Seasonal - Holiday", "Seasonal - Spring", "Seasonal - Fall",
        "Seasonal - Winter/Spring",
    }

    # Deduplicate on item name (take first row per item for scoring)
    unique_items = menu.drop_duplicates(subset=["Item"]).copy()

    scored: list[dict] = []

    for _, row in unique_items.iterrows():
        category = str(row.get("Category", ""))
        item_name = str(row.get("Item", ""))
        item_lower = item_name.lower()

        # Skip food unless explicitly requested
        if category in food_categories and not include_food:
            continue

        score = 0.0
        reason_codes: list[str] = []
        disqualified = False

        # Temperature filter
        if temp_pref in ("hot",):
            if category not in ("Hot Coffee", "Hot Tea", "Hot Drinks"):
                disqualified = True
        elif temp_pref in ("cold", "iced"):
            if category not in ("Cold Coffee", "Cold Drinks", "Iced Tea", "Frappuccino", "Bottled Beverages"):
                disqualified = True

        # Non-coffee filter
        if non_coffee:
            coffee_terms = ("coffee", "espresso", "latte", "americano", "mocha", "macchiato", "cappuccino", "flat white")
            if any(t in item_lower for t in coffee_terms):
                disqualified = True

        # Vegan hard filter
        if vegan and str(row.get("Vegan", "No")) != "Yes":
            disqualified = True

        # Gluten-free hard filter
        if gluten_free and str(row.get("Gluten_Free", "No")) != "Yes":
            disqualified = True

        # Dairy-free approximation (vegan ≈ dairy-free for drinks; note in warnings)
        if dairy_free and str(row.get("Vegan", "No")) != "Yes":
            # Only a heuristic — flag in warnings
            warnings.append(
                "Dairy-free preference applied as 'Vegan=Yes' heuristic. "
                "Verify specific milk options with barista."
            ) if "Dairy-free heuristic" not in " ".join(warnings) else None
            disqualified = True

        if disqualified:
            continue

        # Positive scoring
        # Caffeine preference
        try:
            caffeine_mg = float(row.get("Caffeine_mg", 0) or 0)
        except (ValueError, TypeError):
            caffeine_mg = 0.0

        if wants_caffeine is True and caffeine_mg > 0:
            score += 1.0
            reason_codes.append("has_caffeine")
        elif wants_caffeine is False and caffeine_mg == 0:
            score += 1.0
            reason_codes.append("caffeine_free")
        elif wants_caffeine is None:
            score += 0.3  # neutral baseline

        # Low calorie preference
        try:
            calories = float(row.get("Calories", 0) or 0)
        except (ValueError, TypeError):
            calories = 0.0

        if low_calorie and calories <= 150:
            score += 1.5
            reason_codes.append("low_calorie")
        elif low_calorie and calories > 300:
            score -= 0.5

        # Flavor keyword match
        if flavor_pref:
            key_ingredients = str(row.get("Key_Ingredients", "")).lower()
            notes = str(row.get("Notes", "")).lower()
            if flavor_pref in item_lower or flavor_pref in key_ingredients or flavor_pref in notes:
                score += 2.0
                reason_codes.append(f"flavor_match:{flavor_pref}")

        # Extra keyword matches
        for kw in keywords:
            if kw in item_lower:
                score += 1.0
                reason_codes.append(f"keyword:{kw}")

        # Base category score (prefer drink categories)
        if category in drink_categories:
            score += 0.5

        if score > 0 or not (dairy_free or vegan or gluten_free or non_coffee):
            scored.append(
                {
                    "item": item_name,
                    "category": category,
                    "subcategory": str(row.get("Subcategory", "")),
                    "score": score,
                    "reason_codes": reason_codes,
                    "vegan": str(row.get("Vegan", "No")) == "Yes",
                    "gluten_free": str(row.get("Gluten_Free", "No")) == "Yes",
                    "calories": calories,
                    "caffeine_mg": caffeine_mg,
                }
            )

    if not scored:
        return make_tool_response(
            status="warning",
            data={"candidates": [], "preference_summary": preferences},
            warnings=["No items matched the given preferences. Try relaxing filters."],
            next_actions=["relax_preferences"],
        )

    # Popularity boost from order history
    try:
        history = load_order_history()
        popularity = history.groupby("item_name")["quantity"].sum().to_dict()
        max_pop = max(popularity.values()) if popularity else 1
        for c in scored:
            pop = popularity.get(c["item"], 0)
            c["score"] += (pop / max_pop) * 0.5
            if pop > 0:
                c["reason_codes"].append("popular")
    except Exception:
        warnings.append("Order history unavailable; popularity scoring skipped.")

    # Promotion boost (optional scoring factor, not deterministic)
    if store_id and date:
        try:
            promos = load_promotion_margins()
            active = promos[
                (promos["store_id"] == store_id)
                & (promos["start_date"] <= date)
                & (promos["end_date"] >= date)
            ]
            promo_items = set(active["item_name"].str.lower().tolist())
            for c in scored:
                if c["item"].lower() in promo_items:
                    c["score"] += 0.3
                    c["reason_codes"].append("active_promotion")
        except Exception:
            warnings.append("Promotion data unavailable; promotion scoring skipped.")

    # Inventory down-rank (if store+date provided)
    if store_id and date:
        try:
            snap_result = get_inventory_snapshot(store_id, date)
            if snap_result["status"] == "success":
                snap_df = snap_result["data"]
                low_or_unavail = snap_df[snap_df["stock_status"].isin(["Low", "Critical Low"])]
                problem_ingredients = set(low_or_unavail["ingredient"].str.lower().tolist())
                for c in scored:
                    menu_row = menu[menu["Item"] == c["item"]]
                    if not menu_row.empty:
                        key_ing = str(menu_row.iloc[0].get("Key_Ingredients", "")).lower()
                        if any(p in key_ing for p in problem_ingredients):
                            c["score"] -= 1.5
                            c["reason_codes"].append("ingredient_low_stock")
        except Exception:
            warnings.append("Inventory check unavailable; low-stock down-ranking skipped.")

    # Sort and deduplicate warnings
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = scored[:8]
    warnings = list(dict.fromkeys(warnings))  # deduplicate while preserving order

    return make_tool_response(
        status="success",
        data={
            "candidates": top_candidates,
            "total_matched": len(scored),
            "preference_summary": {k: v for k, v in preferences.items() if v is not None and v != [] and v != ""},
            "store_id": store_id,
            "date": date,
            "hour": hour,
        },
        evidence=[
            {"source": "starbucks_menu_full.csv"},
            {"source": "item_name_mapping.csv"},
            {"source": "order_history.csv"},
        ],
        warnings=warnings,
        next_actions=["present_candidates_to_customer", "check_inventory_for_top_candidate"],
    )


# ---------------------------------------------------------------------------
# 3. check_inventory_status
# ---------------------------------------------------------------------------


def check_inventory_status(
    store_id: str,
    date: str,
    ingredients: Optional[list[str]] = None,
) -> dict:
    """Check inventory availability for a store on a given date.

    Uses the latest-prior snapshot fallback if no exact date match exists.
    Returns per-ingredient statuses, stock levels, and overall flags.

    If ingredients is None, checks all ingredients in the snapshot.
    """
    result = check_ingredients_availability(store_id, date, ingredients)

    # Translate to standard tool response
    if result["status"] == "error":
        return make_tool_response(
            status="error",
            errors=result.get("warnings", ["Inventory data unavailable."]),
            data={
                "store_id": store_id,
                "requested_date": date,
                "snapshot_date_used": None,
                "ingredients": [],
                "recommendation_safe": False,
                "availability_flag": False,
            },
        )

    return make_tool_response(
        status=result["status"],
        data={
            "store_id": store_id,
            "requested_date": date,
            "snapshot_date_used": result.get("snapshot_date_used"),
            "ingredients": result.get("ingredients", []),
            "recommendation_safe": result.get("recommendation_safe", True),
            "availability_flag": result.get("availability_flag", True),
        },
        evidence=[
            {
                "source": "store_inventory.csv",
                "store_id": store_id,
                "snapshot_date": result.get("snapshot_date_used"),
            },
            {"source": "ingredient_mapping.csv"},
        ],
        warnings=result.get("warnings", []),
        human_review_required=result["status"] == "needs_review",
    )


# ---------------------------------------------------------------------------
# 4. detect_rush_period
# ---------------------------------------------------------------------------


def detect_rush_period(store_id: str, date: str, hour: int) -> dict:
    """Return demand level and rush risk for a store at a given date/hour.

    Wrapper around run_demand_rush_detection that conforms to MCP tool conventions.
    """
    return run_demand_rush_detection(store_id, date, hour)


# ---------------------------------------------------------------------------
# 5. calculate_staffing_gap
# ---------------------------------------------------------------------------


def calculate_staffing_gap(store_id: str, date: str, hour: int) -> dict:
    """Return staffing gap and risk level for a store at a given date/hour.

    Wrapper around run_staffing_gap_calculator that conforms to MCP tool conventions.
    """
    return run_staffing_gap_calculator(store_id, date, hour)


# ---------------------------------------------------------------------------
# 6. build_and_validate_order
# ---------------------------------------------------------------------------

# Regex patterns for common order tokens
_SIZE_PATTERN = re.compile(
    r"\b(short|tall|grande|venti|trenta|small|medium|large|extra large|xl)\b", re.IGNORECASE
)
_TEMP_PATTERN = re.compile(
    r"\b(hot|iced|cold|warm|frozen|blended)\b", re.IGNORECASE
)
_MILK_PATTERN = re.compile(
    r"\b(whole milk|2% milk|nonfat milk|skim milk|oat milk|almond milk|soy milk|coconut milk|"
    r"oatmilk|almond|soy|coconut|nonfat|skim|whole|2%|half.?and.?half)\b",
    re.IGNORECASE,
)
_QTY_PATTERN = re.compile(r"\b(one|two|three|four|1|2|3|4)\b(?:\s+of)?\b", re.IGNORECASE)
_ALLERGY_PATTERN = re.compile(
    r"\b(allerg\w*|intoleran\w*|anaphyla\w*|epi.?pen|nut.?allerg\w*|dairy.?allerg\w*|"
    r"gluten.?intoleran\w*|lactose.?intoleran\w*|celiac)\b",
    re.IGNORECASE,
)

_SIZE_NORMALIZE = {
    "small": "Tall",
    "medium": "Grande",
    "large": "Venti",
    "extra large": "Venti",
    "xl": "Venti",
    "short": "Short",
    "tall": "Tall",
    "grande": "Grande",
    "venti": "Venti",
    "trenta": "Trenta",
}

_MILK_NORMALIZE = {
    "whole milk": "Whole Milk",
    "whole": "Whole Milk",
    "2% milk": "2% Milk",
    "2%": "2% Milk",
    "nonfat milk": "Nonfat Milk",
    "skim milk": "Nonfat Milk",
    "nonfat": "Nonfat Milk",
    "skim": "Nonfat Milk",
    "oat milk": "Oat Milk",
    "oatmilk": "Oat Milk",
    "almond milk": "Almond Milk",
    "almond": "Almond Milk",
    "soy milk": "Soy Milk",
    "soy": "Soy Milk",
    "coconut milk": "Coconut Milk",
    "coconut": "Coconut Milk",
    "half and half": "Half & Half",
    "half-and-half": "Half & Half",
}

_QTY_NORMALIZE = {"one": 1, "two": 2, "three": 3, "four": 4, "1": 1, "2": 2, "3": 3, "4": 4}

_CUSTOMIZATION_TERMS = (
    "extra shot", "extra shots", "no whip", "light ice", "no ice", "extra ice",
    "sugar free", "less sugar", "no syrup", "double blended", "extra foam",
    "no foam", "light roast", "bold", "decaf", "half-caf",
)
_SYRUP_TERMS = (
    "vanilla", "caramel", "hazelnut", "cinnamon", "toffee nut", "brown sugar",
    "lavender", "raspberry", "classic syrup", "mocha sauce", "white mocha",
    "pumpkin spice", "peppermint",
)
_TOPPING_TERMS = (
    "whipped cream", "whip", "cinnamon powder", "nutmeg", "caramel drizzle",
    "mocha drizzle", "cold foam", "sweet cream", "strawberry puree",
)


def build_and_validate_order(
    raw_order: str,
    store_id: Optional[str] = None,
    date: Optional[str] = None,
) -> dict:
    """Parse a natural-language order into a structured validated order.

    Uses deterministic regex patterns for size, temperature, milk, quantity,
    syrups, toppings, and customizations.  Item name is resolved via the
    menu matching utilities.

    Returns structured_order, missing_fields, inventory_warnings, prep_notes,
    and follow_up_question if clarification is needed.

    If allergy or medical language is detected, sets human_review_required=True.
    """
    text = raw_order.strip()
    text_lower = text.lower()
    warnings: list[str] = []
    missing_fields: list[str] = []
    prep_notes: list[str] = []

    # Allergy/medical check — flag immediately before any other processing
    allergy_match = _ALLERGY_PATTERN.search(text)
    if allergy_match:
        warnings.append(
            "Allergy or medical language detected. "
            "Do NOT make guarantees. Direct the customer to the official Starbucks allergen guide "
            "and flag this order for human review."
        )

    # Size
    size_match = _SIZE_PATTERN.search(text)
    size_raw = size_match.group(0).lower() if size_match else None
    size = _SIZE_NORMALIZE.get(size_raw) if size_raw else None

    # Temperature
    temp_match = _TEMP_PATTERN.search(text)
    temperature = temp_match.group(0).capitalize() if temp_match else None

    # Milk
    milk_match = _MILK_PATTERN.search(text)
    milk_raw = milk_match.group(0).lower() if milk_match else None
    milk_type = _MILK_NORMALIZE.get(milk_raw) if milk_raw else None

    # Quantity
    qty_match = _QTY_PATTERN.search(text)
    qty_raw = qty_match.group(0).lower() if qty_match else None
    quantity = _QTY_NORMALIZE.get(qty_raw, 1)

    # Syrups (may be multiple)
    syrups = [s for s in _SYRUP_TERMS if s in text_lower]

    # Toppings
    toppings = [t for t in _TOPPING_TERMS if t in text_lower]

    # Customizations
    customizations = [c for c in _CUSTOMIZATION_TERMS if c in text_lower]

    # Item name resolution — strip already-extracted structured tokens from the text
    # so the remaining text describes the item itself, not modifiers or filler.
    # NOTE: temperature is NOT stripped because it disambiguates menu items
    # (e.g. "Iced Matcha Tea Latte" vs "Matcha Tea Latte").
    cleaned = text_lower
    strip_tokens: list[str] = []
    if size_raw:
        strip_tokens.append(size_raw)
    if milk_raw:
        strip_tokens.append(milk_raw)
    if qty_raw:
        strip_tokens.append(qty_raw)
    # Remove already-captured modifier terms so they cannot mislead the menu search
    # (e.g. "vanilla" should not cause "Vanilla Biscotti" to outscore "Iced Matcha").
    strip_tokens.extend(syrups)
    strip_tokens.extend(toppings)
    strip_tokens.extend(customizations)
    for token in strip_tokens:
        if token:
            cleaned = cleaned.replace(token, " ")
    # Strip punctuation
    cleaned = re.sub(r"[,.;:!?()\-]", " ", cleaned)
    # Strip polite filler phrases (multi-word — done as literal substring)
    for filler in ("please", "can i get", "can i have", "i would like", "i'd like",
                   "i want", "give me", "could i get"):
        cleaned = cleaned.replace(filler, " ")
    # Strip connector words (whole-word matches only)
    for word in ("with", "and", "or", "the", "of", "for", "to", "a", "an", "one"):
        cleaned = re.sub(rf"\b{word}\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Try to resolve item name
    item_resolution = resolve_item_name(cleaned) if cleaned else {"status": "needs_review", "canonical_menu_item": None}
    resolved_item = item_resolution.get("canonical_menu_item")

    # Fallback 1: try the full raw text
    if resolved_item is None:
        fallback = resolve_item_name(raw_order)
        if fallback.get("canonical_menu_item"):
            item_resolution = fallback
            resolved_item = fallback["canonical_menu_item"]

    # Fallback 2: use menu candidate search on the cleaned text, then raw text
    if resolved_item is None:
        search_text = cleaned if cleaned else raw_order
        candidates_raw = find_menu_candidates(search_text, limit=3)
        if not candidates_raw:
            candidates_raw = find_menu_candidates(raw_order, limit=3)
        if candidates_raw:
            best = candidates_raw[0]
            if best["score"] >= 1:
                # High enough confidence to auto-resolve
                resolved_item = best["item"]
                item_resolution = {
                    "status": "success",
                    "canonical_menu_item": resolved_item,
                    "confidence": "medium",
                    "match_type": "menu_search_fallback",
                    "candidates": candidates_raw,
                    "warnings": [f"Item resolved via menu search fallback: '{resolved_item}'."],
                }
            else:
                item_resolution = {
                    "status": "warning",
                    "canonical_menu_item": None,
                    "confidence": "low",
                    "match_type": "no_match",
                    "candidates": candidates_raw,
                    "warnings": [f"Could not confidently identify item from '{search_text}'."],
                }

    # Inventory check (if we have a resolved item and store/date)
    inventory_warnings: list[str] = []
    if resolved_item and store_id and date:
        menu_info = get_menu_item_info(resolved_item)
        if menu_info["status"] == "success":
            key_ing = str(menu_info["data"].get("key_ingredients", ""))
            if key_ing:
                ing_terms = [i.strip() for i in key_ing.split(",") if i.strip()]
                inv_result = check_inventory_status(store_id, date, ing_terms)
                for ing in inv_result.get("data", {}).get("ingredients", []):
                    if not ing["availability_flag"]:
                        inventory_warnings.append(
                            f"'{ing['inventory_ingredient']}' is {ing['status']} — item may not be available."
                        )
                    elif not ing["recommendation_safe"]:
                        inventory_warnings.append(
                            f"'{ing['inventory_ingredient']}' is low stock — substitution may be needed."
                        )

    # Required field checks for beverages
    drinks_that_need_size = {
        "Hot Coffee", "Cold Coffee", "Frappuccino", "Iced Tea",
        "Hot Tea", "Hot Drinks", "Cold Drinks",
    }
    is_drink = True  # default assumption unless we know it's food
    if resolved_item:
        menu_check = get_menu_item_info(resolved_item)
        if menu_check["status"] == "success":
            cat = menu_check["data"].get("category", "")
            if cat in ("Bakery", "Breakfast", "Lunch", "Snacks & Sweets"):
                is_drink = False

    if is_drink:
        if not size:
            missing_fields.append("size")
        if not temperature:
            missing_fields.append("temperature")

    # Prep notes
    prep_notes.append("Prepare individually for quality consistency.")
    if customizations:
        prep_notes.append(f"Customizations: {', '.join(customizations)}.")
    if syrups:
        prep_notes.append(f"Syrups: {', '.join(syrups)}.")
    if toppings:
        prep_notes.append(f"Toppings: {', '.join(toppings)}.")
    if milk_type:
        prep_notes.append(f"Milk: {milk_type}.")

    # Build follow-up question for missing required fields
    follow_up_question: Optional[str] = None
    if "size" in missing_fields and "temperature" in missing_fields:
        follow_up_question = "What size and temperature would you like — hot or iced, and Short / Tall / Grande / Venti?"
    elif "size" in missing_fields:
        follow_up_question = "What size would you like — Short, Tall, Grande, or Venti?"
    elif "temperature" in missing_fields:
        follow_up_question = "Would you like that hot or iced?"

    if item_resolution.get("status") in ("warning", "needs_review") and resolved_item is None:
        missing_fields.append("item_name")
        candidates = item_resolution.get("candidates", [])
        if candidates:
            names = ", ".join(c["canonical_menu_item"] for c in candidates[:3])
            follow_up_question = f"I found a few similar items: {names}. Which did you mean?"
        else:
            follow_up_question = "I couldn't identify the item. Could you clarify the drink name?"

    all_warnings = warnings + inventory_warnings
    overall_status = "success"
    if missing_fields or item_resolution.get("status") == "needs_review":
        overall_status = "needs_review"
    elif all_warnings:
        overall_status = "warning"

    return make_tool_response(
        status=overall_status,
        data={
            "raw_order": raw_order,
            "structured_order": {
                "item": resolved_item,
                "size": size,
                "temperature": temperature,
                "milk_type": milk_type,
                "quantity": quantity,
                "syrups": syrups,
                "toppings": toppings,
                "customizations": customizations,
            },
            "item_resolution": {
                "status": item_resolution.get("status"),
                "canonical_name": resolved_item,
                "candidates": item_resolution.get("candidates", []),
            },
            "missing_fields": missing_fields,
            "inventory_warnings": inventory_warnings,
            "prep_notes": prep_notes,
            "follow_up_question": follow_up_question,
        },
        evidence=[
            {"source": "item_name_mapping.csv"},
            {"source": "starbucks_menu_full.csv"},
        ],
        warnings=all_warnings,
        human_review_required=bool(allergy_match),
        next_actions=(
            ["ask_follow_up_question"] if follow_up_question else ["confirm_order"]
        ),
    )
