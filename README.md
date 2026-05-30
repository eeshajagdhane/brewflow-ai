# BrewFlow AI — Starbucks Branch Daily Operations and Order Fulfillment

> **Milestone 04 — Group 8 | MGTA 495 GenAI for Business**

BrewFlow AI is a live role-based AI operations console for a simulated Starbucks branch.
All outputs are generated from real CSV data and deterministic logic — **no canned demo responses**.

> ⚠ **Simulated branch prototype.** BrewFlow AI uses the public Starbucks
> menu plus **simulated** operational CSVs (inventory, staffing, sales
> forecast, order history, promotions). **No proprietary Starbucks data
> is used.** All quantitative estimates in this repo are reasoned ranges,
> not company facts.

---

## Milestone 04 Final Deliverables

| # | Deliverable | File |
|---|---|---|
| 1 | Final process redesign + workflow diagram | [`ai_process_design.md`](ai_process_design.md) / [`ai_process_design.pdf`](ai_process_design.pdf) |
| 2 | Human review and control plan (7 workflow steps, explicit approval points) | [`human_review_plan.md`](human_review_plan.md) |
| 3 | Evidence and source use | [`evidence_and_sources.md`](evidence_and_sources.md) |
| 4 | Time, cost, and quality reasoning | [`estimates.md`](estimates.md) |
| 5 | Predicted failure cases (8 cases, test-mapped) | [`failure_cases.md`](failure_cases.md) |
| 6 | Test report + before/after fix | [`test_report.md`](test_report.md) |
| 7 | Face-validity layer | [`face_validity.md`](face_validity.md) |
| 8 | Final presentation outline | [`presentation_slides/final_presentation_outline.md`](presentation_slides/final_presentation_outline.md) |
| 9 | 10-minute demo script | [`presentation_slides/demo_script.md`](presentation_slides/demo_script.md) |

### What was redesigned

BrewFlow AI redesigns the **daily operations + order fulfilment workflow**
of a single coffee-shop branch. The redesigned chain runs:

> Manager pre-rush readiness → barista drink recommendation → order
> building and validation → order confirmation → human review → audit.

### What BrewFlow AI does

- Aggregates inventory, staffing, demand forecast, and active promotions
  into a single pre-shift readiness briefing for the manager.
- Parses natural-language customer requests into preferences and ranks
  menu candidates with inventory-aware scoring and explicit reason codes.
- Parses raw order text into structured fields (size / temperature / milk
  / syrups / customisations), catching missing fields before submission.
- Routes allergy and medical-sensitive language automatically to
  `escalate`, never silently approving customer-facing recommendations.
- Produces an `evidence_package` per run (tool outputs, RAG snippets,
  assumptions, warnings) plus a deterministic `face_validity` verdict.
- Logs every workflow step and every human review action to an audit log.

### What humans still control

- Final approval of any customer-facing recommendation or order.
- Allergen verification (always escalated, never auto-approved).
- Order-text follow-ups when required fields are missing.
- Manager adjustments to staffing or inventory after reviewing the briefing.
- Drink preparation itself — drinks are still prepared individually for
  quality consistency per the retrieved RAG SOP.

### What evidence users can inspect

For every workflow run, the Evidence Center surfaces:

1. **Tool / Data** — every MCP tool / automation call with status
2. **RAG** — retrieved knowledge-base documents with filename, score,
   matched terms, and snippet
3. **Assumptions** — defaults the workflow had to apply
4. **Warnings** — any signal that something is off (stale snapshot,
   dairy-free heuristic, rush risk, allergy language)
5. **Quality + Face Validity** — quality score with label + the face
   validity verdict (status, confidence, anchors, supporting reasons,
   concerns, recommended action)

### What could go wrong + how the process handles it

The complete predicted-failure register lives in
[`failure_cases.md`](failure_cases.md). At a glance:

| Failure mode | Mitigation |
|---|---|
| Item name not resolved | Follow-up question + closest-match candidates surfaced |
| Stale inventory snapshot | Latest-prior fallback + `stale_data` warning + downgraded face validity |
| Dairy-free heuristic miss | Heuristic labelled in warnings; allergen path forces review |
| Sparse demand history | `low_sample_size` warning + forecast as secondary signal |
| Missed promotion | Active promos surfaced separately in manager briefing |
| Customisation drop | Prep notes render every customisation line; review required |
| Inflated evidence score | Matched-term chips visible so reviewers can verify relevance |
| False allergy escalation from RAG content | Fixed: face validity scans only safe signal sources |

---

## What BrewFlow AI Does

