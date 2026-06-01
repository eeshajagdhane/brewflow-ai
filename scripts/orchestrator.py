"""BrewFlow AI Orchestrator — Milestone 03 connected workflow.

Chains automations, MCP tools, and RAG retrieval into four workflow functions
that return UI-ready structured JSON.  No LLM calls are made here.

Workflow functions:
  1. run_manager_readiness(store_id, date, hour)
  2. run_barista_recommendation(store_id, date, hour, customer_request, preferences)
  3. run_order_builder(store_id, date, raw_order)
  4. run_full_workflow(store_id, date, hour, customer_request, raw_order, preferences)

All outputs follow the standard workflow response envelope:
  {run_id, workflow_type, status, steps, final_output, evidence_package,
   review_queue, review_required, review_actions, audit_log, assumptions, warnings}

The future UI calls these functions directly.  No subprocess calls needed.

Usage::

    from scripts.orchestrator import run_manager_readiness
    result = run_manager_readiness("SD001", "2024-01-15", 8)
"""

from __future__ import annotations

import re
from typing import Optional

from automations.manager_daily_briefing.run_manager_daily_briefing import run_manager_daily_briefing
from mcp_servers.brewflow_mcp_server import (
    build_and_validate_order,
    calculate_staffing_gap,
    check_inventory_status,
    detect_rush_period,
    get_menu_item_info,
    search_menu_by_preferences,
)
from rag.retrieval import retrieve_internal_knowledge
from utils.evidence import build_evidence_package, summarize_evidence_for_review
from utils.face_validity import generate_face_validity_check
from utils.workflow_common import (
    make_audit_entry,
    make_step,
    make_workflow_response,
    now_iso,
    risk_level_from_status,
)


def _attach_face_validity(
    response: dict,
    workflow_type: str,
    user_input: Optional[dict] = None,
) -> dict:
    """Compute and attach a face-validity object to a workflow response in place.

    Reads the already-assembled artifacts from the response (final_output,
    evidence_package, warnings, review_queue, assumptions) so the face-validity
    judgement always reflects exactly what the UI will see.
    """
    response["face_validity"] = generate_face_validity_check(
        workflow_type=workflow_type,
        final_output=response.get("final_output", {}),
        evidence_package=response.get("evidence_package", {}),
        warnings=response.get("warnings", []),
        review_queue=response.get("review_queue", []),
        assumptions=response.get("assumptions", []),
        user_input=user_input,
    )
    return response


# Detect allergy / medical language in a natural-language request.
_ALLERGY_RE = re.compile(
    r"\b(allerg\w*|intoleran\w*|anaphyla\w*|epi.?pen|celiac|lactose)\b",
    re.IGNORECASE,
)


def _extract_preferences_from_text(text: str, base: Optional[dict] = None) -> dict:
    """Deterministically extract preference signals from natural-language text.

    User-provided keys in `base` always win over extracted values.
    Returned dict uses the canonical keys consumed by search_menu_by_preferences.
    """
    base = dict(base or {})
    if not text:
        return base
    t = text.lower()

    # Temperature
    if "temperature" not in base:
        if re.search(r"\b(iced|cold|frozen|blended|chilled|on ice)\b", t):
            base["temperature"] = "iced"
        elif re.search(r"\b(hot|warm|steamed)\b", t):
            base["temperature"] = "hot"

    # Dietary
    if "dairy_free" not in base and re.search(
        r"\b(dairy.?free|non.?dairy|lactose|plant.?based|oat milk|almond milk|soy milk|coconut milk)\b", t
    ):
        base["dairy_free"] = True
    if "vegan" not in base and re.search(r"\bvegan\b", t):
        base["vegan"] = True
    if "gluten_free" not in base and re.search(r"\b(gluten.?free|celiac)\b", t):
        base["gluten_free"] = True

    # Caffeine intent
    if "caffeine" not in base:
        if re.search(r"\b(decaf|no caffeine|caffeine.?free|no espresso)\b", t):
            base["caffeine"] = False
        elif re.search(r"\b(caffeine|highly caffeinated|extra shot|strong)\b", t):
            base["caffeine"] = True

    # Coffee/non-coffee intent
    if "non_coffee" not in base and re.search(
        r"\b(non.?coffee|no coffee|without coffee|just tea|tea instead|refresher)\b", t
    ):
        base["non_coffee"] = True

    # Calories
    if "low_calorie" not in base and re.search(r"\b(low.?cal\w*|skinny|diet|lean|under \d+ calories)\b", t):
        base["low_calorie"] = True

    # Flavor — only set if not already provided
    if "flavor" not in base:
        for flavor in (
            "sweet",
            "fruity",
            "chocolate",
            "caramel",
            "vanilla",
            "matcha",
            "mint",
            "berry",
            "mocha",
            "cinnamon",
            "pumpkin",
            "lavender",
        ):
            if re.search(rf"\b{flavor}\b", t):
                base["flavor"] = flavor
                break

    return base


