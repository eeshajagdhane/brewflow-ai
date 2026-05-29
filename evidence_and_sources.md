# Evidence and Source Use

## 1. What data does the AI use?

All structured data is read from `data/raw/` (read-only CSVs). No external API calls, no database.

| File | Used by | Purpose |
|---|---|---|
| `starbucks_menu_full.csv` | menu_matching, MCP tools | Full product catalog — name, category, size, calories, caffeine, allergens, modifiers |
| `store_inventory.csv` | inventory_matching, run_inventory_monitoring | Per-store ingredient stock levels and status (Healthy / Low / Critical Low / Overstocked) |
| `ingredient_mapping.csv` | inventory_matching | Maps menu ingredient names to inventory column names; marks 14 items as "not_tracked" |
| `item_name_mapping.csv` | menu_matching | 33 canonical ↔ source-name mappings for resolving natural-language order text |
| `order_history.csv` | demand_rush_detection | Historical hourly order counts per store — drives rush/moderate/low demand classification |
| `staff_schedule.csv` | staffing_gap_calculator | Scheduled shifts per store per date — used to compute active headcount vs. required |
| `daily_sales_forecast.csv` | demand_rush_detection | Daily volume forecasts; provides expected demand level as a cross-check |
| `promotion_margins.csv` | manager_daily_briefing | Active promotions by date — promotions surface in barista guidance and menu scoring |
| `demo_scenarios.csv` | tests only | Pre-built test scenarios; not used in production workflow |

All loads go through `utils/data_loader.py`. The loader validates all 9 required files at startup via `validate_required_data_files()`.

## 2. What documents does the AI use?

12 simulated internal knowledge-base documents live in `rag/knowledge_base/`. They represent the policies, SOPs, and training guides an employee would consult during a shift.

| Document | Type | Retrieved for |
|---|---|---|
| `barista_recommendation_guidelines.md` | Training guide | Barista drink recommendation |
| `customization_policy.md` | Policy | Order builder (modifier validation) |
| `inventory_substitution_sop.md` | SOP | Manager readiness, order builder (when stock is low) |
| `rush_hour_service_playbook.md` | Playbook | Manager readiness, barista recommendation during rush |
| `manager_pre_shift_checklist.md` | Checklist | Manager readiness briefing |
| `promotion_decision_policy.md` | Policy | Manager readiness (promotion surfacing) |
| `new_barista_menu_training_guide.md` | Training | Product catalog, barista recommendation |
| `order_confirmation_standard.md` | SOP | Order builder, order summary |
| `dietary_allergen_guidance.md` | Policy | Recommendation, order builder (allergy detection) |
| `drink_quality_consistency_sop.md` | SOP | Order builder, order summary (preparation notes) |
| `service_recovery_policy.md` | Policy | Recommendation, order summary (complaint handling) |
| `post_rush_manager_review_template.md` | Template | Manager readiness (post-rush reporting) |

Retrieval is performed by `rag/retrieval.py` using deterministic keyword scoring — no vector DB, no API keys. `EXAMPLE.md` is excluded from production retrieval.

## 3. What tools or Python functions does the AI use?

**MCP tools** (`mcp_servers/brewflow_mcp_server.py`):

| Tool | What it does |
|---|---|
| `get_menu_item_info(item_name)` | Returns full menu details for a named item — calories, modifiers, allergens |
| `search_menu_by_preferences(preferences, store_id, date, hour)` | Scores and ranks menu items against user preferences (temperature, caffeine, calories, dietary, flavor) |
| `check_inventory_status(store_id, date, ingredients)` | Returns availability status for a list of ingredients on a given date |
| `detect_rush_period(store_id, date, hour)` | Returns demand level, risk level, and barista guidance for a given hour |
| `calculate_staffing_gap(store_id, date, hour)` | Returns scheduled vs. required headcount and staffing status |
| `build_and_validate_order(raw_order, store_id, date)` | Parses natural-language order text, resolves item name, validates inventory, flags allergens |

