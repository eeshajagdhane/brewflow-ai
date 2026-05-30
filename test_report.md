# BrewFlow AI — Test Report

This document covers Milestone 04's "Testing AI Performance" deliverable.

---

## 1. Purpose of testing

Before a manager or barista relies on BrewFlow AI in a real shift, we
need confidence that the system behaves correctly across both the
normal happy path and the edge cases that matter most — allergy
language, missing order fields, stale data, ambiguous item names, and
weak evidence. The test suite is the artefact that lets a teammate
change a tool, swap a model, or update a document and know within
seconds whether anything broke.

All tests below are **local and deterministic** — no external APIs, no
LLM keys, no DeepEval-style remote judges. They run on the same
simulated data files in `data/raw/` that the live UI uses, so a passing
test means the same input would produce the same JSON in the running
orchestrator and Flask UI.

---

## 2. Test coverage summary

| Test area | File | What it checks | Cases | Result |
|---|---|---|---:|---|
| MCP tools | `tests/test_mcp_tools.py` | All 6 MCP tools (menu info, preference search, inventory check, rush detection, staffing gap, order builder) + data file existence | 27 | ✅ pass |
| RAG retrieval | `tests/test_rag_retrieval.py` | All 12 knowledge-base docs indexed, EXAMPLE.md excluded, 4 key query scenarios (dietary, substitution, rush, order confirmation), result shape, top-k, workflow-step boosting | 16 | ✅ pass |
| Workflow orchestration | `tests/test_brewflow_workflow.py` | All 4 orchestrator functions return UI-ready envelopes with `evidence_package`, `review_queue`, `review_required`, `review_actions`, `audit_log`, `assumptions`, `warnings`, `face_validity` | 23 | ✅ pass |
| Face validity layer | `tests/test_face_validity.py` | Plausible / weak / needs_review status logic, allergy escalation, missing-field follow-up, orchestrator integration, RAG-leak regression | 15 | ✅ pass |
| UI routes | `tests/test_ui_routes.py` | Flask app imports, index page renders, 4 workflow API routes hit the live orchestrator, review action records, audit log accumulates + clears | 14 | ✅ pass |
| **Total** | | | **95** | **✅ 95/95** |

**Run command:**
```bash
uv run pytest tests/test_mcp_tools.py tests/test_rag_retrieval.py \
              tests/test_brewflow_workflow.py tests/test_face_validity.py \
              tests/test_ui_routes.py
```

---

## 3. Realistic test cases

Ten representative cases drawn from the suite, covering the workflow
scenarios most likely to appear during a real shift.

| # | Test case | User input | Expected behaviour | Evidence / data expected | Actual result | Pass / Fail | Notes |
|---|---|---|---|---|---|---|---|
| **TC-01** | Normal full workflow | store=SD001, date=2024-01-15, hour=8, request=*"iced sweet dairy-free medium caffeine"*, raw_order=*"grande iced chai with almond milk"* | All 3 phases run; status=needs_review (designed); face_validity=needs_review/review; FV quality ≥ 0.7 | ≥4 tool outputs; 3+ RAG docs; review_queue has `recommendation_candidates` | All 3 phases ran, FV score 0.87, status as expected | ✅ Pass | `test_api_full_workflow_runs_all_phases` |
| **TC-02** | Dairy-free recommendation | store=SD001, date=2024-01-15, hour=8, preferences={dairy_free: True} | All candidates have `vegan=True` (dairy-free proxy); warning surfaces the heuristic | Top 8 candidates with vegan=True; `Dairy-free preference applied as 'Vegan=Yes' heuristic` warning | All returned items vegan, warning visible | ✅ Pass | `test_search_menu_dairy_free_returns_candidates` |
| **TC-03** | High-caffeine cold coffee | preferences={non_coffee: False, caffeine: True, temperature: cold} | Cold-coffee candidates rank top; reason_codes include `has_caffeine` | Top items include Nitro Cold Brew, Cold Brew Coffee, Iced Caffe Americano | Cold-coffee items ranked highest with `has_caffeine` codes | ✅ Pass | Exercises `search_menu_by_preferences` |
| **TC-04** | Inventory check returns latest-prior snapshot | store=SD001, date=2024-01-16 (no exact-date snapshot) | Falls back to latest prior snapshot ≤ 2024-01-16; surfaces snapshot date used | `snapshot_date_used` ≤ requested date; warning if used | Latest-prior fallback worked; snapshot date returned | ✅ Pass | `test_check_inventory_latest_prior_fallback` |
| **TC-05** | Allergy-sensitive request | request=*"I have a nut allergy and want something dairy-free"* | face_validity.status=needs_review, recommended_action=`escalate`; review_queue contains `recommendation_allergy_review` | Warning *"Allergy or medical language detected"*; allergy concern in FV | Status + action correct; review item present | ✅ Pass | `test_api_barista_recommendation_allergy_escalates` + `test_orchestrator_allergy_request_escalates` |
| **TC-06** | Missing size in order | raw_order=*"iced latte with oat milk"* (no size) | `missing_fields: ["size"]`; follow_up_question populated; status=needs_review | follow_up_question = *"What size would you like — Short, Tall, Grande, or Venti?"* | All three fields populated correctly | ✅ Pass | `test_api_order_builder_missing_size_followup` |
| **TC-07** | Unknown / ambiguous item | raw_order=*"large unicorn cloud drink with rainbow foam"* | item_resolution falls back via menu search; candidates list populated; status=warning or needs_review | item_resolution.candidates non-empty even if no exact match | Resolution fell back, candidates surfaced | ✅ Pass | Covered by structure assertions in `test_build_and_validate_order_response_structure` |
| **TC-08** | Manager readiness — high-demand morning | store=SD001, date=2024-01-15, hour=8 | demand_level=Very High, forecast≈211, recommended_actions includes CRITICAL/ACTION items, barista_guidance.rush_level=high | Manager Readiness card with non-empty actions; rush pill = high | All values matched expected ranges | ✅ Pass | `test_manager_readiness_structure` + `test_manager_readiness_barista_guidance` |
| **TC-09** | Weak / missing data (out-of-range date) | store=SD001, date=1900-01-01, hour=8 (detect_rush_period) | status=warning, warnings list non-empty | At least one warning entry; demand may default to low | Warning returned, status downgraded | ✅ Pass | `test_detect_rush_period_missing_data_returns_warning` |
| **TC-10** | UI route end-to-end | POST to `/api/full_workflow` via Flask test_client | HTTP 200; full workflow envelope including face_validity key; review_required=True | All 3 phases present in `steps`; face_validity has status + confidence + anchors_used + recommended_action | All assertions pass | ✅ Pass | `test_api_full_workflow_runs_all_phases` |

