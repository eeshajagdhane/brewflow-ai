# BrewFlow AI — Milestone 04

**Project:** BrewFlow AI: Starbucks Branch Daily Operations and Order Fulfillment
**Course:** MGTA 495 GenAI for Business, Spring 2026
**Team:** Group 8

> **Simulated branch prototype.**
> This project uses the public Starbucks menu plus *simulated* operational
> CSVs (inventory, staffing, sales forecast, order history, promotions).
> No proprietary Starbucks data is used anywhere in this repo.

---

## What BrewFlow AI does

BrewFlow AI is an AI-supported operations console for a simulated Starbucks
branch. It chains **deterministic automations**, **MCP-style tools**, **RAG
retrieval**, and **AI skills** into one orchestrated workflow that a manager
or barista runs before and during a shift:

1. **Manager readiness** — aggregates inventory status, staffing gaps, rush
   demand, and active promotions into a single pre-shift briefing card.
2. **Barista recommendation** — scores the full menu against a customer's
   preferences, cross-checks live inventory, retrieves relevant policy and
   training documents, and surfaces ranked candidates with reason codes.
3. **Order building and validation** — parses a natural-language order into
   structured fields (size, temperature, milk, syrups, customizations),
   catches missing fields before submission, flags allergy or medical
   language, and generates a customer confirmation with barista prep notes.

Every workflow output ships with a structured **evidence package** (tool
outputs, retrieved documents, warnings, assumptions, audit log) and a
**face-validity verdict** so the human reviewer can inspect what the AI used
before approving.

Human approval is part of the designed process — the system never moves a
customer-facing recommendation or order to the next step without an explicit
Approve, Edit, Reject + Rerun, or Escalate action from a barista or manager.

---

## How to run

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (package manager used throughout this repo)

### Install dependencies

```bash
uv sync
```

### Start the web console

```bash
uv run python ui/app.py
```

Open `http://127.0.0.1:5000` in any browser. The console serves the live
Flask + Jinja UI against local CSV data — no external API calls and no LLM
keys required.

### Run the test suite

```bash
uv run pytest tests/test_mcp_tools.py tests/test_rag_retrieval.py \
              tests/test_brewflow_workflow.py tests/test_face_validity.py \
              tests/test_ui_routes.py -v
```

All 95 tests are local and deterministic. They pass without API keys.

### Install skills into Claude Code

```bash
bash install.sh
```

This symlinks every `skills/*/SKILL.md` into `.claude/skills/` so Claude
Code can load them. Restart your Claude Code session after running.

---

## Repository structure

