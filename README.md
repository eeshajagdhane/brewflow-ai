# BrewFlow AI

An operations console for cafés and coffee shops. It chains deterministic
automations, callable tools, RAG retrieval, and a human review step into one
workflow a manager or barista can run before and during a shift.

The current working example uses the public Starbucks menu plus *simulated*
operational data. No proprietary Starbucks data is in this repository.

---

## How it was built

The system was stacked in four layers. Each one sits on the last.

1. **Plan and data** — map the shift, decide what an AI coworker may not do,
   and invent the simulated store CSVs (inventory, staffing, sales forecast,
   order history, promotions).
2. **Skills** — write the contracts: when to recommend a drink, how to parse
   an order, what a confirmation must say. These live as `skills/*/SKILL.md`.
3. **Tools and RAG** — make those steps callable (menu, inventory, rush,
   staffing, order parse/validate) and ground them in twelve SOP and policy
   documents.
4. **Console** — a Flask UI over the orchestrator so a human can see the
   evidence and approve, edit, reject, or escalate before anything reaches
   a customer.

The running path is layers 3 and 4: MCP-style tools, automations, RAG, and
the orchestrator. The skill files are the contracts from layer 2. They
describe the spoken recommendation and confirmation; the console currently
surfaces the structured tool output those skills would consume.

Built with teammates. This repository is maintained by
[@eeshajagdhane](https://github.com/eeshajagdhane).

---

## What it does

1. **Manager readiness** — inventory status, staffing gaps, rush demand, and
   active promotions in one pre-shift briefing.
2. **Barista recommendation** — scores the menu against a customer's
   preferences, cross-checks live inventory, retrieves policy docs, and
   returns ranked candidates with reason codes.
3. **Order building** — parses a natural-language order, catches missing
   fields, flags allergy or medical language, and generates a confirmation
   with barista prep notes.

Every run ships an **evidence package** and a **face-validity verdict**.
Customer-facing recommendations and orders do not move forward without an
explicit Approve, Edit, Reject + Rerun, or Escalate action.

---

## How it's wired

Five layers, all local. No external API calls and no LLM keys at runtime.

```
UI (Flask) → orchestrator.py → { tools · automations · RAG · evidence · face-validity }
```

| Layer | Where | What it does |
|---|---|---|
| **Tools** (6) | `mcp_servers/brewflow_mcp_server.py` | Menu info, preference search, inventory, rush, staffing, order parse/validate |
| **Automations** (4) | `automations/*/run_*.py` | Deterministic threshold logic — inventory, staffing, demand, manager briefing |
| **RAG** | `rag/retrieval.py` → `rag/knowledge_base/*.md` | Keyword scoring over 12 simulated SOP/policy/training docs |
| **Orchestrator** | `scripts/orchestrator.py` | `run_manager_readiness` / `_barista_recommendation` / `_order_builder` / `_full_workflow` |
| **Face validity** | `utils/face_validity.py` | Plausibility verdict on every run — status, confidence, anchors, concerns |
| **UI** | `ui/app.py` | Flask console: six tabs, live orchestrator calls, in-process audit log |

---

## How to run

**Prerequisites:** Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python ui/app.py          # http://127.0.0.1:5000
uv run pytest tests/ -v          # 95 local tests, no API keys
```

---

## Design rules

| Rule | Where it's enforced |
|---|---|
| Human approval on every customer-facing output | `review_required = True` on recommendation and order steps |
| Allergy and medical language always escalates | Regex in `orchestrator.py` and `face_validity.py` |
| The detector does not scan the handbook | Face validity reads the customer's words, warnings, and review labels — not RAG filenames |
| Drinks prepared individually | Phrase locked into every prep note; covered by a regression test |
| Operational data is simulated | Data READMEs and a chip in the UI top bar |
| No external API calls at runtime | Local Python + CSVs + Jinja; tests run offline |

---

## A seam that mattered

The allergy detector originally scanned the whole workflow output. The
handbook file `dietary_allergen_guidance.md` contains the word *allergen*,
so a benign dairy-free request was treated as a medical emergency. The
detector now reads only the customer's words, warnings, and review-queue
labels. Real allergy language still escalates. The handbook does not.

Reject + Rerun currently records the action in the audit log. It does not
yet feed a corrected input back into the orchestrator.

---

## Repository layout

```
brewflow-ai/
├── data/raw/            simulated operational CSVs (read-only)
├── skills/              skill contracts (SKILL.md)
├── automations/         deterministic Python automations
├── mcp_servers/         callable tools with JSON envelopes
├── rag/                 SOP/policy docs + keyword retrieval
├── scripts/             orchestrator
├── ui/                  Flask console
├── utils/               matching, evidence, face validity
└── tests/               95 local deterministic tests
```