**Deterministic automations** (`automations/`):

| Automation | What it does |
|---|---|
| `run_inventory_monitoring(store_id, date)` | Counts low/critical/overstock/healthy ingredients; returns items needing attention |
| `run_staffing_gap_calculator(store_id, date, hour)` | Computes scheduled headcount for the given hour; compares to baseline requirement |
| `run_demand_rush_detection(store_id, date, hour)` | Classifies hour as rush/moderate/low from order history and forecast |
| `run_manager_daily_briefing(store_id, date, hour)` | Combines all three automations into a structured manager briefing with barista guidance |

**Shared utilities** (`utils/`):

| Module | What it does |
|---|---|
| `data_loader.py` | Loads and validates all 9 raw CSVs |
| `menu_matching.py` | Resolves natural-language item names to canonical menu entries |
| `inventory_matching.py` | Maps menu ingredients to inventory rows; applies latest-prior snapshot fallback |
| `workflow_common.py` | Builds workflow step envelopes, audit entries, and tool response wrappers |
| `evidence.py` | Assembles evidence packages, scores evidence quality, generates review summaries |

## 4. How does the user see the evidence?

The orchestrator (`scripts/orchestrator.py`) returns a structured `evidence_package` alongside every workflow result. The evidence package contains:

- **RAG documents**: each retrieved doc shows `filename`, `title`, `section_heading`, `snippet` (first 400 chars), `score`, and `matched_terms`. Users can see exactly which policy or SOP grounded the AI's recommendation.
- **Tool outputs**: each MCP tool call is logged as a workflow step with `tool_name`, `inputs`, and the full structured result. Inventory status, demand level, staffing gap, and menu candidates are all visible.
- **Audit log**: every automation and tool call is recorded in `audit_log` with timestamp, role, action, and status.
- **Review queue**: items flagged for human review appear in `review_queue` with risk level and a one-line reason.
- **Evidence quality score**: `evidence.py` computes a 0.0–1.0 quality score based on the number of sources, RAG coverage, and tool confirmation. A score below 0.4 triggers a `low_evidence_quality` warning.

The planned UI Evidence screen (M04) will render this JSON as:
- A collapsible panel per RAG doc with highlighted matched terms
- A table of tool outputs (inventory rows, staffing numbers, demand level)
- A color-coded quality badge (green ≥ 0.7, yellow 0.4–0.7, red < 0.4)
- A "Show source" link beside each AI claim pointing to the doc or CSV row

## 5. What happens if the evidence is missing, weak, or conflicting?

| Scenario | Detection | Response |
|---|---|---|
| No inventory snapshot for requested date | `get_inventory_snapshot()` finds no row with date ≤ requested_date | Returns `{"status": "no_data"}` + warning; order builder blocks on `review_required=True` |
| RAG retrieval returns no documents (score = 0 for all) | `retrieve_internal_knowledge()` detects all-zero scores | Returns empty list + appends `"weak_evidence: no knowledge base documents matched"` warning to workflow output |
| Ingredient not tracked in inventory | `ingredient_mapping.csv` `inventory_col = "not_tracked"` | Treated as non-blocking; included in evidence with `availability: "not_tracked"` note |
| Item name cannot be resolved | `resolve_item_name()` returns `no_match` after all 4 resolution steps | Order builder sets `item_resolved = False`, surfaces `missing_fields = ["item_name"]`, requires human follow-up |
| Evidence quality score < 0.4 | `evidence_quality_score()` in `evidence.py` | `review_required = True` automatically; `review_queue` entry added with reason `low_evidence_quality` |
| Conflicting inventory signals (Low status but quantity > threshold) | Both status string and quantity checked in `classify_inventory_status()` | Status string from CSV takes precedence; quantity displayed in evidence for human verification |
| Barista recommendation has no in-stock candidates | `search_menu_by_preferences()` scores all items but all have unavailable ingredients | Returns top candidates with `inventory_warning` flag set; `review_required = True` on the recommendation step |
