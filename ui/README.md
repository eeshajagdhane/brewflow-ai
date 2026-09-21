# `ui/` — BrewFlow AI Operations Console

> Flask + Jinja2 + vanilla JS console over the orchestrator.
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
`assumptions`, and the **`face_validity`** object.

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
write to any database. Persistence is a later step.

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
  chevron; expands to `40vh` with search input). The log stays on screen
  so a reviewer can see every tool call and every human action.

No build step, no JS framework — just `fetch()` to the routes and vanilla
DOM. Edit `static/style.css` or `static/app.js` and refresh.

---

## Manual Website Testing Guide

Use this matrix to exercise the UI manually after any change. Every test
below uses **live orchestrator calls** — no mocks, no canned outputs.

**Hour values:** The UI shows 12-hour labels (e.g. `8:00 AM`). The
**backend value** is the numeric hour (`8`). Both are listed below so you
can confirm what the API actually receives.

> **Tip:** Click **Clear** on the audit drawer between major test runs so
> each run starts with a clean log.

### A. Full Workflow (7 cases)

The Full Workflow tab is the main demo path. Each row below is a complete
input set — type the values manually or click a Quick Start where noted.

| # | Scenario | Store | Date | Hour (UI) | Hour (backend) | Customer request | Raw order | Expected behaviour | Evidence Center | Review Queue | Audit Log |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A1** | **Normal happy path** *(Quick Start: ☕ Iced Vanilla Latte)* | SD001 | 2024-01-15 | 8:00 AM | `8` | "I want an iced latte, something smooth and lightly sweet." | `grande iced vanilla latte with oat milk` | All 3 phases run; status=needs_review (designed); face_validity=needs_review/review; structured order size=Grande, milk=Oat Milk | Tool tab: 4+ tools; RAG tab: 3+ docs; FV score ≥ 0.7 | `recommendation_candidates` item | `workflow_completed · full_workflow` entry |
| **A2** | **Dairy-free recommendation** | SD001 | 2024-01-15 | 8:00 AM | `8` | "Iced sweet dairy-free, medium caffeine" | *(blank)* | Order phase skipped; recommendation candidates all vegan/dairy-free | Warning: *"Dairy-free preference applied as Vegan=Yes heuristic"* | `recommendation_candidates` only | Single `workflow_completed` entry |
| **A3** | **High-caffeine cold coffee** *(Quick Start: 🧊 Cold Brew)* | SD001 | 2024-01-15 | 10:00 AM | `10` | "Cold, coffee-forward, smooth, a little sweet." | `grande vanilla sweet cream cold brew` | Cold-coffee candidates rank high; order parses sweet cream as customization | `has_caffeine` reason_code visible | `recommendation_candidates` item | Standard entry |
| **A4** | **Oat-milk / inventory-aware** *(Quick Start: 🥛 Brown Sugar Espresso)* | SD001 | 2024-01-15 | 8:00 AM | `8` | "Iced, espresso-based, sweet, oat milk." | `grande iced brown sugar oatmilk shaken espresso` | Inventory check runs; if oat milk is low you'll see substitution warning | Tool tab shows `check_inventory_status`; warning if stock is low | `recommendation_candidates` (+ inventory note if low) | Standard entry |
| **A5** | **Allergy-sensitive** | SD001 | 2024-01-15 | 8:00 AM | `8` | "I have a nut allergy and want something dairy-free." | *(blank)* | face_validity.status=needs_review, **recommended_action=escalate** | Warnings tab includes allergy line; FV anchors+concerns mention allergy | `recommendation_allergy_review` (escalate) | Single entry, status `needs_review` |
| **A6** | **Missing size order** | SD001 | 2024-01-15 | 8:00 AM | `8` | "Something hot for the morning." | `iced latte with oat milk` *(no size)* | Order Builder card shows `missing_fields: ["size"]` + follow-up question | Warnings minimal; FV shows `ask_follow_up` | `order_missing_fields` item with follow-up question | Standard entry |
| **A7** | **Unknown item** | SD001 | 2024-01-15 | 8:00 AM | `8` | "Surprise me." | `large unicorn cloud drink with rainbow foam` | Item resolution falls back via menu search; item_resolution.candidates listed | RAG retrieval still runs; Tool tab includes `build_and_validate_order` | `recommendation_candidates` (+ possibly missing item flag) | Standard entry |

### B. Manager View (3 cases)

| # | Scenario | Store | Date | Hour (UI) | Hour (backend) | Expected behaviour |
|---|---|---|---|---|---|---|
| **B1** | **Normal afternoon readiness** | SD003 | 2024-02-20 | 2:00 PM | `14` | overall=success or warning; face_validity often `plausible` (green); 0–1 review items; barista_guidance.rush_level=low |
| **B2** | **High rush / staffing gap** | SD001 | 2024-01-15 | 8:00 AM | `8` | demand=high, demand_level=Very High, forecast≈211; recommended_actions includes CRITICAL/ACTION items; barista_guidance.rush_level=high |
| **B3** | **Missing/weak data** | SD001 | 2024-05-30 *(outside data range)* | 8:00 AM | `8` | Warnings list non-empty (sparse or missing forecast); face_validity quality_score downgraded |