```
mgta495-milestone04-Group-8/
│
├── data/
│   └── raw/                          9 simulated operational CSVs (read-only)
│       ├── starbucks_menu_full.csv   Public Starbucks menu catalog
│       ├── store_inventory.csv       Per-store ingredient stock levels
│       ├── ingredient_mapping.csv    Menu ingredient → inventory column map
│       ├── item_name_mapping.csv     Natural-language → canonical item names
│       ├── order_history.csv         Historical hourly order counts per store
│       ├── staff_schedule.csv        Scheduled shifts per store per date
│       ├── daily_sales_forecast.csv  Daily volume forecasts per store
│       ├── promotion_margins.csv     Active promotions by store and date
│       └── demo_scenarios.csv        Pre-built test scenarios (tests only)
│
├── skills/                           5 AI skills (SKILL.md-defined)
│   ├── recommendation/               Ranks and explains drink recommendations
│   ├── order_builder/                Parses and validates natural-language orders
│   ├── order_summary/                Generates customer confirmation + prep notes
│   ├── product_catalog/              Answers menu and product questions
│   └── workflow_orchestrator/        Chains the end-to-end workflow
│
├── automations/                      4 deterministic Python automations (no LLM)
│   ├── inventory_monitoring/         Classifies ingredient stock by alert level
│   ├── staffing_gap_calculator/      Computes scheduled vs. required headcount
│   ├── demand_rush_detection/        Classifies demand: low / moderate / high / very high
│   └── manager_daily_briefing/       Combines all three into a pre-shift briefing
│
├── mcp_servers/
│   └── brewflow_mcp_server.py        6 MCP-style tools with JSON envelopes:
│                                       get_menu_item_info
│                                       search_menu_by_preferences
│                                       check_inventory_status
│                                       detect_rush_period
│                                       calculate_staffing_gap
│                                       build_and_validate_order
│
├── rag/
│   ├── knowledge_base/               12 simulated internal SOP / policy / training docs
│   │   ├── barista_recommendation_guidelines.md
│   │   ├── customization_policy.md
│   │   ├── dietary_allergen_guidance.md
│   │   ├── drink_quality_consistency_sop.md
│   │   ├── inventory_substitution_sop.md
│   │   ├── manager_pre_shift_checklist.md
│   │   ├── new_barista_menu_training_guide.md
│   │   ├── order_confirmation_standard.md
│   │   ├── post_rush_manager_review_template.md
│   │   ├── promotion_decision_policy.md
│   │   ├── rush_hour_service_playbook.md
│   │   └── service_recovery_policy.md
│   └── retrieval.py                  Deterministic keyword-scoring retrieval (no vector DB,
│                                     no API keys)
│
├── scripts/
│   └── orchestrator.py               4 workflow functions exposed to the UI:
│                                       run_manager_readiness()
│                                       run_barista_recommendation()
│                                       run_order_builder()
│                                       run_full_workflow()
│
├── ui/
│   ├── app.py                        Flask app — 7 routes, live orchestrator calls
│   ├── templates/                    Jinja2 HTML templates
│   └── static/                       CSS + vanilla JS (no framework, no build step)
│
├── utils/                            Shared Python helpers
│   ├── data_loader.py                Loads and validates all 9 required CSVs at startup
│   ├── menu_matching.py              Resolves natural-language item names to catalog entries
│   ├── inventory_matching.py         Maps menu ingredients to inventory rows
│   ├── workflow_common.py            Builds workflow envelopes, audit entries, tool wrappers
│   ├── evidence.py                   Assembles evidence packages and quality scores
│   └── face_validity.py              Deterministic plausibility check on every workflow output
│
├── tests/
│   ├── test_mcp_tools.py             27 tests — all 6 MCP tools + data file existence
│   ├── test_rag_retrieval.py         16 tests — RAG index, query scoring, doc exclusion
│   ├── test_brewflow_workflow.py     23 tests — orchestrator envelope shape end-to-end
│   ├── test_face_validity.py         15 tests — face-validity rules + RAG-leak regression
│   ├── test_ui_routes.py             14 tests — Flask routes hit the live orchestrator
│   └── results/                      Per-case test descriptions and run output
│
├── ai_process_design.md              Final process redesign — Mermaid workflow diagram +
│                                     full explanation of what changed, what AI does,
│                                     what humans control, and what the system needs
├── ai_process_design.pdf             Printable version of the above
├── human_review_plan.md              Human review and control table (7 workflow steps,
│                                     3 explicit approval points, UI action mapping)
├── evidence_and_sources.md           How data, documents, and tools are shown to the user;
│                                     what happens when evidence is missing or weak
├── estimates.md                      Before/after time, cost, and quality reasoning
│                                     (reasoned ranges, not company facts)
├── face_validity.md                  How the deterministic face-validity layer works,
│                                     what triggers needs_review, and its limitations
├── failure_cases.md                  8 predicted failure modes with test coverage and
│                                     safety nets; includes the documented FC-08 fix
├── test_report.md                    95-test results table, 3 failure patterns, 2 concrete
│                                     before/after improvements, honest gaps
├── install.sh                        Symlinks skills into .claude/skills/ for Claude Code
└── pyproject.toml / uv.lock          Python project config and locked dependencies
```

---

## What each component type does

| Component | Where | What it does |
|---|---|---|
| **AI skill** | `skills/*/SKILL.md` | Natural-language generation — teaches the model how to use tools and evidence to respond. Used for recommendation drafts, order summaries, and confirmation messages. |
| **Automation** | `automations/*/run_*.py` | Deterministic Python with no LLM. Reads CSVs, applies threshold logic, returns structured data. Used for inventory monitoring, staffing gap calculation, and demand classification. |
| **MCP tool** | `mcp_servers/brewflow_mcp_server.py` | Callable Python function with JSON I/O. Bridges automations and menu data for the orchestrator. |
| **RAG document** | `rag/knowledge_base/*.md` | Simulated internal SOP / policy / training guide. Retrieved by deterministic keyword scoring — no vector DB, no API keys. |
| **Face validity** | `utils/face_validity.py` | Deterministic plausibility check assembled from the evidence package, review queue, warnings, and user input. Not an LLM judge. Returns a structured verdict used by the UI Evidence Center and Review Queue. |

---

## Workflow-to-component map

