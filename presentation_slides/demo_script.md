# BrewFlow AI — 10-Minute Live Demo Script

**Target runtime:** 10 minutes
**Setup:** UI running at `http://127.0.0.1:5000`, Audit Log cleared, Full Workflow tab open.

This script complements [`final_presentation_outline.md`](final_presentation_outline.md). Each block has a timer, the exact inputs to type or pre-fill, and the talking points to hit while clicking.

---

## 0:00 – 1:00  Project overview *(no UI yet)*

**Say:**
> "BrewFlow AI is an AI-supported operations console for a *simulated* Starbucks branch — built for MGTA 495. It chains automations, MCP tools, RAG retrieval, AI skills, and a face-validity layer into one workflow that runs manager readiness, barista recommendation, and order building end-to-end. Every result you'll see is a real call to local Python and CSV data — nothing is mocked. We use the public Starbucks menu and *simulated* operational data, not proprietary Starbucks data."

**Show:** Slide 1.

---

## 1:00 – 2:00  Current process and pain points *(slide only)*

**Say:**
> "Today's baseline is analogue: the manager walks the back-of-house, baristas rely on memory, recommendations vary by shift, and orders fail at the register when fields are missing. We redesigned around four pains: late inventory issues, ad-hoc allergy handling, no audit trail, and inconsistent recommendations."

**Show:** Slide 2.

---

## 2:00 – 3:00  Architecture *(slide + open the UI)*

**Say:**
> "Five AI skills, four deterministic automations, six MCP-style tools, twelve RAG documents, and a face-validity layer. All orchestrated into four workflow functions exposed to a Flask UI. Right tool for the job — deterministic Python for math, RAG for policy, AI only for the natural-language synthesis."

**Show:** Slide 4, then click into the UI in the browser.

---

## 3:00 – 6:00  Live UI demo — Full Workflow main path *(3 minutes)*

### Step 1 — Pre-fill the form (3:00 – 3:30)

**Click:** the **☕ Iced Vanilla Latte** quick-start card under "Common Quick Starts".

The form auto-populates with:
- **Store ID:** SD001
- **Date:** 2024-01-15
- **Hour:** 8:00 AM
- **Customer request:** *"I want an iced latte, something smooth and lightly sweet."*
- **Raw order:** *"grande iced vanilla latte with oat milk"*
- Preferences: temperature=iced, sweetness=medium, milk_preference=oat milk, caffeine=medium, coffee_preference=coffee

**Say:**
> "Quick starts only pre-fill the inputs. They never produce outputs. The user always clicks Run."

> *(Optional)* "Notice every required field has a red asterisk. Optional fields are labelled (Optional). If I tried to run with the store empty, you'd see an inline error message under that specific field."

### Step 2 — Run the workflow (3:30 – 4:00)

**Click:** the green **▶ Run Full Workflow** button.

**Watch:**
- Progress tracker lights up step-by-step (Input → Manager Check → Recommendation → Order Build → Complete)
- Status banner appears (yellow needs_review — by design for customer-facing flows)
- Run Summary card shows: status=needs_review, steps=~11, evidence quality≈0.87, FV=needs_review (yellow), review items=2, audit entries=4–6

**Say:**
> "Real orchestrator call — all four workflow functions ran. The status is needs_review because customer-facing flows are designed to route through human approval — that's not a failure."

### Step 3 — Walk the result cards (4:00 – 5:00)

**Scroll to:** the Face Validity card (yellow left-border).

**Say while pointing:**
> "Status: needs_review. Recommended action: review. Confidence: medium-high. Evidence quality: 0.87 — strong. The anchors chips show which evidence the verdict drew from: MCP/tool output, CSV operational data, RAG internal guidance, human review queue, audit log."

**Expand:** the three collapsible output cards (Manager Readiness → Recommendation → Order Builder).

**Say while expanding each:**
- Manager: *"demand=high, forecast≈211 orders, staffing_gap=1, three recommended manager actions."*
- Recommendation: *"5 ranked candidates with reason codes — `has_caffeine`, `flavor_match:sweet`, `popular`. Inferred preferences box shows what the system parsed from the customer's natural-language request."*
- Order Builder: *"structured order parsed correctly — item=Iced Vanilla Latte, size=Grande, temp=Iced, milk=Oat Milk. Prep notes include 'Prepare individually for quality consistency' from the RAG SOP."*

### Step 4 — Switch to Evidence Center (5:00 – 5:30)

**Click:** "🔍 Evidence Center" in the sidebar — point at the blue badge showing the evidence count.

**Click through:** the 5 sub-tabs at the top.

**Say briefly per tab:**
- Tool / Data: *"Each MCP tool and automation that fired, with status pills."*
- RAG: *"Three docs retrieved with title, filename, score, matched terms as chips, and snippets."*
- Assumptions: *"Anywhere the system filled in a default."*
- Warnings: *"Latest-prior snapshot, dairy-free heuristic, rush forecast warnings."*
- Quality + Face Validity: *"Face validity verdict plus the quality score breakdown."*

### Step 5 — Switch to Review Queue (5:30 – 6:00)

**Click:** "✅ Review Queue" in the sidebar.

**Point at:** the queued items (recommendation_candidates, possibly an inventory note).

**Click:** Approve on one item.

**Say:**
> "One click records the approval. The card gets a green left border and an 'approved' pill. The Audit Log just got a new `user_review · approve` entry. Filter chips let me scope to Pending / Approved / Escalated."

