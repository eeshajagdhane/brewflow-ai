"""BrewFlow AI — deterministic face-validity layer (Milestone 04).

Face validity is **not** a skill, MCP tool, or RAG tool.  It is an
evaluation/review layer that inspects an assembled workflow output and
produces a plain-English plausibility judgement that the future UI can
render in the Evidence Center and Review Queue cards.

The check is fully deterministic:
  * No LLM calls.
  * No network access.
  * Inputs are the already-built workflow artifacts.

`generate_face_validity_check()` is the public entry point.

Returned dict shape::

    {
      "status": "plausible | needs_review | weak | not_applicable",
      "confidence": "high | medium-high | medium | low",
      "supporting_reasons": [str, ...],
      "concerns": [str, ...],
      "human_review_required": bool,
      "evidence_quality": {"score": float, "label": str},
      "anchors_used": [str, ...],
      "recommended_action": "approve | review | ask_follow_up | rerun | escalate",
    }

Design rule: face validity means *"reasonable enough to review/investigate,"*
**not** *"proven correct."*  For customer-facing workflows (barista
recommendation, order builder, order summary), `status="needs_review"` is a
fully successful and intentional state — human approval is part of the
designed process.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Allergy / medical language anywhere in user input, final output, warnings,
# or review queue items.  Use the same vocabulary as the order builder so the
# behaviour is consistent across the system.
_ALLERGY_PATTERN = re.compile(
    r"\b(allerg\w*|intoleran\w*|anaphyla\w*|epi.?pen|celiac|lactose|"
    r"nut.?allerg\w*|dairy.?allerg\w*|gluten.?intoleran\w*)\b",
    re.IGNORECASE,
)

_MEDICAL_PATTERN = re.compile(
    r"\b(medical|medication|prescri\w*|diabet\w*|pregnan\w*|hypertens\w*)\b",
    re.IGNORECASE,
)

# Workflow types where a non-empty review queue is part of the *designed*
# process (human approval before customer-facing use).  For these, having a
# review_queue does not by itself indicate a problem, but it does mark the
# workflow as `needs_review` rather than `plausible`.
_CUSTOMER_FACING_WORKFLOWS = {
    "barista_recommendation",
    "order_builder",
    "order_summary",
    "full_workflow",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scan_text(*sources: object) -> str:
    """Flatten arbitrary nested sources into a single lowercase string for regex."""
    parts: list[str] = []
    for src in sources:
        if src is None:
            continue
        parts.append(str(src))
    return " ".join(parts).lower()


def _safe_signal_text(
    user_input: dict,
    warnings: list,
    review_queue: list,
) -> str:
    """Build the text blob used for allergy / medical signal detection.

    We deliberately exclude `final_output` here because it embeds RAG document
    metadata (filenames + snippets).  Documents such as
    `dietary_allergen_guidance.md` contain the word *allergen* in their
    snippet, which would otherwise produce a false-positive escalate even on
    requests that never mentioned allergies.

    Anything the orchestrator considers a real allergy signal is already
    mirrored into `warnings` and `review_queue`, so those sources are
    sufficient and safe to scan.
    """
    parts: list[str] = []

    if user_input:
        # The whole user_input dict is small and user-controlled — safe to
        # stringify in full.
        parts.append(str(user_input))

    for w in warnings or []:
        parts.append(str(w))

    for q in review_queue or []:
        if isinstance(q, dict):
            # Scan only the labels/reasons added by the orchestrator, not the
            # embedded `data` blob (which can include arbitrary tool output).
            parts.append(str(q.get("item", "")))
            parts.append(str(q.get("reason", "")))
            parts.append(str(q.get("follow_up_question", "")))
            parts.append(str(q.get("customer_request", "")))
        else:
            parts.append(str(q))

    return " ".join(parts).lower()


def _collect_missing_fields(final_output: dict, review_queue: list) -> list[str]:
    """Aggregate every missing-field signal in the workflow artifacts."""
    missing: list[str] = []
    if isinstance(final_output, dict):
        mf = final_output.get("missing_fields") or []
        if isinstance(mf, list):
            missing.extend(str(m) for m in mf)
        # full_workflow nests the order under "order"
        order = final_output.get("order")
        if isinstance(order, dict):
            mf2 = order.get("missing_fields") or []
            if isinstance(mf2, list):
                missing.extend(str(m) for m in mf2)
    for q in review_queue or []:
        if isinstance(q, dict):
            label = str(q.get("item", "")).lower()
            if "missing" in label:
                mf3 = q.get("missing_fields") or []
                if isinstance(mf3, list) and mf3:
                    missing.extend(str(m) for m in mf3)
                else:
                    # The review_queue item itself flags a missing field.
                    missing.append(label)
    # Deduplicate while preserving order
    return list(dict.fromkeys(missing))


def _has_review_queue_topic(review_queue: list, keyword: str) -> bool:
    keyword = keyword.lower()
    for q in review_queue or []:
        if isinstance(q, dict) and keyword in str(q.get("item", "")).lower():
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_face_validity_check(
    workflow_type: str,
    final_output: dict,
    evidence_package: dict,
    warnings: Optional[list] = None,
    review_queue: Optional[list] = None,
    assumptions: Optional[list] = None,
    user_input: Optional[dict] = None,
) -> dict:
    """Produce a deterministic plausibility judgement for a workflow output.

    See module docstring for the full contract.  This function is pure and
    side-effect free; it never raises on missing keys.
    """
    warnings = warnings or []
    review_queue = review_queue or []
    assumptions = assumptions or []
    user_input = user_input or {}

    # ---------------- Not-applicable short-circuit ----------------
    if not workflow_type:
        return {
            "status": "not_applicable",
            "confidence": "low",
            "supporting_reasons": [],
            "concerns": ["No workflow type provided; face validity cannot be evaluated."],
            "human_review_required": True,
            "evidence_quality": {"score": 0.0, "label": "weak"},
            "anchors_used": [],
            "recommended_action": "rerun",
        }

    # ---------------- Evidence summary ----------------
    if not isinstance(evidence_package, dict):
        evidence_package = {}
    tool_outputs = evidence_package.get("tool_outputs") or []
    rag_results = evidence_package.get("rag_results") or evidence_package.get("rag_snippets") or []
    evidence_count = int(evidence_package.get("evidence_count", len(tool_outputs) + len(rag_results)) or 0)
    quality_score = float(evidence_package.get("quality_score", 0.0) or 0.0)
    quality_label = str(evidence_package.get("quality_label", "weak") or "weak")

    # ---------------- Anchors ----------------
    anchors_used: list[str] = []
    if tool_outputs:
        anchors_used.append("MCP/tool output")
        anchors_used.append("CSV operational data")
    if rag_results:
        anchors_used.append("RAG internal guidance")
    if review_queue:
        anchors_used.append("Human review queue")
    if assumptions:
        anchors_used.append("Simulated operational assumptions")
    # Every BrewFlow workflow response carries an audit log.
    anchors_used.append("Audit log")

    # ---------------- Signal detection ----------------
    # IMPORTANT: do NOT scan the full final_output for allergy/medical
    # language — it embeds RAG doc metadata (e.g. `dietary_allergen_guidance.md`
    # snippets) that would produce false-positive escalations on benign
    # requests.  The orchestrator already mirrors any real allergy signal
    # into `warnings` and `review_queue`, so those sources are both
    # sufficient and safe.
    signal_text = _safe_signal_text(user_input, warnings, review_queue)
    allergy_detected = bool(_ALLERGY_PATTERN.search(signal_text))
    medical_detected = bool(_MEDICAL_PATTERN.search(signal_text))
    missing_fields = _collect_missing_fields(final_output if isinstance(final_output, dict) else {}, review_queue)
    inventory_unavailable = _has_review_queue_topic(review_queue, "inventory_unavailable")
    stale_snapshot = any("latest prior" in str(w).lower() for w in warnings)

    # ---------------- Supporting reasons ----------------
    supporting_reasons: list[str] = []
    if tool_outputs:
        supporting_reasons.append("The output is supported by tool evidence.")
    if rag_results:
        supporting_reasons.append("Relevant internal RAG guidance was retrieved.")
    if review_queue:
        supporting_reasons.append("Human review is required before customer-facing use.")

    # Inventory-aware recommendation reasoning
    if workflow_type in ("barista_recommendation", "full_workflow"):
        if any("inventory" in str(t.get("tool", "")).lower() for t in tool_outputs if isinstance(t, dict)):
            supporting_reasons.append("The recommendation uses available inventory evidence.")

    # No-batching quality rule — appears in the order builder / summary prep notes
    prep_text = ""
    if isinstance(final_output, dict):
        prep_text = " ".join(final_output.get("prep_notes") or [])
        nested_order = final_output.get("order")
        if isinstance(nested_order, dict):
            prep_text += " " + " ".join(nested_order.get("prep_notes") or [])
    if "individually" in prep_text.lower():
        supporting_reasons.append(
            "The workflow follows the rule that drinks are prepared individually for quality consistency."
        )
        if "No-batching quality rule" not in anchors_used:
            anchors_used.append("No-batching quality rule")

    # ---------------- Concerns ----------------
    concerns: list[str] = []
    if stale_snapshot:
        concerns.append("Inventory evidence uses a latest-prior snapshot rather than exact same-day data.")
    if missing_fields:
        concerns.append("The customer request is vague or missing required fields.")
    if allergy_detected or medical_detected:
        concerns.append("Allergy or medical-sensitive language requires human review.")
    if evidence_count == 0 or quality_label.lower() == "weak":
        concerns.append("Evidence quality is weak or missing.")
    if inventory_unavailable:
        concerns.append("One or more required ingredients are unavailable in the inventory snapshot.")
    if warnings and not any(c.startswith("The workflow returned warnings") for c in concerns):
        concerns.append(f"The workflow returned {len(warnings)} warning(s) that require review.")

    # ---------------- Status + recommended action ----------------
    # Defaults
    status = "plausible"
    recommended_action = "approve"

    # Weak evidence cascade (lowest baseline)
    if not final_output:
        status = "weak"
        recommended_action = "rerun"
        if "No final output produced; workflow may have errored." not in concerns:
            concerns.append("No final output produced; workflow may have errored.")
    elif evidence_count == 0 and not tool_outputs and not rag_results:
        status = "weak"
        recommended_action = "review"
    elif quality_label.lower() == "weak":
        status = "weak"
        recommended_action = "review"

    # Customer-facing workflows with a populated review queue are
    # intentionally `needs_review`, not `weak`.
    if (
        status == "plausible"
        and review_queue
        and workflow_type in _CUSTOMER_FACING_WORKFLOWS
    ):
        status = "needs_review"
        recommended_action = "review"

    # Missing fields → ask_follow_up (overrides plausible/weak, but not allergy)
    if missing_fields:
        status = "needs_review"
        if recommended_action != "escalate":
            recommended_action = "ask_follow_up"

    # Allergy / medical takes highest priority — escalate, regardless of evidence
    if allergy_detected or medical_detected:
        status = "needs_review"
        recommended_action = "escalate"

    # ---------------- Confidence ----------------
    if status == "plausible":
        if quality_score >= 0.7 and len(warnings) <= 1:
            confidence = "high"
        elif quality_score >= 0.6:
            confidence = "medium-high"
        else:
            confidence = "medium"
    elif status == "needs_review":
        if quality_score >= 0.7:
            confidence = "medium-high"
        elif quality_score >= 0.5:
            confidence = "medium"
        else:
            confidence = "medium" if not (allergy_detected or medical_detected) else "low"
    elif status == "weak":
        confidence = "low"
    else:  # not_applicable (unreachable here, but kept for safety)
        confidence = "low"

    human_review_required = bool(
        review_queue or allergy_detected or medical_detected or missing_fields
    )

    # Deduplicate while preserving order
    supporting_reasons = list(dict.fromkeys(supporting_reasons))
    concerns = list(dict.fromkeys(concerns))
    anchors_used = list(dict.fromkeys(anchors_used))

    return {
        "status": status,
        "confidence": confidence,
        "supporting_reasons": supporting_reasons,
        "concerns": concerns,
        "human_review_required": human_review_required,
        "evidence_quality": {"score": quality_score, "label": quality_label},
        "anchors_used": anchors_used,
        "recommended_action": recommended_action,
    }