# ---------------------------------------------------------------------------
# 1. Manager Readiness Workflow
# ---------------------------------------------------------------------------


def run_manager_readiness(store_id: str, date: str, hour: int) -> dict:
    """Pre-shift manager readiness check.

    Chain:
      detect_rush_period → calculate_staffing_gap → check_inventory_status
      → retrieve_internal_knowledge (manager policies)
      → manager_daily_briefing

    Returns a full workflow response with steps, evidence package, review queue,
    and prioritized recommended manager actions.
    """
    steps: list[dict] = []
    audit_log: list[dict] = []
    all_warnings: list[str] = []
    assumptions: list[str] = []

    # Step 1: Rush detection
    rush_result = detect_rush_period(store_id, date, hour)
    steps.append(
        make_step(
            "detect_rush_period",
            "mcp_tool",
            rush_result["status"],
            rush_result["data"],
            evidence=rush_result.get("evidence", []),
            warnings=rush_result.get("warnings", []),
        )
    )
    audit_log.append(
        make_audit_entry(
            "call",
            "detect_rush_period",
            rush_result["status"],
            f"Demand level: {rush_result['data'].get('demand_level', 'unknown')}",
        )
    )
    all_warnings.extend(rush_result.get("warnings", []))

    # Step 2: Staffing gap
    staffing_result = calculate_staffing_gap(store_id, date, hour)
    steps.append(
        make_step(
            "calculate_staffing_gap",
            "mcp_tool",
            staffing_result["status"],
            staffing_result["data"],
            evidence=staffing_result.get("evidence", []),
            warnings=staffing_result.get("warnings", []),
        )
    )
    audit_log.append(
        make_audit_entry(
            "call",
            "calculate_staffing_gap",
            staffing_result["status"],
            f"Gap: {staffing_result['data'].get('staffing_gap', 'N/A')}",
        )
    )
    all_warnings.extend(staffing_result.get("warnings", []))

    # Step 3: Inventory check
    inv_result = check_inventory_status(store_id, date)
    steps.append(
        make_step(
            "check_inventory_status",
            "mcp_tool",
            inv_result["status"],
            inv_result["data"],
            evidence=inv_result.get("evidence", []),
            warnings=inv_result.get("warnings", []),
        )
    )
    audit_log.append(
        make_audit_entry(
            "call",
            "check_inventory_status",
            inv_result["status"],
            f"Available: {inv_result['data'].get('availability_flag', True)}",
        )
    )
    all_warnings.extend(inv_result.get("warnings", []))

    # Step 4: RAG — manager readiness policies
    rag_results = retrieve_internal_knowledge(
        "manager pre-shift checklist readiness demand staffing inventory",
        top_k=3,
        workflow_step="manager_readiness",
    )
    steps.append(
        make_step(
            "retrieve_internal_knowledge",
            "rag",
            "success",
            {"docs_retrieved": len(rag_results)},
            evidence=[{"source": r["filename"]} for r in rag_results],
        )
    )
    audit_log.append(
        make_audit_entry("call", "retrieve_internal_knowledge", "success", f"Retrieved {len(rag_results)} policy docs.")
    )

    # Step 5: Manager daily briefing
    briefing_result = run_manager_daily_briefing(store_id, date, hour)
    steps.append(
        make_step(
            "manager_daily_briefing",
            "automation",
            briefing_result["status"],
            briefing_result["data"],
            evidence=briefing_result.get("evidence", []),
            warnings=briefing_result.get("warnings", []),
        )
    )
    audit_log.append(
        make_audit_entry(
            "call",
            "manager_daily_briefing",
            briefing_result["status"],
            f"Overall: {briefing_result['data']['readiness_summary']['overall_status']}",
        )
    )
    all_warnings.extend(briefing_result.get("warnings", []))

    # Deduplicate warnings
    all_warnings = list(dict.fromkeys(all_warnings))

    # Evidence package
    tool_outputs = [
        {
            "tool": "detect_rush_period",
            "status": rush_result["status"],
            "summary": str(rush_result["data"].get("demand_level", "")),
        },
        {
            "tool": "calculate_staffing_gap",
            "status": staffing_result["status"],
            "summary": f"gap={staffing_result['data'].get('staffing_gap', 0)}",
        },
        {
            "tool": "check_inventory_status",
            "status": inv_result["status"],
            "summary": f"available={inv_result['data'].get('availability_flag', True)}",
        },
        {
            "tool": "manager_daily_briefing",
            "status": briefing_result["status"],
            "summary": str(briefing_result["data"].get("readiness_summary", {})),
        },
    ]
    evidence_package = build_evidence_package(tool_outputs, rag_results, assumptions=assumptions, warnings=all_warnings)

    # Review queue — flag if needs_review
    review_queue: list[dict] = []
    if briefing_result["human_review_required"]:
        review_queue.append(
            {
                "item": "manager_readiness_briefing",
                "reason": "Critical alerts detected — human review required before shift opens.",
                "data": briefing_result["data"]["readiness_summary"],
            }
        )

    # Determine overall workflow status
    statuses = [rush_result["status"], staffing_result["status"], inv_result["status"], briefing_result["status"]]
    if "needs_review" in statuses:
        overall_status = "needs_review"
    elif "warning" in statuses:
        overall_status = "warning"
    else:
        overall_status = "success"

    response = make_workflow_response(
        workflow_type="manager_readiness",
        status=overall_status,
        steps=steps,
        final_output={
            "store_id": store_id,
            "date": date,
            "hour": hour,
            "readiness_summary": briefing_result["data"]["readiness_summary"],
            "recommended_actions": briefing_result["data"]["recommended_manager_actions"],
            "barista_guidance": briefing_result["data"]["barista_guidance"],
            "active_promotions": briefing_result["data"]["active_promotions"],
            "demand_detail": rush_result["data"],
            "staffing_detail": staffing_result["data"],
            "inventory_low_stock": briefing_result["data"]["inventory_low_stock"],
            "inventory_unavailable": briefing_result["data"]["inventory_unavailable"],
        },
        evidence_package=evidence_package,
        review_queue=review_queue,
        review_required=briefing_result["human_review_required"],
        audit_log=audit_log,
        assumptions=assumptions,
        warnings=all_warnings,
    )
    return _attach_face_validity(
        response,
        "manager_readiness",
        user_input={"store_id": store_id, "date": date, "hour": hour},
    )


