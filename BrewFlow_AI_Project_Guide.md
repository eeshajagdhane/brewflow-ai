# BrewFlow AI — Teammate Project Guide

*A simple, friendly walkthrough of what we built, why we built it, and how to test it.*

This guide is for teammates who want to understand the project quickly, give feedback, and try the UI website. You do not need a coding background to read it. Where we use a technical word, we explain it the first time.

---

## 1. Project Overview

**BrewFlow AI** is a small web app that helps the staff of a coffee shop run their day. It is an "operations console" — a single dashboard where a manager and a barista can check what is happening before a shift, get a drink recommendation for a customer, and turn a free-text order into a clean structured order.

### Why we built it

For a typical busy coffee shop morning, four kinds of work happen in parallel:

- The manager wants to know **how busy** the shop will be, **who is on shift**, and **what is low in stock**.
- The barista wants to **recommend a good drink** based on what the customer wants.
- The barista wants to **build the order correctly** without missing the size, milk, or temperature.
- Both want to **catch dietary or allergy concerns** early — before the drink is made.

Today, this is all done by walking around, looking at clipboards, and relying on memory. BrewFlow AI brings the same tasks into one place, with the AI doing the boring lookups and the human always staying in control.

### Who uses it

| User | What they do in BrewFlow AI |
|---|---|
| **Manager** | Runs the pre-rush readiness check; reviews inventory + staffing + demand; approves AI-generated guidance |
| **Barista** | Enters customer requests, reviews drink recommendations, validates raw orders, approves before the customer gets the drink |

### What the final prototype does

It is a **live** Flask web console. Every result comes from real code calling real CSV files — nothing is faked. The user picks a store / date / hour, types a request, clicks Run, and sees:

- A readiness summary (for the manager)
- A ranked list of drink recommendations (for the barista)
- A parsed structured order (for the order builder)
- An evidence package showing what data and policies the AI used
- A face-validity verdict saying whether the AI's output looks reasonable
- A review queue with action buttons (Approve / Edit / Reject + Rerun / Escalate)
- A timestamped audit log of every step

### What this is NOT

> **Important honesty note.** BrewFlow AI uses the **public Starbucks menu** plus **simulated** operational CSVs (made-up inventory, staffing, sales forecast, order history, promotions). We do not use real proprietary Starbucks data. We are not connected to a real Starbucks point-of-sale system. All quantitative estimates in the project documents are reasoned ranges, not company facts.

---

## 2. Big Picture Workflow

In simple steps, here is what happens when the full workflow runs end-to-end:

1. The **manager** picks the store, date, and hour, and opens the readiness check.
2. The **system** automatically checks rush risk, staffing gap, and inventory levels.
3. **RAG** (which means the AI fetches relevant internal documents) pulls the right policies for this situation — manager checklist, rush playbook, promotion policy.
4. The **manager reviews** the guidance and decides what to do.
5. The **barista** enters the customer's request (and optionally a structured set of preferences).
6. The **AI recommends a drink** using the menu, current inventory, rush context, and internal guidance.
7. The **barista reviews** the recommendation with the customer.
8. The **Order Builder** turns the raw order text ("grande iced chai with almond milk") into a structured order with separate fields for size, milk, temperature, customizations.
9. The **AI creates** a customer-facing confirmation and a barista prep note.
10. A **human approves, edits, rejects + reruns, or escalates** — the system never auto-finalizes a customer-facing recommendation.
11. The **evidence and audit log** are stored and shown in the UI for later review.

