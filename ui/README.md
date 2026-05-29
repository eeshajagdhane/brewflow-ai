# `ui/` — BrewFlow AI Operations Console

> **Milestone 04 prototype interface.**
> Built with Flask + Jinja2 + vanilla JS.
> Every workflow call goes live to `scripts/orchestrator.py` — there are
> **no canned outputs, no mocked data, and no external API calls**.

> ⚠️ **Simulated branch, not real Starbucks operations.**
> The UI uses the public Starbucks menu plus a set of *simulated* operational
> CSVs (inventory, staffing, sales forecast, orders, promotions). It is not
> connected to any proprietary Starbucks data or system.

---

## Run it

```bash
uv sync                       # installs flask if you haven't synced lately
uv run python ui/app.py       # serves on http://127.0.0.1:5000
```

Open `http://127.0.0.1:5000` in any browser.

---

## What the UI calls

The console is a thin layer over four existing orchestrator functions:

| UI route | Calls |
|---|---|
| `POST /api/manager_readiness`      | `run_manager_readiness(store_id, date, hour)` |
| `POST /api/barista_recommendation` | `run_barista_recommendation(store_id, date, hour, customer_request, preferences)` |
| `POST /api/order_builder`          | `run_order_builder(store_id, date, raw_order)` |
| `POST /api/full_workflow`          | `run_full_workflow(store_id, date, hour, customer_request, raw_order, preferences)` |
| `POST /api/review_action`          | Records a UI-side review action to the in-process audit log |
| `GET  /api/audit_log`              | Returns the in-process audit log |
| `DELETE /api/audit_log`            | Clears the in-process audit log |

Each workflow response is returned verbatim, including `final_output`,
`evidence_package`, `review_queue`, `review_actions`, `audit_log`, `warnings`,
`assumptions`, and the Milestone 04 **`face_validity`** object.

---

## Views

The single-page app has six tabs and an always-visible Audit Log footer.

### 1. Full Workflow *(main presentation path — default tab)*
Chains all three workflows: manager readiness → barista recommendation →
order builder (if a raw order is given). This is the primary demo path.
Includes three optional **sample-fill** buttons that pre-fill the form;
the user still clicks **Run** to invoke the live orchestrator:

- *Morning Rush Dairy-Free*
- *Missing Size Order*
- *Allergy-Sensitive Request*

### 2. Manager View
Inputs: `store_id`, `date`, `hour`. Output: readiness summary, rush risk,
staffing, inventory alerts, barista guidance, recommended actions, warnings,
face-validity card.

### 3. Barista View
Inputs: `store_id`, `date`, `hour`, `customer_request`, optional preferences
(temperature, sweetness, milk_preference, caffeine, coffee_preference,
low_calorie). Loose keys are accepted — the MCP tool normalises them.
Output: ranked candidates, inventory cautions, RAG guidance, allergy flag
if detected, face-validity card.

### 4. Order Builder
Inputs: `store_id`, `date`, `raw_order`. Output: structured order, missing
fields, follow-up question, inventory warnings, prep notes (including
"prepare individually for quality consistency"), face-validity card.

### 5. Evidence Center
Auto-updates from the most recent workflow run. Sections:
- Face Validity (status, confidence, evidence quality, anchors, supporting reasons, concerns, recommended action)
- Tool / Data Evidence (each MCP-tool or automation output as a chip)
- RAG Evidence (filename, title, snippet, score, matched terms)
- Assumptions
- Warnings
- Evidence Quality (score + label + recommendation + count)

### 6. Review Queue
Auto-updates from the most recent run. For each item: reason, related step,
candidates if any, face-validity status, and four action buttons:

- **Approve** — records a UI audit entry
- **Edit** — opens a modal for an edit note, then records
- **Reject + Rerun** — records, user can re-run from the workflow tab
- **Escalate** — opens a modal for an escalation note, then records

Review actions update UI state and append to the Audit Log. They do not
write to any database (per Milestone 04 scope).

### Audit Log (footer)
Always visible. Combines:
- The current workflow's `audit_log` entries (from the orchestrator)
- UI-side actions (workflow runs, errors, review actions)

Refresh / Clear buttons reload or clear the in-process log.

---

## Face Validity card colour coding

| status | colour | meaning |
|---|---|---|
| `plausible` | green | evidence sufficient, no concerns |
| `needs_review` | yellow | designed human-approval state OR a real concern |
| `weak` | red | missing or insufficient evidence |
| `not_applicable` | gray | nothing to evaluate |

A `needs_review` verdict is **not** a failure for customer-facing flows —
human approval is part of the designed process.

---

## Error handling

- Orchestrator exceptions are caught in `app.py`, returned as a JSON
  `{"error": ..., "traceback": ...}` with HTTP 500, and the error is added
  to the Audit Log.
- The UI shows a red banner; the app does not crash.
- Warnings from the orchestrator surface as a yellow status banner plus a
  Warnings card in the Evidence Center.

---

## Sample inputs to try

| Path | Inputs | Demonstrates |
|---|---|---|
| Full Workflow | store=SD001, date=2024-01-15, hour=8, request="iced sweet dairy-free medium caffeine", raw_order="grande iced chai with almond milk" | All four anchors, RAG retrieval, inventory check, structured order parsing |
| Order Builder | raw_order="grande iced matcha with oat milk, light ice, and vanilla" | Item resolution + customizations + prep notes |
| Order Builder | raw_order="iced latte with oat milk" *(no size)* | Missing-field detection + follow-up question |
| Barista View | request="I have a nut allergy and want something dairy-free" | Allergy detection → face_validity escalates |

---

## Layout (v2 — refactored)

- **Top bar** — gradient green header + simulated-data chip
- **Left sidebar nav** (~240px) — three grouped sections:
  - *Workflow* — Full Workflow (with **MAIN** pill, prominent green)
  - *Stages* — Manager View, Barista View, Order Builder
  - *Audit* — Evidence Center / Review Queue with live badge counts
  - Sidebar collapses to icon-only at 1024px and into a hamburger drawer below 768px
- **Main content** (max-width 1400px) — view-specific cards, run-summary
  metrics grid, collapsible `<details>`-based output cards
- **Progress tracker** (Full Workflow only) — 5-step horizontal pill row
  (Input → Manager Check → Recommendation → Order Build → Complete)
- **Empty states** — every view shows a friendly empty card with icon + CTA
  *"Go to Full Workflow"* until a run populates it
- **Evidence Center sub-tabs** — Tool / RAG / Assumptions / Warnings /
  Quality + Face Validity
- **Review Queue filter** — All / Pending / Approved / Escalated chips
- **Audit Log** — **collapsible drawer pinned to the bottom** (default
  collapsed but always visible — `52px` bar showing entry count and
  chevron; expands to `40vh` with search input). Auditability is
  Milestone-04-critical so it can't be tucked away.

No build step, no JS framework — just `fetch()` to the routes and vanilla
DOM. Edit `static/style.css` or `static/app.js` and refresh.

---

## Tests

Local route tests live in [`../tests/test_ui_routes.py`](../tests/test_ui_routes.py).
They use Flask's `test_client()`, hit each route with realistic input, and
assert the JSON shape (live orchestrator calls — no mocks). Run with:

```bash
uv run pytest tests/test_ui_routes.py -v
```