# ---------------------------------------------------------------------------
# 2. Barista Recommendation Workflow
# ---------------------------------------------------------------------------


def run_barista_recommendation(
    store_id: str,
    date: str,
    hour: int,
    customer_request: str,
    preferences: Optional[dict] = None,
) -> dict:
    """Inventory-aware drink recommendation workflow.

    Chain:
      detect_rush_period → retrieve_internal_knowledge (recommendation + dietary + substitution + rush)
      → search_menu_by_preferences → check_inventory_status (for top candidates)

    Returns ranked candidates with inventory warnings and RAG policy guidance.
    The recommendation skill uses this output to produce the human-facing response.
    """
    if preferences is None:
        preferences = {}

    # Parse natural-language signals out of the customer request and merge with
    # explicit preferences (explicit preferences win on conflict).
    preferences = _extract_preferences_from_text(customer_request, preferences)

    # Detect named or category-defining menu terms in the customer request.
    # Strategy:
    #   score >= 2 (e.g. "Pink Drink") → exact named_item boost + category group + temperature
    #   score == 1 (e.g. "Latte", "Frappuccino") → keyword boost only, group by common category
    # In both cases, only add keywords that actually appear in the top candidate's name
    # so generic filler words ("want", "something") are never injected.
    from utils.menu_matching import find_menu_candidates as _find_candidates  # local import avoids circular

    _cold_categories = {"Cold Coffee", "Cold Drinks", "Iced Tea", "Frappuccino", "Bottled Beverages"}
    _hot_categories = {"Hot Coffee", "Hot Tea", "Hot Drinks"}
    _item_hints = _find_candidates(customer_request, limit=8)
    if _item_hints:
        _top = _item_hints[0]
        _top_name = _top["item"].lower()

        # Only inject words that actually appear in the top candidate's name
        _query_words = [w for w in customer_request.lower().split() if len(w) > 2]
        _matching_words = [w for w in _query_words if w in _top_name]
        if _matching_words:
            preferences["keywords"] = list(set(preferences.get("keywords", []) + _matching_words))

        if _top["score"] >= 2:
            # Specific named item — strong match: add item boost + category grouping + temperature
            preferences.setdefault("named_item", _top["item"].lower())
            preferences.setdefault("named_category", _top["category"])
            if "temperature" not in preferences:
                if _top["category"] in _cold_categories:
                    preferences["temperature"] = "iced"
                elif _top["category"] in _hot_categories:
                    preferences["temperature"] = "hot"
        elif _top["score"] == 1 and _matching_words:
            # Category-level term (e.g. "latte", "frappuccino") — boost the whole group
            # Find the dominant category among all matches with the same keyword
            _cats = [h["category"] for h in _item_hints if any(w in h["item"].lower() for w in _matching_words)]
            _dominant_cat = max(set(_cats), key=_cats.count) if _cats else None
            if _dominant_cat:
                preferences.setdefault("named_category", _dominant_cat)
                if "temperature" not in preferences:
                    if _dominant_cat in _cold_categories:
                        preferences["temperature"] = "iced"
                    elif _dominant_cat in _hot_categories:
                        preferences["temperature"] = "hot"

    steps: list[dict] = []
    audit_log: list[dict] = []
    all_warnings: list[str] = []
    assumptions: list[str] = []

    # Detect allergy / medical language up front — the recommendation must
    # not guarantee allergen-free preparation; flag for human review and
    # prepend dietary RAG context.
    allergy_detected = bool(_ALLERGY_RE.search(customer_request or ""))
    if allergy_detected:
        all_warnings.append(
            "Allergy or medical language detected in customer request. "
            "Do NOT guarantee allergen-free preparation; refer to the official "
            "Starbucks allergen guide and flag for human review."
        )

    # Step 1: Rush context
    rush_result = detect_rush_period(store_id, date, hour)
    rush_risk = rush_result["data"].get("rush_risk", "low")
    steps.append(
        make_step(
            "detect_rush_period",
            "mcp_tool",
            rush_result["status"],
            rush_result["data"],
            warnings=rush_result.get("warnings", []),
        )
    )
    audit_log.append(make_audit_entry("call", "detect_rush_period", rush_result["status"], f"Rush risk: {rush_risk}"))
    all_warnings.extend(rush_result.get("warnings", []))

    # If rush is high, note it and surface guidance
    if rush_risk == "high":
        assumptions.append("Rush period active — candidates limited to fast-to-prepare options.")

    # Step 2: RAG — recommendation and dietary policies
    rag_query = f"recommendation {customer_request} dietary allergen substitution rush"
    rag_results = retrieve_internal_knowledge(rag_query, top_k=3, workflow_step="barista_recommendation")
    steps.append(
        make_step(
            "retrieve_internal_knowledge",
            "rag",
            "success",
            {"docs_retrieved": len(rag_results), "query": rag_query},
            evidence=[{"source": r["filename"]} for r in rag_results],
        )
    )
    audit_log.append(
        make_audit_entry(
            "call",
            "retrieve_internal_knowledge",
            "success",
            f"Retrieved {len(rag_results)} docs for recommendation context.",
        )
    )

    # Step 3: Menu search
    search_result = search_menu_by_preferences(preferences, store_id=store_id, date=date, hour=hour)
    steps.append(
        make_step(
            "search_menu_by_preferences",
            "mcp_tool",
            search_result["status"],
            search_result["data"],
            warnings=search_result.get("warnings", []),
        )
    )
    audit_log.append(
        make_audit_entry(
            "call",
            "search_menu_by_preferences",
            search_result["status"],
            f"Found {search_result['data'].get('total_matched', 0)} matches.",
        )
    )
    all_warnings.extend(search_result.get("warnings", []))

    candidates = search_result["data"].get("candidates", [])

    # Step 4: Inventory check for top 3 candidates
    top_candidate_items = [c["item"] for c in candidates[:3]]
    inv_result = None
    if top_candidate_items:
        inv_result = check_inventory_status(store_id, date)
        steps.append(
            make_step(
                "check_inventory_status",
                "mcp_tool",
                inv_result["status"],
                inv_result["data"],
                warnings=inv_result.get("warnings", []),
            )
        )
        audit_log.append(
            make_audit_entry(
                "call",
                "check_inventory_status",
                inv_result["status"],
                f"Rec safe: {inv_result['data'].get('recommendation_safe', True)}",
            )
        )
        all_warnings.extend(inv_result.get("warnings", []))

        # Annotate candidates with inventory flags
        inv_ingredients = {
            ing["inventory_ingredient"]: ing
            for ing in inv_result["data"].get("ingredients", [])
            if ing.get("inventory_ingredient")
        }
        for c in candidates[:3]:
            item_info = get_menu_item_info(c["item"])
            if item_info["status"] == "success":
                key_ing = str(item_info["data"].get("key_ingredients", "")).split(",")
                c["inventory_safe"] = True
                c["inventory_warnings"] = []
                for ing_name in key_ing:
                    ing_name_clean = ing_name.strip().lower()
                    for inv_name, inv_data in inv_ingredients.items():
                        if ing_name_clean in inv_name.lower() or inv_name.lower() in ing_name_clean:
                            if not inv_data.get("recommendation_safe", True):
                                c["inventory_safe"] = False
                                c["inventory_warnings"].append(
                                    f"{inv_data['inventory_ingredient']} is {inv_data['status']}"
                                )

    all_warnings = list(dict.fromkeys(all_warnings))

    tool_outputs = [
        {"tool": "detect_rush_period", "status": rush_result["status"], "summary": f"rush_risk={rush_risk}"},
        {
            "tool": "search_menu_by_preferences",
            "status": search_result["status"],
            "summary": f"{len(candidates)} candidates",
        },
    ]
    if inv_result:
        tool_outputs.append(
            {
                "tool": "check_inventory_status",
                "status": inv_result["status"],
                "summary": f"rec_safe={inv_result['data'].get('recommendation_safe', True)}",
            }
        )
    evidence_package = build_evidence_package(tool_outputs, rag_results, assumptions=assumptions, warnings=all_warnings)

    review_queue: list[dict] = []
    if allergy_detected:
        review_queue.append(
            {
                "item": "recommendation_allergy_review",
                "reason": "Allergy or medical language in customer request — barista must verify allergens before recommending.",
                "customer_request": customer_request,
            }
        )
    if search_result["data"].get("candidates"):
        review_queue.append(
            {
                "item": "recommendation_candidates",
                "reason": "Review top candidates before presenting to customer.",
                "candidates": candidates[:3],
            }
        )

    statuses = [rush_result["status"], search_result["status"]]
    if inv_result:
        statuses.append(inv_result["status"])
    if allergy_detected:
        statuses.append("needs_review")
    overall_status = (
        "needs_review" if "needs_review" in statuses else ("warning" if "warning" in statuses else "success")
    )

    response = make_workflow_response(
        workflow_type="barista_recommendation",
        status=overall_status,
        steps=steps,
        final_output={
            "store_id": store_id,
            "date": date,
            "hour": hour,
            "customer_request": customer_request,
            "preferences": preferences,
            "rush_risk": rush_risk,
            "top_candidates": candidates[:5],
            "rag_guidance": [{"doc": r["filename"], "snippet": r["snippet"][:150]} for r in rag_results],
        },
        evidence_package=evidence_package,
        review_queue=review_queue,
        review_required=True,  # always human-review before presenting recommendation
        audit_log=audit_log,
        assumptions=assumptions,
        warnings=all_warnings,
    )
    return _attach_face_validity(
        response,
        "barista_recommendation",
        user_input={
            "customer_request": customer_request,
            "preferences": preferences,
            "store_id": store_id,
            "date": date,
            "hour": hour,
        },
    )