### Simple text diagram

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                MANAGER PHASE                                     │
  │  Manager picks store/date/hour                                   │
  │     ↓                                                            │
  │  Tools: detect_rush_period + calculate_staffing_gap +            │
  │         check_inventory_status                                   │
  │     ↓                                                            │
  │  RAG: manager_pre_shift_checklist + rush_hour_service_playbook   │
  │     ↓                                                            │
  │  Automation: manager_daily_briefing                              │
  │     ↓                                                            │
  │  Manager reviews briefing → Approve / Edit / Rerun / Escalate    │
  └──────────────────────────────────────────────────────────────────┘
                              ↓ barista_guidance carries over
  ┌──────────────────────────────────────────────────────────────────┐
  │                BARISTA RECOMMENDATION PHASE                      │
  │  Barista enters customer request + optional preferences          │
  │     ↓                                                            │
  │  Orchestrator parses natural language → preferences               │
  │     ↓                                                            │
  │  RAG: barista_recommendation_guidelines, dietary_allergen_       │
  │       guidance, service_recovery_policy                          │
  │     ↓                                                            │
  │  Tools: search_menu_by_preferences + check_inventory_status      │
  │     ↓                                                            │
  │  Skill: recommendation                                           │
  │     ↓                                                            │
  │  Barista reviews ranked candidates → Approve / Edit / Escalate   │
  └──────────────────────────────────────────────────────────────────┘
                              ↓ selected_item carries over
  ┌──────────────────────────────────────────────────────────────────┐
  │                ORDER BUILDER PHASE                               │
  │  Raw order: "grande iced matcha with oat milk, light ice"        │
  │     ↓                                                            │
  │  Tool: build_and_validate_order (regex parser + item resolver +  │
  │        inventory check + allergy detection)                      │
  │     ↓                                                            │
  │  Missing field?  →  Ask follow-up question  →  Loop              │
  │     ↓                                                            │
  │  RAG: order_confirmation_standard, drink_quality_consistency     │
  │     ↓                                                            │
  │  Skill: order_summary  → customer confirmation + prep notes      │
  │     ↓                                                            │
  │  Barista approves the final order → drink prepared individually  │
  └──────────────────────────────────────────────────────────────────┘
                              ↓ every step recorded
  ┌──────────────────────────────────────────────────────────────────┐
  │                EVIDENCE + REVIEW + AUDIT                         │
  │  Evidence package: tool outputs, RAG snippets, assumptions,      │
  │  warnings, quality score                                         │
  │  Face Validity: status, confidence, anchors, supporting reasons, │
  │  concerns, recommended action                                    │
  │  Review Queue: items flagged for a human                         │
  │  Audit Log: every step + every human review action               │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 3. Folder Structure Explanation

Here is what lives in each folder and why it matters.

| Folder | What's inside | Why it matters |
|---|---|---|
| `data/raw/` | 9 CSV files: menu, inventory, staffing, orders, forecast, etc. | The single source of truth for every workflow. **Read-only — never edit.** |
| `skills/` | 5 sub-folders, each with a `SKILL.md` file | "Skills" are AI instruction docs that tell the AI how to behave in one role (recommendation, order_summary, etc.) |
| `automations/` | 4 sub-folders with `run_*.py` files | Plain Python calculations (no AI). Inventory monitoring, staffing gap, demand rush, manager briefing. |
| `mcp_servers/` | `brewflow_mcp_server.py` (6 callable tools) | The "tools" the AI can call — like menu lookup, inventory check, order parsing. MCP = Model Context Protocol. |
| `rag/` | `knowledge_base/` (12 simulated SOP/policy docs) + `retrieval.py` | RAG = Retrieval Augmented Generation. The system fetches relevant internal documents before producing answers. |
| `scripts/` | `orchestrator.py` (the workflow driver) + a docs PDF builder | The orchestrator is the brain that chains automations + tools + RAG + skills into the 4 workflow functions. |
| `utils/` | Shared Python helpers (data loader, evidence builder, face validity) | Used by every other piece. Includes the face-validity layer. |
| `ui/` | `app.py` (Flask server) + `templates/index.html` + `static/` (CSS, JS) | The web app you open at http://127.0.0.1:5000 |
| `tests/` | 5 active test files (95 tests) + a results folder | Local tests that confirm everything still works. No API keys needed. |
| `presentation_slides/` | Slide outline + 10-minute demo script | For the final class presentation |
| Root markdown files | `README.md`, `estimates.md`, `test_report.md`, `ai_process_design.md`, `human_review_plan.md`, `failure_cases.md`, `evidence_and_sources.md`, `face_validity.md` | The Milestone 04 deliverable documents |

---

## 4. Data Explanation

All 9 files live in `data/raw/`. Please do not modify them.