> All 95 tests pass; the table above shows 10 representative tests that
> map directly to user-visible behaviours. The full suite breakdown is
> in Section 2.

---

## 4. Failure cases that were tested

These map 1-to-1 against the predicted failure register in
[`failure_cases.md`](failure_cases.md). Each row identifies the failure,
the test (or test class) that catches a regression, and the safety net
the orchestrator provides.

| Failure case | Test coverage | Safety net in the running system |
|---|---|---|
| **Wrong item resolution** (FC-01) | `test_build_and_validate_order_missing_size`, `test_order_builder_missing_size_triggers_review` | `item_resolution.candidates` surfaced + follow-up question + review queue entry |
| **Loose preference keys** (used to be silently ignored) | `test_search_menu_dairy_free_returns_candidates` (asserts candidates respect `dairy_free=True`); manual smoke confirms `milk_preference`, `coffee_preference`, `caffeine: "medium"`, `sweetness: "sweet"` are normalised | `_normalize_preferences()` in `mcp_servers/brewflow_mcp_server.py` maps loose keys to canonical preference flags |
| **Natural-language customer request ignored** | `test_barista_recommendation_dairy_free` (preferences inferred from request text); orchestrator integration tests | `_extract_preferences_from_text()` in `scripts/orchestrator.py` parses temperature, dietary, caffeine, flavor signals before scoring |
| **Allergy-sensitive request not flagged** | `test_api_barista_recommendation_allergy_escalates`, `test_orchestrator_allergy_request_escalates`, `test_order_builder_allergy_requires_human_review` | `_ALLERGY_RE` in orchestrator + `_ALLERGY_PATTERN` / `_MEDICAL_PATTERN` in face_validity; status forced to `needs_review` + action forced to `escalate` |
| **False escalation from RAG content** (FC-08) | `test_benign_request_does_not_falsely_escalate`, `test_full_workflow_benign_request_does_not_escalate` | `_safe_signal_text()` scans only safe sources (user_input, warnings, review_queue labels) — not the stringified final_output |
| **Missing required order fields** | `test_api_order_builder_missing_size_followup`, `test_missing_size_field_triggers_followup` | Structured parsing detects missing fields; orchestrator returns `ask_follow_up` recommended action |
| **Missing data / weak evidence** | `test_detect_rush_period_missing_data_returns_warning`, `test_missing_evidence_returns_weak` | Status downgrades to `weak` when evidence_count = 0 or quality_label = "weak"; FV returns `weak` + review action |

---

## 5. Before / after improvement (concrete)

### Improvement A — Face validity false-positive fix *(headline)*

**Before:**
`face_validity` stringified `final_output` and scanned the full string
for allergy keywords. Whenever the recommendation workflow retrieved
`dietary_allergen_guidance.md` from RAG (which is normal for any
dairy-free or dietary query), the word *"allergen"* leaked into the
scan. Result: `recommended_action = "escalate"` on benign requests like
*"something hot and caffeinated"*.

Live evidence captured during the audit:

| Request | Pre-fix recommended_action | Allergy hits in final_output |
|---|---|---|
| *"I want something iced, sweet, dairy-free, and medium caffeine."* | `review` ✓ | none |
| *"something hot and caffeinated"* | **`escalate` ✗** | `{"allergen"}` (leaked from RAG doc filename) |
| *"I have a nut allergy and want something cold"* | `escalate` ✓ | `{"allergen"}` (legitimate hit on user text) |

