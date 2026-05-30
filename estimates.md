# Time, Cost, and Quality Reasoning

This document presents the reasoned before/after estimates for BrewFlow
AI's redesigned workflow. It is written for Milestone 04's "Time, Cost,
and Quality" deliverable.

---

## 1. Purpose and assumptions

**These are reasoned estimates, not Starbucks company facts.**

- BrewFlow AI is a class prototype built on the public Starbucks menu plus
  **simulated** operational CSVs (inventory, staffing, sales forecast,
  order history, promotions). No proprietary Starbucks data is used.
- Time estimates are derived from the system's deterministic workflow
  logic, the prototype outputs we observed during testing, and reasonable
  judgement about a barista or manager's task flow.
- Cost estimates use a **public, educational** assumption of $25–$35/hour
  loaded labour cost for store-level operational labour. Actual Starbucks
  costs are not used.
- All estimates are presented as **ranges**, not single point values,
  because uncertainty is high and we do not have a ground-truth study.
- Any reduction the AI provides depends on the human still reviewing
  the output. Human-review time does not disappear — it is partially
  re-shaped from "lookup time" to "verification time".

---

## 2. Before / after time estimate (per case)

The seven rows below span the workflow phases the BrewFlow orchestrator
actually implements. "Current process" describes the analogue baseline
(barista or manager doing the equivalent task with the existing register,
binders, and inventory sheet). "AI-supported process" describes the time
with BrewFlow AI in the loop.

| # | Process step | Current time per case | AI-supported time per case | Why time might change | Confidence in estimate |
|---|---|---:|---:|---|---|
| **1** | Manager pre-rush readiness check | 10–20 min | 3–7 min | Manager-readiness automation aggregates inventory + staffing + demand + promotions in a single deterministic pass; manager spends time reviewing the briefing rather than collecting raw data. | Medium |
| **2** | Customer preference intake | 2–5 min | 2–4 min | Conversation-bound; AI parses natural language but cannot speed up the customer's own decision. A small reduction comes from the system already inferring preferences from the request. | High |
| **3** | Drink recommendation | 3–8 min | 1–3 min | Inventory-aware menu ranking with explicit reason codes; barista scans 3–5 candidates with stock status rather than reciting the menu and checking stock manually. | Medium |
| **4** | Inventory / substitution check | 3–6 min | 1–2 min | Snapshot lookup is sub-second; barista verifies the surfaced low/unavailable items rather than walking to the back to count. | High |
| **5** | Order validation and confirmation | 2–5 min | 1–3 min | Structured parsing catches missing size/temperature/milk before the order is submitted; confirmation text is generated, barista checks rather than writes. | Medium-high |
| **6** | Post-rush review / audit review | 10–20 min | 4–8 min | Audit log + evidence package are already compiled per case; manager skims rather than reconstructing from receipts and notes. | Medium |
| **7** | Allergen / dietary risk handling *(safety-critical)* | 3–8 min | 3–7 min | **Roughly unchanged.** AI surfaces the risk early and routes to escalation, but the human verification step is preserved deliberately and never automated. | High |

**Aggregated case time (low–high):**

- Current process: ~33–72 min/case across all phases
- AI-supported process: ~15–34 min/case across all phases
- Plausible reduction: roughly **30–55% of total elapsed time**, with the
  largest gains in manager readiness and post-rush review (lookup-heavy)
  and the smallest gains in customer intake and allergen handling
  (conversation- and safety-bound).

> ⚠ These ranges assume the system is being used as designed: the human
> reviewer still inspects the face-validity verdict and acts on review
> queue items. They are not an estimate of fully-automated throughput.

---

## 3. Summary metric table

| Metric | Current process estimate | AI-supported process estimate | Expected change |
|---|---|---|---|
| Total time per case (all phases) | 33–72 min | 15–34 min | ↓ 30–55% lower bound |
| Human review time | ~0 (no formal step) | 3–7 min per case (designed) | ↑ formal review step replaces informal verification |
| Number of manual data lookups | 4–8 per case (binders, sheets, register) | 0–1 per case | ↓ near-zero |
| Risk of recommending an unavailable item | Medium-high (relies on barista memory + last walk-by) | Low (inventory-aware ranking with `recommendation_safe` flag) | ↓ substantially lower |
| Evidence visibility | Verbal only; little persistent record | Full Evidence Center per run (tool outputs, RAG docs, assumptions, warnings, FV) | ↑ qualitatively much higher |
| Escalation clarity | Ad-hoc; depends on barista judgement | Deterministic; allergy/medical language auto-routes to `escalate` action | ↑ clearer |
| Recommendation consistency | Varies by shift/barista | High; same scoring rules applied each run | ↑ more consistent |

