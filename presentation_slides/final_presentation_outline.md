# BrewFlow AI — Final Presentation Outline

**Project:** BrewFlow AI: Starbucks Branch Daily Operations and Order Fulfillment
**Milestone:** 04 — Final Presentation
**Total runtime target:** ~10 minutes + Q&A
**Slides:** 9
**Companion demo script:** [`demo_script.md`](demo_script.md)

> All slides should reinforce: simulated branch prototype, public menu
> data + simulated operational CSVs, no proprietary Starbucks data.

---

## Slide 1 — Project overview: BrewFlow AI

**Bullets:**
- BrewFlow AI is an AI-supported **operations console** for a simulated
  Starbucks branch — built for MGTA 495 GenAI for Business, Group 8.
- It chains **automations, MCP-style tools, RAG retrieval, AI skills, and
  a face-validity layer** into one workflow that runs manager readiness,
  barista recommendation, and order building end-to-end.
- The UI is a live Flask web console; every result is a real orchestrator
  call against local CSV data — **nothing is mocked or canned**.
- The system is designed around **human-in-the-loop review**: every
  customer-facing recommendation and order requires a barista or manager
  to approve before delivery.
- *Note framed up front:* "We use the public Starbucks menu and **simulated**
  operational data. No proprietary Starbucks data is used."

**Speaker notes:**
Open with the role we're playing — an internal operations console for
baristas and managers, not a customer ordering app. Make the simulated-
data scope clear immediately so the rest of the talk lands honestly.

**Show in UI:** Open `http://127.0.0.1:5000` — the BrewFlow AI Operations
Console home with the simulated-data chip visible in the top bar.

---

## Slide 2 — Current business process and pain points

**Bullets:**
- Today's baseline (analogue): manager walks the back-of-house, baristas
  rely on memory + paper notes, recommendations vary by shift, orders
  fail at the register when fields are missing.
- Pain points we redesigned around:
  - Inventory issues caught **too late** (after a recommendation)
  - Allergy / medical signals handled **ad-hoc** — depends on barista
  - Post-rush review is **verbal**, not auditable
  - Recommendations are **inconsistent** between baristas
  - Manager pre-shift prep is **10–20 minutes of lookups**
- These pain points came from process analysis in Milestones 02–03 and
  are the basis for the time/cost estimates in `estimates.md`.

**Speaker notes:**
Frame the existing pains as concrete and measurable. The slide is your
"why we built this" — it sets up Slide 7 (the time/cost reasoning) and
Slide 8 (testing for the failure modes the redesign should catch).

**Show in UI:** none — this is a context slide.

---

## Slide 3 — Final AI-supported workflow

**Bullets:**
- One redesigned chain: **Manager Readiness → Barista Recommendation → Order Builder → Evidence + Review + Audit**.
- Colour-coded by **who does the work** (human green / AI red / human
  review purple / collaboration orange / tool blue / RAG yellow).
- Critical safety routing built in: allergy / medical language always
  escalates; missing required order fields always trigger a follow-up
  question; weak evidence always downgrades face validity.
- Drinks are still **prepared individually for quality consistency** —
  no automation of drink prep.

**Speaker notes:**
Walk the audience left-to-right across the Mermaid diagram from
`ai_process_design.md`. Point at the purple (human review) blocks and
emphasise that these are intentional, not bottlenecks.

**Show in UI:** Manager View tab → run a readiness check
(SD001 / 2024-01-15 / 8:00 AM) to show the readiness card briefly before
moving on.

---

## Slide 4 — System architecture: skills, automations, MCP, RAG

**Bullets:**
- **5 AI skills** (`skills/*/SKILL.md`) — natural-language generation
  for recommendation, order summary, etc.
- **4 deterministic automations** (`automations/`) — inventory
  monitoring, staffing gap, demand rush detection, manager briefing.
- **6 MCP-style tools** (`mcp_servers/brewflow_mcp_server.py`) —
  callable Python with JSON envelopes: menu lookup, preference search,
  inventory status, rush detection, staffing gap, order builder.
- **12 RAG docs** (`rag/knowledge_base/`) — simulated SOPs, policies,
  training guides. Retrieved by deterministic keyword scoring.
- **Face-validity layer** (`utils/face_validity.py`) — deterministic
  plausibility verdict on every workflow output, not an LLM judge.
- All orchestrated by `scripts/orchestrator.py` into 4 workflow
  functions exposed to the Flask UI.

**Speaker notes:**
Spend ~30 seconds per layer. Emphasise that we use the *right tool for
the job*: deterministic Python for math and lookups, RAG for policy
context, AI skills only for the natural-language synthesis. This is the
"explainable AI" pattern, not "throw everything at an LLM".

**Show in UI:** Use the **🥛 Brown Sugar Oatmilk Shaken Espresso** quick
start to pre-fill, then click ▶ Run Full Workflow. Once results land,
hover the Evidence Center badge in the sidebar to show the counts updating.

---

## Slide 5 — Live UI walkthrough

**Bullets:**
- Single-page Flask + Jinja + vanilla JS app, no framework, no build step.
- Six tabs: **Full Workflow (main)**, Manager, Barista, Order Builder,
  Evidence Center, Review Queue + a collapsible **Audit Log** drawer.
- Inputs are validated **before submit**: store and hour are required
  dropdowns; date and request fields are required; per-field error
  messages point exactly to what's missing.
- The Audit Log drawer is collapsed by default but clearly visible so
  every workflow run and every human-review click is traceable.
- All workflow results are **live** — refresh and click Run again to get
  a fresh run_id.