| Role | Task | How |
|---|---|---|
| Manager | Pre-rush readiness check | `run_manager_readiness()` → automations + RAG |
| Barista | Inventory-aware drink recommendation | `run_barista_recommendation()` → MCP tools + RAG |
| Customer / Barista | Order building and validation | `run_order_builder()` → `build_and_validate_order` |
| All | Order confirmation | `order_summary` skill → RAG confirmation SOP |
| All | Human review and audit | Evidence package + review queue |

---

## The Connected Workflow

```
Manager Readiness (detect_rush → staffing → inventory → briefing)
         ↓ barista_guidance
Barista Recommendation (search_menu → check_inventory → RAG guidance)
         ↓ top_candidates + selected_item
Order Builder (parse order → validate → missing fields → follow-up)
         ↓ structured_order
Order Summary (customer confirmation + barista prep note)
         ↓
Human Review (evidence_package + review_queue + approve/edit/reject/escalate)
```

---

## What is a Skill vs Automation vs MCP Tool vs RAG Document?

| Component | Where | What it does |
|---|---|---|
| **Skill** | `skills/*/SKILL.md` | AI instruction document — teaches the model how to use tools + evidence to respond to a user. Conversational, judgment-heavy. |
| **Automation** | `automations/*/run_*.py` | Deterministic Python — no LLM. Reads CSVs, calculates thresholds, returns structured data. |
| **MCP Tool** | `mcp_servers/brewflow_mcp_server.py` | Callable Python function with JSON I/O. Bridges automations and menu data for the orchestrator. |
| **RAG Document** | `rag/knowledge_base/*.md` | Simulated internal SOP / policy / training guide. Retrieved by keyword scoring. |

---

## Folder Structure

| Folder | Contents |
|---|---|
| `data/raw/` | 9 finalized CSV files — read only, never modified |
| `utils/` | data_loader, menu_matching, inventory_matching, workflow_common, evidence, **face_validity** (M04) |
| `automations/` | 4 deterministic automations (inventory, staffing, demand, briefing) |
| `mcp_servers/` | brewflow_mcp_server.py (6 tools) + example_server.py (reference) |
| `rag/knowledge_base/` | 12 SOP/policy documents + EXAMPLE.md (reference) |
| `rag/retrieval.py` | Deterministic keyword retrieval — no API keys |
| `skills/` | 5 SKILL.md files (product_catalog, recommendation, order_builder, order_summary, workflow_orchestrator) |
| `scripts/orchestrator.py` | 4 workflow functions returning UI-ready JSON (each carries a `face_validity` object) |
| `tests/` | Local tests — no API keys required |
| `ui/` | **Flask Operations Console (M04)** — `app.py`, `templates/`, `static/`. Six tabs over the live orchestrator. |

> **Face validity (Milestone 04):** Every orchestrator response now includes
> a top-level `face_validity` object — a deterministic, rule-based
> plausibility check assembled from the existing `evidence_package`,
> `review_queue`, `warnings`, and `user_input`. Face validity is an
> evaluation/review layer (lives in `utils/face_validity.py`), **not** a
> skill, MCP tool, or RAG tool. The future UI will render this in the
> Evidence Center and Review Queue. See [`face_validity.md`](face_validity.md).

---

## How to Run the UI (Operations Console)

```bash
uv sync
uv run python ui/app.py            # http://127.0.0.1:5000
```

> **Simulated branch, not real Starbucks operations.** The UI uses the
> public Starbucks menu plus simulated operational CSVs (inventory,
> staffing, sales forecast, orders, promotions). It is not connected to
> any proprietary Starbucks data or system.

The console has six tabs (**Full Workflow** — main demo path — plus
Manager, Barista, Order Builder, Evidence Center, Review Queue) and an
always-visible Audit Log footer. Every workflow call goes live to
`scripts/orchestrator.py`. See [`ui/README.md`](ui/README.md) for full
view-by-view docs.

## How to Run Tests

```bash
uv run pytest tests/test_mcp_tools.py tests/test_rag_retrieval.py \
  tests/test_brewflow_workflow.py tests/test_face_validity.py \
  tests/test_ui_routes.py -v
```

## How to Run the Orchestrator from Python

```python
from scripts.orchestrator import run_manager_readiness, run_full_workflow

# Pre-shift readiness check
result = run_manager_readiness("SD001", "2024-01-15", 8)
print(result["final_output"]["readiness_summary"])
print(result["final_output"]["recommended_actions"])

# Full workflow
result = run_full_workflow(
    store_id="SD001", date="2024-01-15", hour=8,
    customer_request="something cold and sweet",
    raw_order="Grande iced caramel macchiato with oat milk",
    preferences={"temperature": "cold"},
)
print(result["status"], len(result["steps"]))
```

