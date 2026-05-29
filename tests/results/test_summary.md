# BrewFlow AI — Test Summary

Test cases mapped to Milestone 04 grading needs.
All tests run locally with no external API keys.

## Test Execution

```bash
# Run all BrewFlow tests
uv run pytest tests/test_mcp_tools.py tests/test_rag_retrieval.py tests/test_brewflow_workflow.py -v

# Run the full suite (includes starter reference tests if any)
uv run pytest
```

## Test Case Descriptions

### TC-01: Normal Recommendation (Happy Path)
**File:** `test_brewflow_workflow.py::test_barista_recommendation_has_candidates`
**Scenario:** Customer requests "something cold and refreshing." Preferences: temperature=cold.
**What is tested:** search_menu_by_preferences returns ranked candidates; orchestrator assembles evidence.
**Expected:** status=success or warning, ≥1 candidate returned, evidence_count > 0.

---

### TC-02: Dairy-Free Recommendation
**File:** `test_brewflow_workflow.py::test_barista_recommendation_dairy_free`
**Scenario:** Customer is dairy-free. Preferences: dairy_free=True.
**What is tested:** All returned candidates have vegan=True (dairy-free proxy).
**Expected:** Candidates list non-empty; all items are vegan.

---

### TC-03: Low-Stock Substitution
**File:** `test_mcp_tools.py::test_check_inventory_exact_date`
**Scenario:** Store SD001 on 2024-01-15 has low-stock and unavailable ingredients.
**What is tested:** inventory_monitoring returns low_stock and unavailable lists; check_inventory_status flags recommendation_safe.
**Expected:** status=warning or needs_review; unavailable list is not empty.

---

### TC-04: Missing Size in Order
**File:** `test_mcp_tools.py::test_build_and_validate_order_missing_size` + `test_brewflow_workflow.py::test_order_builder_missing_size_triggers_review`
**Scenario:** Customer says "I want a hot caramel macchiato" without specifying size.
**What is tested:** missing_fields includes "size"; follow_up_question is set; review_required = True.
**Expected:** missing_fields=["size"], follow_up_question non-null.

---

### TC-05: Vague Customer Request
**File:** `test_mcp_tools.py::test_search_menu_empty_prefs_returns_results`
**Scenario:** Customer gives no preferences. Empty preferences dict.
**What is tested:** search_menu_by_preferences still returns results from the menu.
**Expected:** Candidates list non-empty; no error.

---

### TC-06: Allergy-Sensitive Request
**File:** `test_mcp_tools.py::test_build_and_validate_order_allergy_triggers_review` + `test_brewflow_workflow.py::test_order_builder_allergy_requires_human_review`
**Scenario:** Customer says "I have a nut allergy."
**What is tested:** human_review_required = True; allergy warning in response; review_queue contains allergy item.
**Expected:** human_review_required=True; warning contains "allergy".

---

### TC-07: Manager Readiness (Normal)
**File:** `test_brewflow_workflow.py::test_manager_readiness_structure` and `test_manager_readiness_step_names`
**Scenario:** Manager runs readiness check for SD001 on 2024-01-15 at 8 AM.
**What is tested:** All 5 steps run; barista_guidance is populated; evidence_package has tool + RAG outputs.
**Expected:** 5 steps in output; review_actions present; evidence_count > 0.

---

### TC-08: Understaffed Rush
**File:** `test_mcp_tools.py::test_calculate_staffing_gap_known_date_hour`
**Scenario:** Store with staffing_gap < 0 during a high-rush period.
**What is tested:** calculate_staffing_gap returns risk_level and staffing_gap; manager_daily_briefing includes gap in recommended_actions.
**Expected:** staffing_gap int; risk_level in (low, medium, high).

---

### TC-09: Weak or Missing Evidence
**File:** `test_rag_retrieval.py::test_knowledge_base_index_populated`
**Scenario:** RAG is queried for a topic with no good match.
**What is tested:** retrieve_internal_knowledge returns a warning when all scores are 0.
**Expected:** Index is non-empty; weak evidence case triggers warning in result.

---

### TC-10: Order Confirmation (Prep Notes)
**File:** `test_mcp_tools.py::test_build_and_validate_order_prep_notes_individual` + `test_brewflow_workflow.py::test_order_builder_prep_notes_include_individually`
**Scenario:** Any completed order.
**What is tested:** prep_notes always include "individually" per drink_quality_consistency_sop.md.
**Expected:** "individually" appears in prep_notes text.

---

### TC-11: Full Workflow Chain
**File:** `test_brewflow_workflow.py::test_full_workflow_has_all_phases`
**Scenario:** Full workflow from readiness → recommendation → order.
**What is tested:** All three phases present in steps; audit_log populated; evidence_count increases with order phase.
**Expected:** phases = {manager_readiness, barista_recommendation, order_builder}.

---

### TC-12: Item Name Mapping Resolution
**File:** `test_mcp_tools.py::test_build_and_validate_order_item_name_mapping`
**Scenario:** Order uses item name from item_name_mapping.csv.
**What is tested:** Item resolves to canonical menu name; structured_order.item is not None.
**Expected:** structured_order.item non-null.

## Reference-Only Tests (Not Run by Default)

| File | Why Reference-Only |
|---|---|
| `tests/test_workflow.py` | Requires DeepEval + LLM API calls — marked `integration` |
| `tests/utils/test_connect.py` | Requires OAuth credentials |
| `tests/utils/test_oauth_gpt.py` | Requires OpenAI API key |