For each Manager run, check the **barista_guidance** block in the output card — `rush_level`, `service_mode`, `avoid_ingredients`, `caution_ingredients`, `promotion_items`.

### C. Barista View (5 cases)

All Barista runs below use `SD001 / 2024-01-15`.

| # | Scenario | Hour (UI) | Hour (backend) | Customer request | Suggested preferences | Expected behaviour |
|---|---|---|---|---|---|---|
| **C1** | **Iced sweet dairy-free** | 8:00 AM | `8` | "Iced, sweet, dairy-free" | milk_preference: dairy-free | Vegan candidates (Iced Black Tea, Pink Drink, Mango Dragonfruit) |
| **C2** | **Cold brew / high caffeine** | 10:00 AM | `10` | "Cold coffee with strong caffeine" | temperature: iced; caffeine: high | Cold-coffee candidates rank high (Nitro Cold Brew, Cold Brew Coffee, Iced Americano) |
| **C3** | **Vague request** | 8:00 AM | `8` | "Something good" | *(none)* | System returns broad candidates; quality_score may dip; face_validity still needs_review (designed) |
| **C4** | **Allergy-sensitive** | 8:00 AM | `8` | "I have a nut allergy, dairy-free please" | milk_preference: dairy-free | face_validity escalates; `recommendation_allergy_review` item in queue |
| **C5** | **Low-calorie request** | 8:00 AM | `8` | "Light, low-calorie, refreshing" | low_calorie: true | Top candidates skew to teas / refreshers; reason_codes include `low_calorie` |

All recommendation runs have `review_required=True` by design.

### D. Order Builder (5 cases)

All Order Builder runs use `SD001 / 2024-01-15`.

| # | Scenario | Raw order | Expected behaviour |
|---|---|---|---|
| **D1** | **Complete normal order** | `grande iced caramel macchiato with oat milk` | item=Iced Caramel Macchiato, size=Grande, temp=Iced, milk=Oat Milk; no missing fields |
| **D2** | **Missing size** | `iced latte with oat milk` | `missing_fields: ["size"]`, follow_up_question populated; status=needs_review |
| **D3** | **Ambiguous / unknown drink** | `large unicorn cloud drink with rainbow foam` | item_resolution falls back via menu search; candidates list shows closest matches |
| **D4** | **Allergy-sensitive** | `grande latte, I have a nut allergy` | human_review_required=true; allergy warning; face_validity recommends `escalate` |
| **D5** | **Heavy customization** | `grande iced matcha with oat milk, light ice, vanilla, extra shot` | customizations=[light ice, extra shot]; syrups=[vanilla]; milk_type=Oat Milk; prep_notes include each |

### E. Evidence Center — what should appear

After running any workflow, switch to **🔍 Evidence Center** and check each sub-tab:

| Sub-tab | What should be there | When |
|---|---|---|
| **Tool / Data** | Every MCP tool / automation that fired, with status pill (green/yellow). Manager runs see 3+ tools, Recommendation sees 2–3, Order Builder sees 1, Full Workflow sees all of them. | After every run |
| **RAG** | 3+ documents per workflow with title, filename, score, matched terms, snippet. For dairy-free / allergy queries you'll see `dietary_allergen_guidance.md`. For rush queries: `rush_hour_service_playbook.md`. | After every run |
| **Assumptions** | Lines like *"Rush period active — recommendation tuned for high-demand context"* when the workflow had to assume defaults. Empty for clean runs. | When the orchestrator filled in defaults |
| **Warnings** | Lines like *"HIGH rush risk at hour 08:00 — forecast 211 orders"*, allergy warnings, latest-prior-snapshot warnings. | When the run produced warnings |
| **Quality + Face Validity** | Face Validity card with status / confidence / anchors + Evidence Quality summary (score + label + recommendation + count). | Always — face_validity is required on every run |

### F. Review Queue — what produces items

| Scenario | Review item that should appear |
|---|---|
| Any barista recommendation | `recommendation_candidates` — designed human approval before serving |
| Allergy/medical language in request or order | `recommendation_allergy_review` *or* `order_allergy_review` — escalate |
| Missing required order fields (size, temperature) | `order_missing_fields` with follow-up question — ask follow-up |
| Weak evidence quality (score < 0.3) | Workflow-level needs_review with low-quality concern |
| Low-stock substitution needed | Inventory warning surfaces in evidence; reviewer should verify before approving recommendation |
| Unknown / ambiguous item | Order item_resolution returns candidates instead of canonical_name; reviewer picks one |
| Vague request | No specific review item, but `recommendation_candidates` still queued |

Use the **filter chips** (All / Pending / Approved / Escalated) at the top of the Review Queue to scope what you see after acting on items. Each Approve / Edit / Reject + Rerun / Escalate click updates the UI and appends a `user_review` entry to the Audit Log.

---

## Tests

Local route tests live in [`../tests/test_ui_routes.py`](../tests/test_ui_routes.py).
They use Flask's `test_client()`, hit each route with realistic input, and
assert the JSON shape (live orchestrator calls — no mocks). Run with:

```bash
uv run pytest tests/test_ui_routes.py -v
```