# ---------------------------------------------------------------------------
# 3. Order Builder Workflow
# ---------------------------------------------------------------------------


def run_order_builder(store_id: str, date: str, raw_order: str) -> dict:
    """Parse and validate a raw order string into a structured order.

    Chain:
      build_and_validate_order → retrieve_internal_knowledge (order confirmation + quality SOP)

    Returns structured order, missing fields, follow-up question if needed,
    and RAG confirmation guidance.
    """
    steps: list[dict] = []
    audit_log: list[dict] = []
    all_warnings: list[str] = []
    assumptions: list[str] = []

    # Step 1: Build and validate order
    order_result = build_and_validate_order(raw_order, store_id=store_id, date=date)
    steps.append(
        make_step(
            "build_and_validate_order",
            "mcp_tool",
            order_result["status"],
            order_result["data"],
            warnings=order_result.get("warnings", []),
        )
    )
    audit_log.append(
        make_audit_entry(
            "call",
            "build_and_validate_order",
            order_result["status"],
            f"Item: {order_result['data']['structured_order'].get('item', 'unknown')} "
            f"Missing: {order_result['data']['missing_fields']}",
        )
    )
    all_warnings.extend(order_result.get("warnings", []))

    # Step 2: RAG — order confirmation and quality SOP
    rag_results = retrieve_internal_knowledge(
        "order confirmation standard quality preparation individually",
        top_k=3,
        workflow_step="order_builder",
    )
    steps.append(
        make_step(
            "retrieve_internal_knowledge",
            "rag",
            "success",
            {"docs_retrieved": len(rag_results)},
            evidence=[{"source": r["filename"]} for r in rag_results],
        )
    )
    audit_log.append(
        make_audit_entry(
            "call", "retrieve_internal_knowledge", "success", f"Retrieved {len(rag_results)} confirmation policy docs."
        )
    )

    all_warnings = list(dict.fromkeys(all_warnings))

    tool_outputs = [
        {
            "tool": "build_and_validate_order",
            "status": order_result["status"],
            "summary": str(order_result["data"].get("structured_order", {})),
        }
    ]
    evidence_package = build_evidence_package(tool_outputs, rag_results, assumptions=assumptions, warnings=all_warnings)

    review_queue: list[dict] = []
    if order_result["human_review_required"]:
        review_queue.append(
            {
                "item": "order_allergy_review",
                "reason": "Allergy or medical language in order — human review required.",
                "data": order_result["data"],
            }
        )
    if order_result["data"]["missing_fields"]:
        review_queue.append(
            {
                "item": "order_missing_fields",
                "reason": f"Missing required fields: {order_result['data']['missing_fields']}",
                "follow_up_question": order_result["data"]["follow_up_question"],
            }
        )

    structured_order = order_result["data"]["structured_order"]
    overall_status = order_result["status"]

    response = make_workflow_response(
        workflow_type="order_builder",
        status=overall_status,
        steps=steps,
        final_output={
            "store_id": store_id,
            "date": date,
            "raw_order": raw_order,
            "structured_order": structured_order,
            "missing_fields": order_result["data"]["missing_fields"],
            "follow_up_question": order_result["data"].get("follow_up_question"),
            "inventory_warnings": order_result["data"].get("inventory_warnings", []),
            "prep_notes": order_result["data"].get("prep_notes", []),
            "rag_confirmation_guidance": [{"doc": r["filename"], "snippet": r["snippet"][:150]} for r in rag_results],
        },
        evidence_package=evidence_package,
        review_queue=review_queue,
        review_required=bool(order_result["human_review_required"] or order_result["data"]["missing_fields"]),
        audit_log=audit_log,
        assumptions=assumptions,
        warnings=all_warnings,
    )
    return _attach_face_validity(
        response,
        "order_builder",
        user_input={"raw_order": raw_order, "store_id": store_id, "date": date},
    )