---

## Milestone 02 Coverage

| Deliverable | File |
|---|---|
| product_catalog skill | `skills/product_catalog/SKILL.md` |
| recommendation skill | `skills/recommendation/SKILL.md` |
| order_builder skill | `skills/order_builder/SKILL.md` |
| order_summary skill | `skills/order_summary/SKILL.md` |
| inventory_monitoring automation | `automations/inventory_monitoring/run_inventory_monitoring.py` |
| staffing_gap_calculator automation | `automations/staffing_gap_calculator/run_staffing_gap_calculator.py` |
| demand_rush_detection automation | `automations/demand_rush_detection/run_demand_rush_detection.py` |
| manager_daily_briefing automation | `automations/manager_daily_briefing/run_manager_daily_briefing.py` |

## Milestone 03 Coverage

| Deliverable | File |
|---|---|
| Connected workflow chain | `scripts/orchestrator.py` (4 functions) |
| `get_menu_item_info` MCP tool | `mcp_servers/brewflow_mcp_server.py` |
| `search_menu_by_preferences` MCP tool | `mcp_servers/brewflow_mcp_server.py` |
| `check_inventory_status` MCP tool | `mcp_servers/brewflow_mcp_server.py` |
| `detect_rush_period` MCP tool | `mcp_servers/brewflow_mcp_server.py` |
| `calculate_staffing_gap` MCP tool | `mcp_servers/brewflow_mcp_server.py` |
| `build_and_validate_order` MCP tool | `mcp_servers/brewflow_mcp_server.py` |
| RAG retrieval | `rag/retrieval.py` + 12 docs in `rag/knowledge_base/` |
| Workflow handoffs | `scripts/orchestrator.py::run_full_workflow()` |

---

## Notes

- UI will be built later in `ui/` — not part of this milestone.
- All outputs are generated from live data/functions — no canned demo responses.
- Professor starter examples (`mcp_servers/example_server.py`, `rag/knowledge_base/EXAMPLE.md`,
  `.claude/commands/`) are preserved as reference-only.
- `tests/test_workflow.py` (DeepEval) and `tests/utils/` (OAuth) require API keys — run with `-m integration`.

---

# Milestone 04 — Course Template (Preserved for Reference) It
builds on the Milestone 03 template (skills, MCP tools, RAG) and adds the
pieces specific to M04: a real user interface, an explicit human-review
plan, evidence/source displays, time/cost/quality reasoning, predicted
failure cases, and an automated DeepEval test suite.

Your assignment brief is in [`milestone04.qmd`](milestone04.qmd). The six
graded deliverables are:

1. **Final Process Redesign** — updated workflow diagram + 1–2 page explanation.
2. **Human Review and Control Plan** — table covering ≥6 process steps.
3. **User Interface** — at least 4 screens (start, AI work, evidence, review).
4. **Evidence and Source Use** — how RAG/tool output is shown to the user.
5. **Time, Cost, and Quality Reasoning** — before/after estimates with assumptions.
6. **Testing AI Performance** — 5+ predicted failures + 8–12 DeepEval test cases with results.

A final presentation pulls these together on **June 4**. There is also a
**May 28 checkpoint** for the RAG + current UI.

---

## Setup

```bash
uv sync                                       # installs deps into .venv (incl. deepeval)
cp .env.example .env && $EDITOR .env          # add TRITONAI_API_KEY
bash install.sh                               # registers skills with Claude Code
                                              #   (run again after you add a skill)
```

If you also want the MCP example to be invokable from Claude Code:

```bash
uv run mcp dev mcp_servers/example_server.py  # opens the MCP inspector
```

`uv run pytest` should pass on a fresh clone.

---

## Folder map

| Folder | What lives here |
| --- | --- |
| [`skills/`](skills/README.md) | LLM-based skills (one folder per skill; each has `SKILL.md` + `scripts/`) |
| [`automations/`](automations/README.md) | Deterministic Python steps (no LLM); same CLI contract as skills |
| [`mcp_servers/`](mcp_servers/README.md) | MCP servers that expose your skills + data as tools |
| [`rag/`](rag/README.md) | Proprietary knowledge base + retrieval code |
| [`ui/`](ui/README.md) | User interface for the workflow (≥4 screens) — **new in M04** |
| [`scripts/`](scripts/README.md) | Orchestrator + glue scripts |
| [`utils/`](utils/README.md) | Shared helpers (`connect.py` for LLM calls is already here) |
| [`data/`](data/README.md) | `raw/`, `processed/`, `working/`, `dictionaries/` data folders |
| [`tests/`](tests/README.md) | pytest + **DeepEval** test cases for AI performance — extended in M04 |
| [`presentation_slides/`](presentation_slides/README.md) | Final presentation materials — **new in M04** |