| Workflow step | Component type | File / name |
|---|---|---|
| Inventory status and alerts | Automation + MCP tool | `automations/inventory_monitoring/`, `brewflow_mcp_server.py · check_inventory_status` |
| Staffing gap calculation | Automation + MCP tool | `automations/staffing_gap_calculator/`, `brewflow_mcp_server.py · calculate_staffing_gap` |
| Rush / demand detection | Automation + MCP tool | `automations/demand_rush_detection/`, `brewflow_mcp_server.py · detect_rush_period` |
| Manager pre-shift briefing | Automation (orchestrates the three above) | `automations/manager_daily_briefing/` |
| Menu scoring against preferences | MCP tool | `brewflow_mcp_server.py · search_menu_by_preferences` |
| Drink recommendation (natural language) | AI skill | `skills/recommendation/SKILL.md` |
| Order parsing and validation | MCP tool | `brewflow_mcp_server.py · build_and_validate_order` |
| Order confirmation and prep notes | AI skill | `skills/order_summary/SKILL.md` |
| Policy / SOP / training retrieval | RAG | `rag/retrieval.py` → `rag/knowledge_base/*.md` |
| Evidence assembly and quality scoring | Utility | `utils/evidence.py` |
| Plausibility check on every run | Utility | `utils/face_validity.py` |
| End-to-end workflow orchestration | Orchestrator | `scripts/orchestrator.py` |
| Human review and audit trail | UI + orchestrator | `ui/app.py` → `POST /api/review_action`, `GET /api/audit_log` |

---

## The connected workflow

```
Manager Readiness
  detect_rush_period → calculate_staffing_gap → check_inventory_status
  → run_manager_daily_briefing → RAG (checklist, playbook, promotions)
         ↓ barista_guidance

Barista Recommendation
  search_menu_by_preferences → check_inventory_status
  → RAG (recommendation guidelines, allergen guidance, rush playbook)
  → recommendation skill
         ↓ top_candidates + selected_item

Order Builder
  build_and_validate_order → check_inventory_status
  → RAG (customization policy, order confirmation standard, quality SOP)
  → order_summary skill
         ↓ structured_order + prep_notes

Human Review
  evidence_package + face_validity + review_queue
  → Approve / Edit / Reject + Rerun / Escalate
         ↓

Audit Log (every step + every human action recorded)
```

---

## Key design principles

| Principle | Where it is enforced |
|---|---|
| **Human approval is required on every customer-facing output** | `review_required = True` always set on recommendation and order steps; face-validity returns `needs_review` as the designed state for customer-facing flows |
| **Allergy and medical language always escalates** | `_ALLERGY_RE` in `orchestrator.py` + `_ALLERGY_PATTERN` / `_MEDICAL_PATTERN` in `face_validity.py`; status forced to `needs_review`, action forced to `escalate` |
| **Drinks are prepared individually for quality consistency** | Phrase appears verbatim in every prep note; retrieved from `drink_quality_consistency_sop.md` via RAG; asserted by `test_order_builder_prep_notes_include_individually` |
| **All operational data is simulated** | Stated in data README files; simulated-data chip visible in UI top bar; called out in every deliverable document |
| **No external API calls at runtime** | All workflows use local Python + CSVs + Jinja UI; all 95 tests run offline without any keys |
| **Evidence is always visible to the reviewer** | Every run produces an `evidence_package`; the UI Evidence Center surfaces tool outputs, RAG docs (with matched terms and snippets), assumptions, warnings, quality score, and face-validity card |

---

## User interface

The UI is a single-page Flask + Jinja + vanilla JS app with six tabs and an
always-visible Audit Log footer. No frontend framework. No build step.

| Tab | What it does |
|---|---|
| **Full Workflow** *(default — main demo path)* | Chains all three workflows: manager readiness → barista recommendation → order builder. Includes quick-start buttons that pre-fill the form. |
| **Manager View** | Pre-shift readiness check — rush risk, staffing status, inventory alerts, barista guidance, recommended actions. |
| **Barista View** | Drink recommendation — ranked candidates with reason codes, inventory cautions, RAG guidance, allergy flag if detected. |
| **Order Builder** | Order parsing and validation — structured fields, missing-field detection, follow-up question, prep notes. |
| **Evidence Center** | Five sub-tabs: Tool / Data outputs, RAG documents (with matched terms and snippets), Assumptions, Warnings, and Quality + Face Validity. |
| **Review Queue** | All items flagged for human review with filter chips (All / Pending / Approved / Escalated) and four action buttons: Approve, Edit, Reject + Rerun, Escalate. |
| **Audit Log** | Collapsible footer drawer — combines orchestrator audit entries and UI-side review actions. Every click is logged. |

---

## How to use the orchestrator from Python