**After:**
`utils/face_validity._safe_signal_text()` now scans only safe sources:
`user_input`, `warnings`, and `review_queue` item labels + reasons.
The full `final_output` (which embeds RAG metadata) is no longer
scanned. Real allergy language in the user request still escalates;
benign requests no longer escalate.

| Request | Post-fix recommended_action |
|---|---|
| *"I want something iced, sweet, dairy-free, and medium caffeine."* | `review` ✓ |
| *"something hot and caffeinated"* | `review` ✓ *(was wrongly `escalate`)* |
| *"I have a nut allergy and want something cold"* | `escalate` ✓ |
| Order: *"grande latte, I have a nut allergy"* | `escalate` ✓ |

Two regression tests now lock this in:
`test_benign_request_does_not_falsely_escalate` and
`test_full_workflow_benign_request_does_not_escalate`.

### Improvement B — Order parsing item resolution

**Before:**
The raw order *"grande iced matcha with oat milk, light ice, and
vanilla"* resolved incorrectly to *"Vanilla Biscotti with Almonds"*.
Reason: after stripping `grande`, `iced`, and `oat milk`, the remaining
`"matcha with light ice and vanilla"` was passed to `find_menu_candidates`
which scored *"Vanilla Biscotti with Almonds"* higher than *"Iced Matcha
Tea Latte"* on combined keyword count.

**After:**
The cleaning logic in `build_and_validate_order` now also strips already-
captured syrups, toppings, customisations, and connector words ("with",
"and"), but explicitly **keeps the temperature word** (`iced` /`hot`) so
the menu search can disambiguate temperature-specific items. The
sentence cleans down to `"iced matcha"`, which the menu search
resolves to *"Iced Matcha Tea Latte"* with a confident score.

Tests: `test_build_and_validate_order_normal`,
`test_order_builder_normal_order`, plus the live smoke run
documented in the validation logs.

---

## 6. Three most common failure patterns

After running the suite end-to-end and reviewing what triggered the most
edits during development, three patterns dominate:

1. **Input ambiguity.** The customer's natural-language request, or the
   raw order text, contains words that match more than one menu item or
   omit critical fields. *Examples:* missing size, "dirty chai", "iced
   matcha with vanilla". Mitigation: structured parsing + missing-field
   detection + follow-up question + Review Queue routing.
2. **Missing or weak evidence.** A workflow runs on an out-of-range date,
   a new store with sparse history, or a query that doesn't match any KB
   doc. Mitigation: latest-prior snapshot fallback, `low_sample_size`
   warnings, face_validity weak status with `review` action, evidence
   quality score visible in the UI.
3. **Over-triggered safety / escalation signals.** Especially the
   face-validity false-positive on allergen RAG content (FC-08 above).
   Mitigation: scan only safe signal sources; never rely on stringified
   final_output for keyword detection.

---

## 7. What would improve with more time

These are the honest next steps an actual production deployment would
need to take. None of them are blockers for the Milestone 04 prototype,
but each would close a real gap.

- **More realistic inventory simulation.** The current
  `store_inventory.csv` is a static daily snapshot. A real deployment
  would need streaming updates from POS to handle minute-by-minute
  stock changes.
- **More robust NLP order parsing.** The current regex parser handles
  the common shorthand but doesn't catch all paraphrased orders
  ("oat caramel macc grande iced") or implicit modifiers. A small
  fine-tuned classifier or LLM-assisted parser would improve recall.
- **Deeper RAG evaluation with DeepEval or similar.** The current tests
  verify that the right *documents* are retrieved; they do not verify
  semantic relevance of the matched passages. An LLM-judge eval (which
  requires API keys, hence out of scope here) would close this gap.
- **Persistent review and action history.** Today the audit log lives
  in process memory and clears on restart. A production deployment
  would persist these to a database for cross-session auditing.
- **User studies with baristas and managers.** All time/cost estimates
  in `estimates.md` are reasoned ranges, not measurements. A small user
  study would convert those ranges into measured deltas and let the
  team prioritise improvements that matter to real users.
- **Promotion-name normalisation.** FC-05 (promotion not surfaced
  because of an item-name mismatch across CSVs) is a known gap; a
  promotions name-normaliser would close it.
- **Allergen-flag verification using a structured `Dairy_Free` /
  `Nut_Free` column in the menu CSV** rather than the current
  `Vegan=Yes` heuristic. The current heuristic is documented in
  warnings, but a real safety system would not rely on a proxy.

---

## Appendix: Test files

| File | Purpose |
|---|---|
| `tests/test_mcp_tools.py` | Direct tests of each MCP tool with live data |
| `tests/test_rag_retrieval.py` | RAG index correctness + query scoring |
| `tests/test_brewflow_workflow.py` | Orchestrator end-to-end envelope shape |
| `tests/test_face_validity.py` | Face-validity rule logic + orchestrator integration + RAG-leak regression |
| `tests/test_ui_routes.py` | Flask app routes hit the live orchestrator |
| `tests/results/test_summary.md` | Per-case labelled descriptions |

The `tests/test_workflow.py` file (DeepEval stub) and
`tests/utils/test_connect.py` (OAuth) require API keys and are
intentionally not included in the default suite. They remain in the
repo for future, key-gated runs.
