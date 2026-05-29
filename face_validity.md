# Face Validity in BrewFlow AI

## 1. What "face validity" means here

In BrewFlow AI, **face validity** is a deterministic plausibility check on a
completed workflow output. It answers one question:

> *"Does this AI-assisted result look reasonable enough — given the evidence,
> the warnings, and the human-review checkpoints — for a manager or barista to
> review and act on?"*

It is **not** a correctness proof. It is **not** an LLM judge. It is a
rules-based summary that the future UI uses to render an at-a-glance
plausibility card.

## 2. How BrewFlow AI checks face validity

`utils/face_validity.generate_face_validity_check()` reads the artifacts that
the orchestrator has already assembled — `final_output`, `evidence_package`,
`warnings`, `review_queue`, `assumptions`, and the original `user_input` — and
returns one structured object:

```json
{
  "status":           "plausible | needs_review | weak | not_applicable",
  "confidence":       "high | medium-high | medium | low",
  "supporting_reasons": ["..."],
  "concerns":           ["..."],
  "human_review_required": true,
  "evidence_quality":   {"score": 0.85, "label": "strong"},
  "anchors_used":       ["MCP/tool output", "RAG internal guidance", ...],
  "recommended_action": "approve | review | ask_follow_up | rerun | escalate"
}
```

The orchestrator attaches this object as `response["face_validity"]` on every
workflow result. No LLM is called. No data files are modified. No external
service is contacted.

## 3. Where face validity appears in the future UI

| UI surface | Use of `face_validity` |
|---|---|
| **Evidence Center** | Render a "Face Validity" card showing `status`, `confidence`, `evidence_quality`, the `anchors_used` chips, and the `supporting_reasons` / `concerns` lists side by side. |
| **Review Queue** | Tag each queued item with the workflow's `status` and `recommended_action` so the reviewer sees *why* the system asked for review (e.g. `escalate` because allergy language was detected). |
| **Final workflow output card** | A small badge — green for `plausible`, yellow for `needs_review`, red for `weak`, grey for `not_applicable` — beside the AI summary. |

## 4. Evidence anchors used

The `anchors_used` list documents *what kind* of evidence underpins the
judgement. Possible values:

- **CSV operational data** — pulled from `data/raw/` (menu, inventory, staff
  schedule, sales forecast, promotions, order history).
- **MCP/tool output** — outputs of the six MCP-style tools in
  `mcp_servers/brewflow_mcp_server.py`.
- **RAG internal guidance** — passages retrieved from the 12 documents in
  `rag/knowledge_base/`.
- **Human review queue** — items the workflow explicitly queued for a person
  to approve, edit, reject, or escalate.
- **Audit log** — chronological record of every step the workflow ran.
- **Simulated operational assumptions** — anywhere the workflow had to
  substitute a default (e.g. baseline required headcount).
- **No-batching quality rule** — barista best-practice that drinks are
  prepared individually for quality consistency; surfaces in order builder
  and order summary prep notes.

## 5. What causes `status = "needs_review"`

The check escalates to `needs_review` (rather than `plausible`) whenever any
of these signals appear:

- **Allergy or medical-sensitive language** in the customer request, final
  output, warnings, or review queue → `recommended_action = "escalate"`.
- **Missing order fields** in `final_output.missing_fields` or in a
  `review_queue` entry tagged `order_missing_fields` → `ask_follow_up`.
- **Ambiguous item names** that resolved through the menu-search fallback
  rather than the exact mapping table.
- **Low-stock or unavailable ingredients** flagged by the inventory check.
- **Conflicting evidence** — e.g. a `Healthy` status alongside a stale
  snapshot warning.
- **Weak evidence quality** — `quality_score = 0.0` or `quality_label =
  "weak"` downgrades the status to `weak`.

For customer-facing workflows (barista recommendation, order builder, order
summary, full workflow), a populated review queue is part of the *designed*
process — `needs_review` here is a normal, successful state, not a failure.

## 6. Important limitation

Face validity is a **plausibility heuristic**, not a correctness proof. A
`plausible` verdict does **not** mean the recommendation is right; it means
the output is grounded enough in tool evidence and policy retrieval that a
human reviewer can engage with it productively. Conversely, `needs_review`
does not mean the AI failed — for safety-sensitive paths (allergy, missing
fields), it is exactly the expected outcome.

The face-validity layer is meant to **support** human review, never replace
it.