```python
from scripts.orchestrator import run_manager_readiness, run_full_workflow

# Pre-shift readiness check
result = run_manager_readiness("SD001", "2024-01-15", 8)
print(result["final_output"]["readiness_summary"])
print(result["final_output"]["recommended_actions"])

# Full end-to-end workflow
result = run_full_workflow(
    store_id="SD001",
    date="2024-01-15",
    hour=8,
    customer_request="something cold and sweet",
    raw_order="Grande iced caramel macchiato with oat milk",
    preferences={"temperature": "cold"},
)
print(result["status"], len(result["steps"]))
```

---

## Milestone 04 deliverables index

| Deliverable | File |
|---|---|
| Final process redesign (workflow diagram + explanation) | [`ai_process_design.md`](ai_process_design.md) / [`ai_process_design.pdf`](ai_process_design.pdf) |
| Human review and control plan | [`human_review_plan.md`](human_review_plan.md) |
| User interface | [`ui/`](ui/) — run with `uv run python ui/app.py` |
| Evidence and source use | [`evidence_and_sources.md`](evidence_and_sources.md) |
| Time, cost, and quality reasoning | [`estimates.md`](estimates.md) |
| Face validity explanation | [`face_validity.md`](face_validity.md) |
| Failure cases register | [`failure_cases.md`](failure_cases.md) |
| Test report (results, patterns, before/after) | [`test_report.md`](test_report.md) |
| Test files | [`tests/`](tests/) |

---

## Answering the grader questions

**What business process did the team redesign?**
Daily operations and order fulfillment at a simulated Starbucks branch —
specifically the manager's pre-shift readiness check, the barista's drink
recommendation conversation, and the order validation and confirmation flow.

**What does the AI coworker actually do?**
It runs inventory, staffing, and demand lookups; retrieves relevant internal
SOPs and training guides; scores and ranks menu items against customer
preferences; parses natural-language orders into structured fields; and
generates a customer-facing confirmation with barista prep notes. All
natural-language synthesis is performed by the AI skills in `skills/`.

**What does the human still control?**
Every customer-facing recommendation requires a barista Approve, Edit,
Reject + Rerun, or Escalate action before delivery. Allergy or medical
language always routes to escalate — the human verifies against the physical
ingredient label before serving. Order finalisation is always a human action.
Drink preparation is always done individually by the barista.

**What evidence can the human inspect?**
The Evidence Center surfaces: each MCP tool's structured output, every
retrieved RAG document (filename, title, snippet, matched terms, score),
assumptions the workflow made, warnings it raised, and a face-validity card
with status, confidence, anchors, supporting reasons, concerns, and
recommended action.

**What could go wrong, and how is it handled?**
See [`failure_cases.md`](failure_cases.md) for the full 8-case register. The
most significant fix made during development: the face-validity layer used to
falsely escalate benign requests because retrieved RAG docs (e.g.
`dietary_allergen_guidance.md`) contained the word "allergen". Fixed by
scanning only safe signal sources (`user_input`, `warnings`, `review_queue`
labels) and not the stringified final output. Two regression tests now lock
this in.

**What improvement does the team expect, based on stated assumptions?**
Using a $25–$35/hour educational labour assumption and reasoned time ranges,
we estimate total per-case elapsed time drops from 33–72 minutes (analogue)
to 15–34 minutes (AI-supported) — a plausible 30–55% reduction in lookup-
heavy phases. Human review time is preserved by design and partially
increases. See [`estimates.md`](estimates.md) for the full step-by-step
breakdown and honest gaps.

**Why are the analysis and AI results plausible in the real-world context?**
The largest time reductions are in the most lookup-heavy steps (manager
readiness, post-rush review). Steps that are conversation-bound (customer
intake) or safety-critical (allergen handling) show little or no reduction.
Cost estimates use explicitly stated educational assumptions with no claim
about real Starbucks costs. No claim is made about drink prep speed, allergen
incident rates, or customer satisfaction — those would require real-world
data. See [`face_validity.md`](face_validity.md) for the full plausibility
argument.

**How did the team test the prototype, and what did the tests reveal?**
95 local deterministic tests (no API keys). Three dominant failure patterns
surfaced: input ambiguity (missing fields, fuzzy item names), missing or weak
evidence (out-of-range dates, sparse history), and over-triggered safety
signals (the RAG-content false escalation). Both headline failure patterns
drove concrete fixes that are now locked in by regression tests. See
[`test_report.md`](test_report.md) for the full results table, before/after
comparisons, and honest gaps.