---

## 6:00 – 7:00  Evidence Center + Review Queue deeper *(if time)*

**Open:** the Audit Log drawer at the bottom.

**Say:**
> "Every workflow run and every human-review click is logged here with timestamp, source, action, and message. Refresh keeps it current; Clear wipes it. Search filters in-place."

**Filter:** by typing `allergy` (won't match yet; just demo the search).

**Collapse:** the drawer.

---

## 7:00 – 8:00  Face validity + human-in-the-loop — Edge case demo

### Step 1 — Allergy-sensitive edge case (7:00 – 7:45)

**Type into Full Workflow form** (manually overriding the previous fill):
- **Store ID:** SD001
- **Date:** 2024-01-15
- **Hour:** 8:00 AM
- **Customer request:** *"I have a nut allergy and want something dairy-free."*
- **Raw order:** *"iced latte with oat milk"* (intentionally no size)

**Click:** ▶ Run Full Workflow.

**Watch:**
- Face Validity card: **yellow**, status=needs_review, recommended_action=**escalate** (not just `review`).
- Concerns list includes *"Allergy or medical-sensitive language requires human review."*
- The customer-request side also produces *"missing_fields: ['size']"* on the Order Builder phase.
- Review Queue gains: `recommendation_allergy_review` AND `order_missing_fields`.

**Say:**
> "Two safety signals at once. The system never auto-approves an allergen-flagged recommendation, and it never proceeds with a missing required field. The face validity verdict promotes recommended_action to `escalate` — the strongest level."

### Step 2 — Click Escalate (7:45 – 8:00)

**Click:** Escalate on the `recommendation_allergy_review` card.

**Modal opens.** Type: *"Verify against the physical allergen guide before confirming any alternative drink."*

**Click:** Submit.

**Say:**
> "The escalation note is now in the audit log alongside the original recommendation. A senior manager sees both the AI's verdict and the human's reasoning."

---

## 8:00 – 9:00  Testing + failure cases

**Switch to slide 8 + reference `test_report.md`.**

**Say:**
> "95 local tests passing — MCP tools, RAG, orchestration, face validity, UI routes. No external API keys. Our headline before/after fix: face validity used to escalate benign requests because retrieved RAG docs included the word *allergen*. We fixed it by scanning only safe signal sources — user input, warnings, and review queue labels. Real allergy requests still escalate. Benign ones no longer do. Two regression tests lock it in."

**Optional — show the proof live:**

Type into the form:
- **Customer request:** *"Something hot and caffeinated"*
- **Raw order:** *"venti hot latte"*

**Click:** Run.

**Show:** Face Validity = `needs_review` with action = `review` (not `escalate`). No false escalation.

---

## 9:00 – 10:00  Limitations and next steps

**Show:** Slide 9.

**Say:**
> "Limitations: all operational data is *simulated*. The audit log lives in process memory, not a database. The dairy-free flag uses Vegan=Yes as a documented heuristic. No real customer wait-time or satisfaction data exists for this prototype, so the time/cost numbers in our `estimates.md` are reasoned ranges, not measurements."

> "Next steps if this moved past prototype: real inventory streaming from POS; database-backed audit log; a small user study to convert ranges into measurements; a DeepEval / LLM-judge layer for RAG semantic relevance; structured Dairy_Free / Nut_Free columns in the menu; compliance and security review before any real customer contact."

> "What we stand by: the architecture, the human-in-the-loop story, the auditability, and the deterministic face-validity approach. Thanks — questions?"

---

## Exact demo inputs (copy-paste reference)

### Main demo (3:00 – 6:00)

| Field | Value |
|---|---|
| store_id | SD001 |
| date | 2024-01-15 |
| hour | 8:00 AM *(backend: 8)* |
| customer_request | I want an iced latte, something smooth and lightly sweet. |
| raw_order | grande iced vanilla latte with oat milk |
| preferences.temperature | iced |
| preferences.sweetness | medium |
| preferences.milk_preference | oat milk |
| preferences.caffeine | medium |
| preferences.coffee_preference | coffee |

### Edge-case demo (7:00 – 8:00)

| Field | Value |
|---|---|
| store_id | SD001 |
| date | 2024-01-15 |
| hour | 8:00 AM *(backend: 8)* |
| customer_request | I have a nut allergy and want something dairy-free. |
| raw_order | iced latte with oat milk *(intentionally no size)* |

### Benign-request proof (8:00 – 9:00)

| Field | Value |
|---|---|
| store_id | SD001 |
| date | 2024-01-15 |
| hour | 8:00 AM *(backend: 8)* |
| customer_request | Something hot and caffeinated |
| raw_order | venti hot latte |

---

## If something goes wrong on stage

| Failure | Recovery |
|---|---|
| UI doesn't load | Show `ai_process_design.pdf` + walk the Mermaid diagram from `ai_process_design.md` |
| A workflow returns an error banner | Open the audit log drawer to show the error is logged + traceable; then re-run with the **🧊 Vanilla Sweet Cream Cold Brew** quick start as a known-good fallback |
| You forget what the face validity card means | Point at the colour and read the supporting reasons / concerns lists aloud — that's exactly the audience-facing explanation |
| Timer running long | Skip the Audit Log search demo at 6:00–7:00; jump directly to the allergy edge case at 7:00 |