# ---------------------------------------------------------------------------
# 4. Full Workflow
# ---------------------------------------------------------------------------


def run_full_workflow(
    store_id: str,
    date: str,
    hour: int,
    customer_request: str,
    raw_order: Optional[str] = None,
    preferences: Optional[dict] = None,
) -> dict:
    """Complete BrewFlow workflow: readiness → recommendation → order builder.

    Chain:
      run_manager_readiness → run_barista_recommendation
      → run_order_builder (if raw_order is provided or a candidate was selected)

    The barista_guidance from readiness is passed into the recommendation context.
    All steps, evidence, and audit logs are merged into a single workflow package.
    """
    if preferences is None:
        preferences = {}

    merged_steps: list[dict] = []
    merged_audit: list[dict] = []
    merged_warnings: list[str] = []
    merged_assumptions: list[str] = []
    merged_tool_outputs: list[dict] = []
    merged_rag_results: list[dict] = []

    # --- Phase 1: Manager Readiness ---
    readiness = run_manager_readiness(store_id, date, hour)
    for step in readiness["steps"]:
        step["phase"] = "manager_readiness"
        merged_steps.append(step)
    merged_audit.extend(readiness.get("audit_log", []))
    merged_warnings.extend(readiness.get("warnings", []))
    merged_assumptions.extend(readiness.get("assumptions", []))
    merged_tool_outputs.extend(readiness["evidence_package"].get("tool_outputs", []))
    merged_rag_results.extend(readiness["evidence_package"].get("rag_results", []))

    # Carry barista_guidance into recommendation preferences
    barista_guidance = readiness["final_output"].get("barista_guidance", {})
    rush_risk = barista_guidance.get("rush_level", "low")
    if rush_risk == "high":
        merged_assumptions.append("Rush period active — recommendation tuned for high-demand context.")

    # --- Phase 2: Recommendation ---
    recommendation = run_barista_recommendation(store_id, date, hour, customer_request, preferences)
    for step in recommendation["steps"]:
        step["phase"] = "barista_recommendation"
        merged_steps.append(step)
    merged_audit.extend(recommendation.get("audit_log", []))
    merged_warnings.extend(recommendation.get("warnings", []))
    merged_assumptions.extend(recommendation.get("assumptions", []))
    merged_tool_outputs.extend(recommendation["evidence_package"].get("tool_outputs", []))
    merged_rag_results.extend(recommendation["evidence_package"].get("rag_results", []))

    # --- Phase 3: Order Builder (if raw_order provided) ---
    order_output: Optional[dict] = None
    if raw_order:
        order_wf = run_order_builder(store_id, date, raw_order)
        for step in order_wf["steps"]:
            step["phase"] = "order_builder"
            merged_steps.append(step)
        merged_audit.extend(order_wf.get("audit_log", []))
        merged_warnings.extend(order_wf.get("warnings", []))
        merged_assumptions.extend(order_wf.get("assumptions", []))
        merged_tool_outputs.extend(order_wf["evidence_package"].get("tool_outputs", []))
        merged_rag_results.extend(order_wf["evidence_package"].get("rag_results", []))
        order_output = order_wf["final_output"]

    # Deduplicate
    merged_warnings = list(dict.fromkeys(merged_warnings))
    merged_assumptions = list(dict.fromkeys(merged_assumptions))

    # Merged evidence package
    evidence_package = build_evidence_package(
        merged_tool_outputs, merged_rag_results, assumptions=merged_assumptions, warnings=merged_warnings
    )

    # Collect review queues
    review_queue: list[dict] = []
    review_queue.extend(readiness.get("review_queue", []))
    review_queue.extend(recommendation.get("review_queue", []))
    if raw_order:
        review_queue.extend(order_wf.get("review_queue", []))  # type: ignore[possibly-undefined]

    review_required = (
        readiness.get("review_required", False)
        or recommendation.get("review_required", False)
        or (raw_order and order_wf.get("review_required", False))  # type: ignore[possibly-undefined]
    )

    # Overall status: take worst status across all phases
    phase_statuses = [readiness["status"], recommendation["status"]]
    if raw_order:
        phase_statuses.append(order_wf["status"])  # type: ignore[possibly-undefined]
    overall_status = (
        "needs_review" if "needs_review" in phase_statuses else "warning" if "warning" in phase_statuses else "success"
    )

    response = make_workflow_response(
        workflow_type="full_workflow",
        status=overall_status,
        steps=merged_steps,
        final_output={
            "store_id": store_id,
            "date": date,
            "hour": hour,
            "customer_request": customer_request,
            "manager_readiness": readiness["final_output"],
            "recommendation": recommendation["final_output"],
            "order": order_output,
        },
        evidence_package=evidence_package,
        review_queue=review_queue,
        review_required=review_required,
        audit_log=merged_audit,
        assumptions=merged_assumptions,
        warnings=merged_warnings,
    )
    return _attach_face_validity(
        response,
        "full_workflow",
        user_input={
            "customer_request": customer_request,
            "raw_order": raw_order,
            "preferences": preferences,
            "store_id": store_id,
            "date": date,
            "hour": hour,
        },
    )