| File | What it represents | Real or simulated? | Used by |
|---|---|---|---|
| `starbucks_menu_full.csv` | The Starbucks menu — drink names, sizes, calories, caffeine, allergen flags, ingredients | **Public Starbucks menu data** | Menu lookup, preference search, item resolution |
| `order_history.csv` | 20,000 made-up customer orders across stores, dates, and hours | Simulated | Demand/rush detection, popularity boost in recommendations |
| `store_inventory.csv` | Daily snapshot of ingredient stock for each store | Simulated | Inventory checks, "avoid" / "caution" lists in the manager briefing |
| `staff_schedule.csv` | Made-up shift data: who is working, when | Simulated | Staffing gap calculation |
| `daily_sales_forecast.csv` | Hourly forecast and actual order counts per store/date | Simulated | Rush detection, manager readiness |
| `promotion_margins.csv` | Active promotions with margin info | Simulated | Manager briefing, recommendation scoring boost |
| `item_name_mapping.csv` | 33 mappings to handle name variations ("Iced Latte" → "Iced Caffe Latte") | Synthetic mapping table | Item name resolution in order parsing |
| `ingredient_mapping.csv` | Links menu ingredient terms ("oat milk") to inventory column names | Synthetic mapping table | Inventory check for parsed orders |
| `demo_scenarios.csv` | 12 ready-made test scenarios | Simulated | Used by tests, not the live workflow |

> The only file that ties back to real Starbucks is the **menu**. Everything else is fabricated for educational use.

---

## 5. Skills Explanation

A **skill** is a set of natural-language instructions for the AI, written in a `SKILL.md` file. Skills are good at **judgment-heavy** work — explaining a choice, summarizing an order, suggesting an alternative.

An **automation** (next section) is plain Python — good at **deterministic** work like counting low-stock items or calculating staffing gaps.

> Rule of thumb: if the work needs creativity or natural language, use a skill. If the work is arithmetic or table lookup, use an automation.

| # | Skill | What it does | When it's used | Inputs | Evidence it uses | Output | Human role |
|---|---|---|---|---|---|---|---|
| 1 | `product_catalog` | Answers questions about menu items in plain English | When a barista is unsure about a drink's caffeine, calories, or ingredients | Item name or partial name | `starbucks_menu_full.csv` via `get_menu_item_info` tool; RAG `new_barista_menu_training_guide.md` | A clear factual summary of the item | Barista reads the answer; no formal approval needed |
| 2 | `recommendation` | Generates a drink recommendation with reasons | Once the customer has described what they want | Customer request + preferences + inventory context + RAG guidance | `search_menu_by_preferences`, `check_inventory_status`, RAG dietary + recommendation + service-recovery docs | Ranked candidates with explanation; flagged for human approval | Barista reviews with the customer, then Approves / Edits / Escalates |
| 3 | `order_builder` | Helps shape a raw customer sentence into a structured order | When the customer says something like "grande iced chai with oat milk" | Raw order text | `build_and_validate_order` tool; RAG `customization_policy.md`, `inventory_substitution_sop.md` | Structured order + missing fields + follow-up question | Barista confirms or fills missing fields |
| 4 | `order_summary` | Writes a customer-facing confirmation + a barista prep note | After the order is validated | Structured order from order_builder | RAG `order_confirmation_standard.md`, `drink_quality_consistency_sop.md` | Confirmation text + prep notes (with "prepare individually") | Barista reads the confirmation back to the customer |
| 5 | `workflow_orchestrator` | High-level coordinator skill (in our case, mostly handled by `scripts/orchestrator.py`) | Across the whole workflow | All of the above | All tools + RAG | Routes outputs from one step to the next | Indirect — managers/baristas see the orchestrated final output |

---

## 6. Automations Explanation

Automations are plain Python calculations. **No AI guessing happens here** — same input always gives the same output.

| # | Automation | What it does | Why it's not a skill | Data it uses | Output | Where it shows in the UI |
|---|---|---|---|---|---|---|
| 1 | `inventory_monitoring` | Counts how many ingredients are low / overstocked / unavailable / healthy | Pure table classification — no opinion needed | `store_inventory.csv` | Lists of low, overstock, unavailable items + counts | Manager Readiness card; Evidence Center → Tool/Data tab |
| 2 | `staffing_gap_calculator` | Counts how many unique employees are scheduled for the hour and compares to a baseline | Math, not opinion | `staff_schedule.csv` | `scheduled_staff`, `required_staff`, `staffing_gap`, status (Understaffed / Balanced / Overstaffed) | Manager Readiness card |
| 3 | `demand_rush_detection` | Classifies the hour as low / moderate / high / very high based on historical orders + forecast | Statistics, not judgment | `order_history.csv`, `daily_sales_forecast.csv` | `demand_level`, `rush_risk`, forecast vs actual orders | Manager Readiness card; included in barista_guidance |
| 4 | `manager_daily_briefing` | Combines the three above + active promotions into a single briefing | Pure orchestration of deterministic steps | All the above + `promotion_margins.csv` | Readiness summary + recommended manager actions + barista guidance | Manager Readiness output card |