---

## 4. Cost reasoning

**Educational assumption only.** We use a loaded labour rate of
**$25–$35/hour** for store-level operational labour. Actual Starbucks
compensation is not used and not implied.

### Per-case labour-cost ranges

Using the time ranges from Section 2:

| Process | Time range | $25/hr cost | $35/hr cost | Cost band |
|---|---|---:|---:|---|
| Current (analogue) | 33–72 min | $13.75 – $30.00 | $19.25 – $42.00 | **$13.75 – $42.00 / case** |
| AI-supported | 15–34 min | $6.25 – $14.17 | $8.75 – $19.83 | **$6.25 – $19.83 / case** |
| Per-case saving | ~18–38 min | $7.50 – $15.83 | $10.50 – $22.17 | **$7.50 – $22.17 / case** |

### What this does and does not mean

- These are **labour-time savings**, not total savings. They do not
  include the cost of running BrewFlow AI itself (compute, hosting), and
  they do not include the cost of getting a real version of this system
  past compliance, security review, and integration with existing POS
  systems — all of which are out of scope for this class prototype.
- A meaningful chunk of the saved labour time is **reinvested in human
  review**. That is the design, not a flaw.
- The system does **not** automate drink preparation; per-drink prep time
  is unchanged. The savings are upstream of preparation.

---

## 5. Quality reasoning

Six quality dimensions where BrewFlow AI is expected to help. Each is
described with the specific mechanism, not as a vague claim.

1. **More consistent recommendations.** Same deterministic scoring rules
   (`search_menu_by_preferences`) applied each run; popularity boost from
   `order_history.csv`; explicit reason codes (`has_caffeine`,
   `flavor_match:sweet`, `popular`, `active_promotion`). Variability
   between baristas is reduced.
2. **Fewer missed inventory issues.** Inventory-aware ranking down-ranks
   candidates whose key ingredients are low or critical-low; manager
   briefing lists `avoid_ingredients` and `caution_ingredients` before the
   shift starts.
3. **Better handling of missing order details.** Structured parsing
   detects missing size or temperature before the order reaches the
   barista; orchestrator generates a follow-up question
   (`"What size would you like — Short, Tall, Grande, or Venti?"`) rather
   than guessing.
4. **Better evidence visibility.** Every workflow run produces an
   `evidence_package` with tool outputs, RAG docs (filename, score,
   matched terms, snippet), assumptions, warnings, and quality score. A
   manager can audit any decision without re-deriving it.
5. **Stronger human-review checkpoints.** Customer-facing workflows
   always queue items for human approval; allergy/medical language always
   routes to `escalate`; missing required fields always route to
   `ask_follow_up`. The system never silently auto-approves a
   customer-facing recommendation.
6. **Better auditability.** Every workflow step and every human review
   action is logged in the audit trail with timestamp, source
   (`orchestrator` vs `user_review`), action, status, and message.
   Post-rush review is faster *and* more thorough.

---

## 6. Face-validity check for these estimates

Are these estimates plausible? Quick self-check against five obvious
failure modes for time/cost claims:

| Plausibility check | Verdict | Why |
|---|---|---|
| Are the largest gains in lookup-heavy work? | ✅ Yes | Manager readiness (lookup-heavy) and inventory check (lookup-heavy) show the biggest reductions. Customer intake (conversation-bound) and allergen handling (safety-bound) show small or zero reduction. |
| Do we assume human review goes away? | ✅ No | Human review time is explicitly preserved in the summary table (Section 3); some saved time is reinvested in reviewing the AI output. |
| Do we claim drink prep is faster? | ✅ No | Drink preparation is outside the BrewFlow scope. Drinks are still prepared individually for quality consistency per the RAG SOP `drink_quality_consistency_sop.md`. |
| Are the cost numbers grounded in a stated assumption? | ✅ Yes | $25–$35/hour is labelled an educational assumption; the calculations are derived from the time ranges, not pulled from elsewhere. |
| Could a non-believer dismiss these as marketing numbers? | ⚠ Maybe | They are reasoned, not measured. The honest mitigation: every claim uses a range, and the report explicitly says "reasoned estimate, not company fact" up front. A real next step would be a small barista/manager user study to replace the ranges with measurements. |

---

## What we cannot estimate without more data

- Actual customer-perceived wait time (we don't measure latency to first
  recommendation in this prototype).
- True allergen-incident rate before vs after (no real safety incident
  data exists for this simulated branch).
- Promotion uplift / conversion rate (would need real till data).
- Customer satisfaction lift (would need a survey).

These are honest gaps. A production deployment would need real-world
A/B-test data to convert the ranges above into measured deltas.