**Speaker notes:**
This is where most of the demo time goes (see `demo_script.md`).
Show the dropdowns, the inline validation if an input is missing, and
the way the sidebar badges update after a run.

**Show in UI:** Walk through the Full Workflow tab live (5–6 minutes
total in the script).

---

## Slide 6 — Evidence, face validity, and human review

**Bullets:**
- Every workflow output ships with **6 evidence anchors**: MCP/tool
  output, CSV operational data, RAG internal guidance, human review
  queue, audit log, no-batching quality rule.
- **Face Validity card** on every run: status (plausible / needs_review
  / weak / not_applicable), confidence, anchors used as chips,
  supporting reasons, concerns, recommended action.
- **Review Queue** lists everything the workflow flagged for a human;
  filter chips (All / Pending / Approved / Escalated) scope what's shown;
  four action buttons (Approve / Edit / Reject + Rerun / Escalate) all
  recorded to the audit log.
- For customer-facing flows, `status = needs_review` is the **designed
  outcome**, not a failure — human approval is built into the process.
- The face-validity false-positive fix (RAG content leaking "allergen"
  into the scan) is a real lesson — covered on Slide 8.

**Speaker notes:**
Walk through the Evidence Center sub-tabs after the live run. Highlight
the face_validity card colour (yellow = needs review, by design). Then
switch to the Review Queue and click Approve on one item — show the
audit log entry being appended.

**Show in UI:** Evidence Center → all 5 sub-tabs. Review Queue → click
Approve on one item, expand audit drawer to show the new entry.

---

## Slide 7 — Time, cost, and quality estimates

**Bullets:**
- Reasoned estimates, not Starbucks company facts. All ranges, all
  labelled as assumptions. Cost uses $25–$35/hour as an educational
  assumption.
- **Per-case time:** 33–72 min (analogue) → 15–34 min (AI-supported).
  Plausible reduction roughly **30–55%**, largest gains in lookup-heavy
  steps (manager readiness, post-rush review).
- **Cost band:** ~$13.75–$42.00/case → ~$6.25–$19.83/case.
- **Quality:** more consistent recommendations, fewer missed inventory
  issues, structured handling of missing order details, visible
  evidence, stronger review checkpoints, full auditability.
- Honest gaps acknowledged: no user study, no real wait-time data, no
  promotion uplift measurement.

**Speaker notes:**
Show the summary table from `estimates.md`. Be explicit about what is
*not* claimed (drink prep speedup, customer satisfaction lift,
allergen incident reduction — we don't have data to claim those).

**Show in UI:** none — reference `estimates.md` and the orchestrator
audit log.

---

## Slide 8 — Testing results and fixes

**Bullets:**
- **95/95 local tests passing**, no external API keys.
- Coverage: MCP tools (27), RAG retrieval (16), workflow orchestration
  (23), face validity (15), UI routes (14).
- Three most common failure patterns surfaced during development:
  1. Input ambiguity (missing fields, fuzzy item names)
  2. Missing / weak evidence (out-of-range dates, sparse history)
  3. Over-triggered safety signals (the RAG-leak false escalation)
- **Headline before/after fix:** face validity used to escalate benign
  requests because retrieved RAG docs (e.g. `dietary_allergen_guidance.md`)
  contained the word "allergen". Fix: scan only safe sources
  (`user_input`, `warnings`, `review_queue` labels). Real allergy
  requests still escalate; benign ones no longer do. Locked in by two
  regression tests.

**Speaker notes:**
Show the test counts. Walk through the before/after of the face-validity
false-positive in concrete terms — this is the strongest example of the
team finding and fixing a real flaw in development.

**Show in UI:** none. Reference `test_report.md` for the full report.

---

## Slide 9 — Limitations and next steps

**Bullets:**
- **Limitations of this prototype:**
  - All operational data is **simulated**; no real Starbucks data
  - No persistent audit storage (in-process only)
  - No real wait-time / customer satisfaction measurement
  - Dairy-free heuristic uses `Vegan=Yes` as a proxy (documented)
  - No LLM-judge semantic relevance test on retrieved RAG content
- **Next steps** if this moved beyond prototype:
  - Real inventory streaming from POS
  - Database-backed audit log
  - User study to convert reasoned estimates into measured deltas
  - DeepEval / LLM-judge layer for RAG semantic relevance
  - Structured `Dairy_Free` / `Nut_Free` columns in the menu
  - Compliance + security review before any real customer contact
- **What we stand by:** the architecture, the human-in-the-loop story,
  the auditability, and the face-validity approach to plausibility checks.

**Speaker notes:**
End on what *can* go to a production conversation versus what would need
more data. Avoid overclaiming. Re-iterate the simulated-data scope one
final time.

**Show in UI:** Return to the Audit Log drawer fully expanded to show
the full trace of the demo's workflow + review actions. Close with the
sim-chip note in the top bar visible.

---

## Slide-deck delivery checklist

- [ ] Flask UI is running locally (`uv run python ui/app.py`)
- [ ] Audit Log cleared before starting (Clear button in drawer)
- [ ] Browser open to `http://127.0.0.1:5000` on Full Workflow tab
- [ ] One pre-filled demo path tested 5 minutes before the talk
- [ ] One allergy edge-case tested 5 minutes before the talk
- [ ] Terminal visible (or split-screen) to show live POST log lines
- [ ] `estimates.md`, `test_report.md`, `ai_process_design.pdf`,
      `face_validity.md` open in tabs as backup if the UI hits an issue

See [`demo_script.md`](demo_script.md) for the exact 10-minute timed
walkthrough.