Top-level deliverable documents (fill these in):

- [`human_review_plan.md`](human_review_plan.md) — table of human review/control points
- [`evidence_and_sources.md`](evidence_and_sources.md) — how data/documents/tools are shown
- [`estimates.md`](estimates.md) — time, cost, and quality assumptions
- [`failure_cases.md`](failure_cases.md) — predicted failures and process handling
- [`test_report.md`](test_report.md) — DeepEval results, failure patterns, before/after

Add your workflow diagram as `ai_process_design.pdf` at the repo root.

Top-level files you should not need to edit:

- `install.sh` — auto-discovers every `skills/*/SKILL.md` and symlinks it into `.claude/skills/`
- `conftest.py` — loads `.env` before pytest collects
- `.env.example` — copy to `.env` and add your key
- `pyproject.toml` — uv-managed dependencies; add to it with `uv add <pkg>`
- `.mcp.json` — registers your MCP servers with Claude Code

---

## What's new in M04 (vs M03)

M03 gave you a working orchestrator with skills, MCP tools, and RAG. M04
asks: *if a real person used this every day, what would the interaction
look like, and how would you know it was working?* That breaks into four
new pieces of work:

### 1. A real UI (`ui/`)

The orchestrator's CLI is not enough. Build at least four screens:

1. **Start screen** (carried from M03, refined) — operator selects/enters the case.
2. **AI work screen** (carried from M03, refined) — operator watches the AI produce output.
3. **Evidence screen** (new) — structured display of retrieved docs, tool output, data rows.
4. **Review screen** (new) — approve / edit / reject / rerun / escalate, with each action wired to a real outcome.

See [`ui/README.md`](ui/README.md) for tool suggestions and the screen contract.

### 2. Human review plan (`human_review_plan.md`)

A table that names ≥6 workflow steps, what the AI does, what the human
does, whether approval is required, what could go wrong, and what happens
when it does. At least 1–2 rows must be explicit review/approval points.

### 3. Evidence and source use (`evidence_and_sources.md`)

A short doc explaining what data/documents/tools the AI uses, how the user
sees the evidence, and what happens when evidence is missing or weak.

### 4. Time, cost, and quality estimates (`estimates.md`)

Two tables: a per-step before/after time table (≥5 rows) and a summary
table. Use **reasoned assumptions and ranges** — not invented company data.

### 5. Failure cases + DeepEval tests (`failure_cases.md`, `tests/`, `test_report.md`)

- List **≥5 realistic failure cases** with consequence and handling.
- Build a **DeepEval test set of 8–12 cases**, run it, and write up the
  results, the 3 most common failure patterns, and one before/after fix.

See [`tests/README.md`](tests/README.md) for the DeepEval starter and
[`tests/test_workflow.py`](tests/test_workflow.py) for a runnable example.

---

## Timeline

- **May 28 (checkpoint):** RAG + current UI demo. Two teams selected to share.
- **June 4 (final):** All deliverables + final presentation. Push to GitHub before class.

---

## Before you submit

- [ ] Workflow diagram + 1–2 page explanation in `ai_process_design.pdf`.
- [ ] `human_review_plan.md` covers ≥6 steps with ≥1–2 review points.
- [ ] `ui/` has at least 4 working screens.
- [ ] `evidence_and_sources.md` answers all 5 questions in the brief.
- [ ] `estimates.md` has the per-step table (≥5 rows) and the summary table.
- [ ] `failure_cases.md` lists ≥5 realistic failures.
- [ ] `tests/test_workflow.py` runs 8–12 DeepEval cases and writes results to `tests/results/`.
- [ ] `test_report.md` summarizes results, top-3 failure patterns, and one before/after fix.
- [ ] `uv run pytest` is green.
- [ ] `presentation_slides/` contains the final deck.

---

## Reading the reference repo

The `customer-ticket-process/` reference repo your instructor shared is
still the worked example for skills, MCP, RAG, and the orchestrator. M04
adds new pieces (UI, review plan, estimates, DeepEval) that are
project-specific — there is no reference to copy from. Start small,
make it work, then make it better.