---

## 7. MCP Tools Explanation

**What is MCP?** Model Context Protocol. In simple words: **MCP-style tools are callable backend functions that let the AI workflow access data or run calculations.** Think of them like buttons the AI can press to get information.

All 6 tools live in `mcp_servers/brewflow_mcp_server.py`.

| # | Tool | What it does | Input (simple) | Output (simple) | Used in |
|---|---|---|---|---|---|
| 1 | `get_menu_item_info` | Looks up a drink by name | A drink name like "Iced Latte" | Category, calories, caffeine, allergen info, size options | Product catalog skill |
| 2 | `search_menu_by_preferences` | Ranks the menu against preferences | Preferences like `{temperature: iced, dairy_free: True}` | Top 8 drinks with scores and reason codes | Barista recommendation |
| 3 | `check_inventory_status` | Checks if ingredients are in stock | Store ID, date, list of ingredients | Per-ingredient stock status + safety flag | Manager readiness, order validation |
| 4 | `detect_rush_period` | Says how busy the hour is | Store ID, date, hour | demand_level, rush_risk, forecast vs actual orders | Manager readiness; recommendation context |
| 5 | `calculate_staffing_gap` | Compares scheduled vs required staff | Store ID, date, hour | scheduled_staff, required_staff, staffing_gap, status | Manager readiness |
| 6 | `build_and_validate_order` | Parses raw order text | Raw text like "grande iced chai with oat milk" | Structured order (size, temp, milk, syrups, customizations) + missing fields + follow-up question | Order Builder |

**Example: `build_and_validate_order` in plain English**

- Input: `"grande iced matcha with oat milk, light ice, and vanilla"`
- Output: item=`Iced Matcha Tea Latte`, size=`Grande`, temp=`Iced`, milk=`Oat Milk`, syrups=`[vanilla]`, customizations=`[light ice]`, missing_fields=`[]`, prep_notes include the line *"Prepare individually for quality consistency."*

---

## 8. RAG Explanation

**What is RAG?** Retrieval-Augmented Generation. In simple words: **RAG lets the AI retrieve relevant internal documents before giving an answer.** Instead of guessing, the AI first looks at the company's own policies, SOPs, and training guides, and uses them to ground its response.

> **Honesty note.** Our knowledge base is **simulated** internal company guidance written for this class project. It is not actual proprietary Starbucks documentation.

The 12 documents live in `rag/knowledge_base/`.

| # | Document | What's in it | When the AI retrieves it | Why it matters |
|---|---|---|---|---|
| 1 | `barista_recommendation_guidelines.md` | How to suggest drinks: ask about temperature, sweetness, dairy preferences | Every recommendation run | Keeps recommendations consistent across baristas |
| 2 | `customization_policy.md` | Which modifications are allowed and how to charge for them | When the order has customizations like "extra shot" | Prevents giving away paid extras for free |
| 3 | `inventory_substitution_sop.md` | What to substitute when an ingredient is low (e.g. oat milk → soy milk) | When inventory check shows a key ingredient is low | Keeps service running during stock issues |
| 4 | `rush_hour_service_playbook.md` | How to streamline service during peak hours | When demand_level is high or very high | Helps the barista keep the line moving |
| 5 | `manager_pre_shift_checklist.md` | Steps a manager should run through before opening | Every manager-readiness run | Standardizes pre-shift prep |
| 6 | `promotion_decision_policy.md` | When and how to mention a promotion to a customer | When the store has active promotions for that date | Balances revenue with not pushing too hard |
| 7 | `new_barista_menu_training_guide.md` | Onboarding facts about the menu | When a barista asks about an unfamiliar drink | Helps newer baristas without needing a manager |
| 8 | `order_confirmation_standard.md` | How to phrase the customer-facing confirmation ("Grande iced caramel macchiato — confirmed.") | When the order summary is being generated | Keeps the confirmation friendly and accurate |
| 9 | `dietary_allergen_guidance.md` | What to say (and what NOT to say) for dietary and allergy requests | When dairy-free, vegan, or allergen language appears | Critical safety document — never guarantees allergen-free prep |
| 10 | `drink_quality_consistency_sop.md` | "Prepare each drink individually for consistent quality." No batching. | Every order-summary run | Ensures the prep notes always include the no-batching rule |
| 11 | `service_recovery_policy.md` | What to do when something goes wrong (item out of stock, wrong order) | When a recommendation may not be available | Gives the barista a script for graceful recovery |
| 12 | `post_rush_manager_review_template.md` | A template a manager fills in after the rush to capture what worked | Referenced in the post-rush flow | Closes the feedback loop for the next shift |

