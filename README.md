# BrewFlow AI

**An AI-supported operations console for cafés and coffee shops** — it chains
deterministic automations, MCP-style tools, RAG retrieval, and AI skills into one
orchestrated workflow that a manager or barista runs before and during a shift.

The system is built to work for any café or coffee-shop concept; the current working
example is modeled on a Starbucks branch, using the public Starbucks menu plus
*simulated* operational data.

> **Simulated data.** This project uses the public Starbucks menu plus *simulated*
> operational CSVs (inventory, staffing, sales forecast, order history, promotions).
> No proprietary Starbucks data is used anywhere in this repo. Swapping in a different
> menu and operational data set adapts it to another café.

---

## About this project

BrewFlow AI started as a team project for a **GenAI for Business** course, which I built
together with my teammates. The original coursework covered the full process redesign:
mapping a coffee shop's daily operations, deciding what an AI coworker should and
shouldn't do, and building the deterministic prototype documented below.

I then **cloned it into my own repository to improve the end-to-end process** — turning
the coursework prototype into a genuinely closed-loop workflow (wiring the AI skills into
the runtime, making human review actually re-drive the workflow, and adding multi-turn
order continuity). See [What I'm improving](#what-im-improving-personal-fork) for the
details.

---

## What BrewFlow AI does

BrewFlow AI runs the three moments where a barista or manager needs fast, evidence-backed
answers during a shift:

1. **Manager readiness** — aggregates inventory status, staffing gaps, rush demand, and
   active promotions into a single pre-shift briefing card.
2. **Barista recommendation** — scores the full menu against a customer's preferences,
   cross-checks live inventory, retrieves relevant policy and training documents, and
   surfaces ranked candidates with reason codes.
3. **Order building and validation** — parses a natural-language order into structured
   fields (size, temperature, milk, syrups, customizations), catches missing fields
   before submission, flags allergy or medical language, and generates a customer
   confirmation with barista prep notes.

Every workflow output ships with a structured **evidence package** (tool outputs,
retrieved documents, warnings, assumptions, audit log) and a **face-validity verdict**,
so a human reviewer can inspect exactly what the AI used before approving. Human approval
is part of the design — the system never moves a customer-facing recommendation or order
forward without an explicit Approve, Edit, Reject + Rerun, or Escalate action.

---

## How it's built

Five cleanly separated layers, all running locally — **no external API calls and no LLM
keys required at runtime.**

```
UI (Flask) → orchestrator.py → { MCP tools · automations · RAG · evidence · face-validity }
```

| Layer | Where | What it does |
|---|---|---|
| **MCP tools** (6) | `mcp_servers/brewflow_mcp_server.py` | Callable Python functions with JSON envelopes: menu info, preference search, inventory, rush, staffing, order parse/validate |
| **Automations** (4) | `automations/*/run_*.py` | Deterministic threshold logic, no LLM — inventory monitoring, staffing gap, demand classification, manager briefing |
| **RAG** | `rag/retrieval.py` → `rag/knowledge_base/*.md` | Deterministic keyword scoring over 12 simulated SOP/policy/training docs — no vector DB |
| **Orchestrator** (4 workflows) | `scripts/orchestrator.py` | Chains everything into `run_manager_readiness / _barista_recommendation / _order_builder / _full_workflow` |
| **Face validity** | `utils/face_validity.py` | Deterministic plausibility verdict attached to every run — status, confidence, anchors, concerns, recommended action |
| **UI** | `ui/app.py` + `ui/templates` / `ui/static` | Flask single-page console: six tabs, live orchestrator calls, in-process audit log and order queue |

---

## How to run

**Prerequisites:** Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync

# Start the web console → open http://127.0.0.1:5000
uv run python ui/app.py

# Run the test suite (95 local, deterministic tests — no API keys)
uv run pytest tests/ -v
```

The console serves the live Flask + Jinja UI against local CSV data. All 95 tests run
offline and deterministically.

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

## Design principles

| Principle | Where it's enforced |
|---|---|
| **Human approval required on every customer-facing output** | `review_required = True` on recommendation and order steps; face-validity returns `needs_review` as the designed state for customer-facing flows |
| **Allergy and medical language always escalates** | Allergy/medical regex in `orchestrator.py` and `face_validity.py`; status forced to `needs_review`, action forced to `escalate` |
| **Drinks prepared individually for quality consistency** | Phrase appears verbatim in every prep note; retrieved from `drink_quality_consistency_sop.md` via RAG; locked in by a regression test |
| **All operational data is simulated** | Stated in the data READMEs and surfaced as a chip in the UI top bar |
| **No external API calls at runtime** | All workflows use local Python + CSVs + Jinja UI; all 95 tests run offline without any keys |
| **Evidence is always visible to the reviewer** | Every run produces an `evidence_package`; the UI Evidence Center surfaces tool outputs, RAG docs (with matched terms and snippets), assumptions, warnings, quality score, and the face-validity card |

---

## What I'm improving (personal fork)

The coursework prototype is deterministic and fully auditable, but a few seams keep it
from being a true closed-loop process. This fork is where I'm closing them:

- **Wire the AI skills into the runtime.** The `skills/*/SKILL.md` definitions describe the
  natural-language synthesis, but the running system currently surfaces raw structured
  data. Adding a thin skill adapter — with the deterministic layer still gating every
  output — turns tool results into the actual customer-facing recommendation and
  confirmation text.
- **Close the review loop.** Today `POST /api/review_action` records the action to the
  audit log but doesn't re-drive the workflow. Making *Reject + Rerun* and *Edit* feed
  corrected input back into the orchestrator makes the human review an actual step in the
  process rather than a logged event.
- **Multi-turn order continuity.** The order builder already asks a follow-up question when
  a field is missing; adding lightweight session state lets the customer's answer flow back
  in and complete the same order.
- **Persistence + measurement.** Moving the in-process audit log and order queue into a
  small store makes review history durable and lets the workflow capture real cycle times —
  turning the project's before/after time estimates into measured results.

---

## Repository layout

```
brewflow-ai/
├── data/raw/            9 simulated operational CSVs (read-only)
├── skills/              5 AI skills (SKILL.md-defined)
├── automations/         4 deterministic Python automations (no LLM)
├── mcp_servers/         6 MCP-style tools with JSON envelopes
├── rag/                 12 simulated SOP/policy/training docs + keyword retrieval
├── scripts/             orchestrator.py — 4 workflow functions exposed to the UI
├── ui/                  Flask app — 7 routes, live orchestrator calls
├── utils/               data loading, menu/inventory matching, evidence, face validity
├── tests/               95 local deterministic tests
└── *.md                 process-design, evidence, estimates, failure-cases, test-report docs
```

---

## Original coursework deliverables

The full process-redesign write-ups from the course are preserved in the repo root:

| Deliverable | File |
|---|---|
| Final process redesign (workflow diagram + explanation) | `ai_process_design.md` |
| Human review and control plan | `human_review_plan.md` |
| Evidence and source use | `evidence_and_sources.md` |
| Time, cost, and quality reasoning | `estimates.md` |
| Face validity explanation | `face_validity.md` |
| Failure cases register | `failure_cases.md` |
| Test report (results, patterns, before/after) | `test_report.md` |

---

*Original team project by Group 8 for MGTA 495 (GenAI for Business, 2026). This fork is
maintained and extended by [@eeshajagdhane](https://github.com/eeshajagdhane).*