---

## 9. Face Validity Explanation

**What is face validity?** In simple words: **face validity checks whether the AI's output looks reasonable based on the evidence it used.** It is a final sanity check before a human is asked to review.

| What face validity IS | What face validity is NOT |
|---|---|
| A deterministic rules-based check (no LLM) | An MCP tool |
| A scoring + status verdict | A RAG document |
| An evaluation/review layer | An AI skill |
| A "reasonable enough to investigate" judgment | A guarantee of correctness |

Every workflow result includes a `face_validity` object with these fields:

| Field | What it tells you |
|---|---|
| `status` | Overall verdict: `plausible` / `needs_review` / `weak` / `not_applicable` |
| `confidence` | How sure the system is: `high` / `medium-high` / `medium` / `low` |
| `supporting_reasons` | Why the AI thinks the output is reasonable |
| `concerns` | What might be wrong |
| `evidence_quality` | A 0–1 score + a label (`strong` / `moderate` / `weak`) |
| `anchors_used` | What kinds of evidence the AI grounded its answer in (tool output, RAG, audit log, etc.) |
| `recommended_action` | What the human should do: `approve` / `review` / `ask_follow_up` / `rerun` / `escalate` |

### Examples in plain English

| Scenario | Face validity verdict |
|---|---|
| Normal recommendation, good evidence | `status = plausible`, `recommended_action = approve` |
| Allergy language in the request | `status = needs_review`, `recommended_action = escalate` |
| Order is missing the size | `status = needs_review`, `recommended_action = ask_follow_up` |
| No RAG docs retrieved + only 1 tool output | `status = weak`, `recommended_action = review` |
| Manager readiness for a quiet afternoon, no concerns | `status = plausible`, `recommended_action = approve` |

---

## 10. Human-in-the-Loop Explanation

BrewFlow AI never serves a customer-facing recommendation without a human reviewing it first. This is a design choice, not a bug.

Where humans stay in control:

- **Manager** reviews the pre-rush readiness guidance.
- **Barista** reviews each drink recommendation before telling the customer.
- **Barista or customer** confirms the final structured order before drink prep.
- **Review Queue** shows everything the workflow flagged for human attention.
- **Human can Approve, Edit, Reject + Rerun, or Escalate** — every click is recorded.

### Why this matters

- **Avoids blind trust in AI.** Even good AI can be confidently wrong.
- **Helps with dietary and allergen caution.** The AI surfaces the risk; the human verifies.
- **Helps with missing fields.** The AI asks; the human answers.
- **Helps when evidence is weak.** The AI flags low confidence; the human investigates.

---

## 11. UI Website Guide

The website is the **BrewFlow AI Operations Console**. It is a single page with six tabs in a left sidebar plus a collapsible Audit Log drawer at the bottom.

### Full Workflow *(main demo path)*

**What it does:** Runs all three workflows back-to-back — manager readiness, barista recommendation, and order builder.

**Required fields** (marked with a red `*`):
- Store ID
- Date
- Hour
- Customer Request

**Optional fields**:
- Raw Order
- Structured preferences (temperature, sweetness, milk_preference, caffeine, coffee_preference, low_calorie)

**What happens when you click Run:**
1. Progress tracker at the top lights up step-by-step
2. Status banner appears (usually yellow `needs_review` — that's by design)
3. Face Validity card shows the verdict
4. Three collapsible output cards: Manager Readiness, Recommendation, Order Builder
5. Workflow-level review buttons (Approve / Edit / Reject + Rerun / Escalate)

**When to use this view:** The main path for the final presentation demo. Use it when you want to see the entire system end-to-end.

### Manager View

**What it does:** Just the manager pre-rush readiness check.

**Required inputs:** Store ID, Date, Hour.

**What the manager sees:** A summary card with overall status, demand level, staffing gap, inventory alerts, and a list of recommended manager actions. Plus a barista guidance block.

**Example use case:** Manager opening the store at 7:00 AM wants a 30-second briefing before unlocking the door.

### Barista View

**What it does:** Drink recommendation only — no order parsing.

**Required inputs:** Store ID, Date, Hour, Customer Request.

**Optional inputs:** Structured preferences.

**How it works:** The system parses the customer's request, ranks the menu, checks inventory for the top candidates, retrieves relevant RAG guidance, and returns ranked candidates with reason codes.

**What evidence to check:** Open the Evidence Center and look at the Tool/Data tab (to see what scored well) and the RAG tab (to see what guidance was retrieved).

**Example use case:** A customer says "something sweet and cold and dairy-free." The barista enters that, runs the recommendation, and reads the top 3 to the customer.

### Order Builder

**What it does:** Parses a raw customer order into structured fields.

**Required inputs:** Store ID, Date, Raw Order.

**What output to expect:** A structured order with separate fields for item, size, temperature, milk, syrups, customizations, plus prep notes.

**What happens if size or item is missing:** The system catches it, sets `missing_fields = ["size"]`, generates a follow-up question, and routes to the Review Queue.

**Example use case:** Barista types "grande iced matcha with oat milk, light ice, and vanilla." The system parses it correctly. Order can be approved.

### Evidence Center

**What it shows:** Everything the AI used to make its decision in the most recent workflow run.

Five sub-tabs:

| Sub-tab | What you'll see |
|---|---|
| **Tool / Data** | Every MCP tool and automation that ran, with a status pill |
| **RAG** | Knowledge base documents retrieved, with title, score, matched terms, and a snippet |
| **Assumptions** | Anywhere the workflow had to use a default |
| **Warnings** | Anything the workflow flagged (stale snapshot, dairy-free heuristic, etc.) |
| **Quality + Face Validity** | The face-validity card + the evidence quality score |

**Why teammates should check this:** This is the "show your work" tab. After every Run, switch here and confirm the system used the kind of evidence you'd expect.

### Review Queue

**What review items are:** Items the workflow flagged for a human to look at — recommendation candidates, missing order fields, allergy concerns, low-stock warnings.

**What the action buttons mean:**

| Button | What it does |
|---|---|
| **Approve** | The output is good — go ahead. Card gets a green border. |
| **Edit** | Opens a notes modal. The output needs a small change. Card gets a blue border. |
| **Reject + Rerun** | The output is wrong. Run the workflow again with new inputs. Card gets a red border. |
| **Escalate** | Send to a senior manager — usually for allergy or medical concerns. Card gets an amber border. |

**When review items appear:** Always, for customer-facing workflows (recommendation, order builder, full workflow). The system is *designed* to require human approval.

### Audit Log

**What it records:** Every workflow run (with source `orchestrator`) and every human review click (with source `user_review`). Each entry has a timestamp, action, workflow type, status, and a short message.

**Why it matters:** If something went wrong, you can replay exactly what happened — what was run, what the system did, what a human approved.

**How it helps:** The drawer is at the bottom of the screen. Click the green bar to expand it to about 40% of the screen height. Search lets you filter by any keyword.

---

## 12. How to Run the Website

Open a terminal, navigate to the project folder, then:

```bash
uv sync
uv run python ui/app.py
```

You should see:

```
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

Open `http://127.0.0.1:5000` in your browser (Chrome, Safari, Firefox — anything).

To stop the server, press `Ctrl + C` in the terminal.

### How to run the tests

```bash
uv run pytest tests/test_mcp_tools.py tests/test_rag_retrieval.py \
              tests/test_brewflow_workflow.py tests/test_face_validity.py \
              tests/test_ui_routes.py
```

**Expected result: 95 tests passing.** No API keys are needed.

---

## 13. Website Testing Instructions for Teammates

These are inputs you can copy into the UI. Always click the green Run button after pasting.

### Full Workflow tests

#### Test F1 — Normal dairy-free workflow

| Field | Value |
|---|---|
| Store ID | SD001 |
| Date | 2024-01-15 |
| Hour | 8:00 AM |
| Customer Request | I want something iced, sweet, dairy-free, and medium caffeine. |
| Raw Order | grande iced chai with almond milk |

**Expected behavior:** All three phases run. Status = needs_review. Face Validity = needs_review/review (yellow).

- **Evidence Center:** Tool tab shows 4+ tools; RAG tab shows 3+ docs; quality score around 0.85.
- **Review Queue:** A `recommendation_candidates` item with Approve buttons.
- **Audit Log:** One `workflow_completed · full_workflow` entry.

#### Test F2 — Cold brew / high-caffeine workflow

| Field | Value |
|---|---|
| Store ID | SD001 |
| Date | 2024-01-15 |
| Hour | 10:00 AM |
| Customer Request | I want something cold, coffee-forward, smooth, and a little sweet. |
| Raw Order | grande vanilla sweet cream cold brew |

**Expected behavior:** Cold-coffee candidates rank top. Reason codes include `has_caffeine`. Order Builder parses sweet cream as a customization.

- **Evidence Center:** Tool tab shows `check_inventory_status` and `search_menu_by_preferences`.
- **Review Queue:** `recommendation_candidates` item.
- **Audit Log:** Standard workflow entry.

#### Test F3 — Oat milk inventory-sensitive workflow

| Field | Value |
|---|---|
| Store ID | SD001 |
| Date | 2024-01-15 |
| Hour | 8:00 AM |
| Customer Request | I want something iced, espresso-based, sweet, and made with oat milk. |
| Raw Order | grande iced brown sugar oatmilk shaken espresso |

**Expected behavior:** Inventory check runs; if oat milk is low on the snapshot, you'll see an inventory warning.

- **Evidence Center:** Warnings tab may list a low-stock note.
- **Review Queue:** `recommendation_candidates`, plus an inventory note if oat milk is low.

#### Test F4 — Allergy-sensitive workflow

| Field | Value |
|---|---|
| Store ID | SD001 |
| Date | 2024-01-15 |
| Hour | 8:00 AM |
| Customer Request | I have a nut allergy and want something dairy-free. |
| Raw Order | *(leave blank)* |

**Expected behavior:** Face Validity status = needs_review, recommended_action = **escalate**. Order phase skipped because there's no raw_order.

- **Evidence Center:** Warnings tab includes the allergy line.
- **Review Queue:** `recommendation_allergy_review` item.
- **Audit Log:** Entry with status `needs_review`.

#### Test F5 — Missing size workflow

| Field | Value |
|---|---|
| Store ID | SD001 |
| Date | 2024-01-15 |
| Hour | 8:00 AM |
| Customer Request | Something hot for the morning. |
| Raw Order | iced latte with oat milk *(no size — intentional)* |

**Expected behavior:** Order Builder catches the missing size; follow-up question appears; Face Validity recommends `ask_follow_up`.

- **Evidence Center:** Warnings tab quiet; FV concerns mention missing fields.
- **Review Queue:** `order_missing_fields` item with the follow-up question attached.
- **Audit Log:** Standard entry.

#### Test F6 — Unknown item workflow

| Field | Value |
|---|---|
| Store ID | SD001 |
| Date | 2024-01-15 |
| Hour | 8:00 AM |
| Customer Request | Surprise me. |
| Raw Order | large unicorn cloud drink with rainbow foam |

**Expected behavior:** Item resolution falls back via menu search; candidates list populated. Status = warning or needs_review.

- **Evidence Center:** Tool tab still includes `build_and_validate_order`.
- **Review Queue:** `recommendation_candidates`.
- **Audit Log:** Standard entry.

### Manager View tests

| # | Scenario | Store ID | Date | Hour | Expected behavior |
|---|---|---|---|---|---|
| **M1** | Normal afternoon readiness | SD003 | 2024-02-20 | 2:00 PM | overall = success / warning; FV often `plausible` (green); 0–1 review items |
| **M2** | High rush / staffing gap | SD001 | 2024-01-15 | 8:00 AM | demand_level = Very High, forecast ≈ 211, recommended_actions includes CRITICAL/ACTION items |
| **M3** | Missing/weak data | SD001 | 2024-05-30 *(outside data range)* | 8:00 AM | Warnings non-empty; FV quality_score may downgrade |

### Barista View tests

All use SD001 / 2024-01-15 / 8:00 AM unless noted.

| # | Scenario | Customer Request | Preferences | Expected behavior |
|---|---|---|---|---|
| **B1** | Iced sweet dairy-free | "Iced, sweet, dairy-free" | milk_preference: dairy-free | Candidates all vegan (Iced Black Tea, Pink Drink, Mango Dragonfruit) |
| **B2** | Cold brew high caffeine | "Cold coffee with strong caffeine" (use hour 10:00 AM) | caffeine: high | Cold coffee top (Nitro Cold Brew, Cold Brew Coffee) |
| **B3** | Vague request | "Something good" | *(none)* | Broad candidates; quality score may dip |
| **B4** | Allergy-sensitive | "I have a nut allergy, dairy-free please" | milk_preference: dairy-free | FV escalates; allergy review queue item |
| **B5** | Low-calorie | "Light, low-calorie, refreshing" | low_calorie: true | Teas / refreshers rank top; `low_calorie` reason code |

### Order Builder tests

All use SD001 / 2024-01-15.

| # | Scenario | Raw Order | Expected behavior |
|---|---|---|---|
| **O1** | Complete order | `grande iced caramel macchiato with oat milk` | item = Iced Caramel Macchiato, size = Grande, temp = Iced, milk = Oat Milk; no missing fields |
| **O2** | Missing size | `iced latte with oat milk` | `missing_fields = ["size"]`, follow-up question populated |
| **O3** | Unknown drink | `large unicorn cloud drink with rainbow foam` | Item resolution falls back; candidates list shown |
| **O4** | Allergy-sensitive | `grande latte, I have a nut allergy` | human_review_required = true; allergy warning; FV recommends `escalate` |
| **O5** | Customized order | `grande iced matcha with oat milk, light ice, vanilla, extra shot` | customizations = [light ice, extra shot]; syrups = [vanilla]; milk = Oat Milk; prep notes include each |

---

## 14. What Feedback We Want From Teammates

Please test the site and answer these questions:

1. Was the overall workflow easy to understand from the UI?
2. Did the Full Workflow view make sense as the main demo path?
3. Were required and optional fields clear (red asterisks + "(Optional)" labels)?
4. Was the Evidence Center helpful for understanding what the AI used?
5. Did the Review Queue make human control feel real?
6. Did the Face Validity card make sense?
7. Were any outputs confusing or hard to read?
8. Did any test case break or produce a weird result?
9. What design / layout changes would make it easier to use?
10. What is the single most important thing we should improve before the final presentation?

Please be honest. We would rather hear "I didn't understand X" than have you say nice things and then a grader say the same thing.

---

## 15. Known Limitations

We are being upfront about what this prototype is **not**:

- All operational data is **simulated**. There is no real Starbucks connection.
- Not connected to a real point-of-sale (POS) system.
- No real inventory updates are written back — the system reads CSVs, never writes to them.
- The 12 RAG documents are **simulated** internal policies written for this project, not actual Starbucks documents.
- Face validity is a **plausibility check**, not proof of correctness. A `plausible` verdict does not mean the output is right; it means a human can engage with it productively.
- Human review is still required — the system does not auto-finalize customer-facing recommendations.
- All time and cost estimates in `estimates.md` are **reasoned ranges**, not measurements. A real user study would be needed to convert them into measured numbers.
- The Audit Log lives in process memory only. If you restart the server, it clears.

---

## 16. Final Project Status

| Area | Status |
|---|---|
| Backend (skills, automations, MCP tools, RAG, orchestrator, face-validity) | ✅ Complete |
| UI (Flask + Jinja + vanilla JS, 6 tabs, validation, dropdowns, polish) | ✅ Complete |
| Local tests (5 files) | ✅ 95/95 passing |
| Milestone 04 deliverables (process design, human review plan, evidence + sources, estimates, failure cases, test report, face validity, presentation outline, demo script) | ✅ Complete |
| Teammate feedback | 🔵 In progress — that's why this guide exists |
| Final demo polish | 🔵 Pending teammate input |

We are ready for teammate feedback and final demo polish.

---

*Thanks for taking the time to read this and try the site. Questions, broken cases, or "this feels off" — please flag them so we can fix before the final.*
