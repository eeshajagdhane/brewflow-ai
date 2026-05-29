"""BrewFlow AI — face-validity layer tests.

All tests run locally with no external API keys.

Coverage:
  * Direct unit tests on `generate_face_validity_check` for the four headline
    scenarios called out in the Milestone 04 brief.
  * Orchestrator-integration tests confirming that every workflow response
    now carries a properly-structured `face_validity` object.
"""

from __future__ import annotations

import pytest

from scripts.orchestrator import (
    run_barista_recommendation,
    run_full_workflow,
    run_manager_readiness,
    run_order_builder,
)
from utils.face_validity import generate_face_validity_check

STORE = "SD001"
DATE = "2024-01-15"
HOUR = 8

_REQUIRED_KEYS = {
    "status",
    "confidence",
    "supporting_reasons",
    "concerns",
    "human_review_required",
    "evidence_quality",
    "anchors_used",
    "recommended_action",
}

_VALID_STATUSES = {"plausible", "needs_review", "weak", "not_applicable"}
_VALID_CONFIDENCES = {"high", "medium-high", "medium", "low"}
_VALID_ACTIONS = {"approve", "review", "ask_follow_up", "rerun", "escalate"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strong_evidence(
    quality_score: float = 0.85,
    quality_label: str = "strong",
    n_tools: int = 3,
    n_rag: int = 3,
) -> dict:
    """Build a plausible-shaped evidence package for unit tests."""
    return {
        "tool_outputs": [{"tool": f"tool_{i}", "status": "success"} for i in range(n_tools)],
        "rag_results": [{"filename": f"doc_{i}.md", "snippet": "snippet…"} for i in range(n_rag)],
        "rag_snippets": [{"filename": f"doc_{i}.md", "snippet": "snippet…"} for i in range(n_rag)],
        "assumptions": [],
        "warnings": [],
        "evidence_count": n_tools + n_rag,
        "quality_score": quality_score,
        "quality_label": quality_label,
        "quality_recommendation": "Evidence is sufficient for automated decision.",
    }


def _check_shape(fv: dict) -> None:
    missing = _REQUIRED_KEYS - set(fv.keys())
    assert not missing, f"face_validity missing keys: {missing}"
    assert fv["status"] in _VALID_STATUSES, f"unexpected status: {fv['status']!r}"
    assert fv["confidence"] in _VALID_CONFIDENCES, f"unexpected confidence: {fv['confidence']!r}"
    assert fv["recommended_action"] in _VALID_ACTIONS, (
        f"unexpected recommended_action: {fv['recommended_action']!r}"
    )
    assert isinstance(fv["supporting_reasons"], list)
    assert isinstance(fv["concerns"], list)
    assert isinstance(fv["human_review_required"], bool)
    assert isinstance(fv["evidence_quality"], dict)
    assert "score" in fv["evidence_quality"]
    assert "label" in fv["evidence_quality"]
    assert isinstance(fv["anchors_used"], list)


# ---------------------------------------------------------------------------
# 1. Normal / plausible workflow output
# ---------------------------------------------------------------------------


def test_normal_plausible_output_has_full_shape():
    final = {
        "readiness_summary": {"overall_status": "success"},
        "recommended_actions": ["[OK] Proceed with standard pre-shift checklist."],
        "barista_guidance": {"rush_level": "low"},
    }
    fv = generate_face_validity_check(
        workflow_type="manager_readiness",
        final_output=final,
        evidence_package=_strong_evidence(),
    )
    _check_shape(fv)
    assert fv["status"] in ("plausible", "needs_review")
    assert fv["confidence"] != "low"
    assert len(fv["supporting_reasons"]) > 0


def test_normal_plausible_output_anchors_present():
    fv = generate_face_validity_check(
        workflow_type="manager_readiness",
        final_output={"readiness_summary": {"overall_status": "success"}},
        evidence_package=_strong_evidence(),
    )
    # MCP/tool, RAG, audit log anchors should all appear with this payload
    assert "MCP/tool output" in fv["anchors_used"]
    assert "RAG internal guidance" in fv["anchors_used"]
    assert "Audit log" in fv["anchors_used"]


# ---------------------------------------------------------------------------
# 2. Missing evidence case
# ---------------------------------------------------------------------------


def test_missing_evidence_returns_weak():
    empty_evidence = {
        "tool_outputs": [],
        "rag_results": [],
        "evidence_count": 0,
        "quality_score": 0.0,
        "quality_label": "weak",
    }
    fv = generate_face_validity_check(
        workflow_type="manager_readiness",
        final_output={"readiness_summary": {}},
        evidence_package=empty_evidence,
    )
    _check_shape(fv)
    assert fv["status"] in ("weak", "needs_review")
    # At least one concern must explicitly call out weak/missing evidence
    assert any(
        "weak" in c.lower() or "missing" in c.lower() for c in fv["concerns"]
    ), f"no weak-evidence concern found: {fv['concerns']}"


def test_empty_final_output_returns_weak():
    fv = generate_face_validity_check(
        workflow_type="manager_readiness",
        final_output={},
        evidence_package=_strong_evidence(),
    )
    _check_shape(fv)
    assert fv["status"] == "weak"
    assert fv["recommended_action"] in ("rerun", "review")


# ---------------------------------------------------------------------------
# 3. Allergy-sensitive request
# ---------------------------------------------------------------------------


def test_allergy_in_user_input_triggers_escalation():
    fv = generate_face_validity_check(
        workflow_type="barista_recommendation",
        final_output={"top_candidates": [{"item": "Iced Black Tea"}]},
        evidence_package=_strong_evidence(),
        user_input={"customer_request": "I have a nut allergy and want something cold"},
    )
    _check_shape(fv)
    assert fv["status"] == "needs_review"
    assert fv["human_review_required"] is True
    assert fv["recommended_action"] in ("review", "escalate")
    assert any("allerg" in c.lower() or "medical" in c.lower() for c in fv["concerns"]), (
        f"no allergy concern found: {fv['concerns']}"
    )


def test_allergy_in_warnings_triggers_escalation():
    fv = generate_face_validity_check(
        workflow_type="order_builder",
        final_output={"structured_order": {"item": "Caffe Latte"}, "missing_fields": []},
        evidence_package=_strong_evidence(),
        warnings=["Allergy or medical language detected. Do NOT make guarantees."],
    )
    _check_shape(fv)
    assert fv["status"] == "needs_review"
    assert fv["human_review_required"] is True


# ---------------------------------------------------------------------------
# 4. Missing field / order clarification case
# ---------------------------------------------------------------------------


def test_missing_size_field_triggers_followup():
    final = {
        "structured_order": {"item": "Iced Caffe Latte", "size": None},
        "missing_fields": ["size"],
        "follow_up_question": "What size would you like?",
    }
    review_queue = [{"item": "order_missing_fields", "missing_fields": ["size"]}]
    fv = generate_face_validity_check(
        workflow_type="order_builder",
        final_output=final,
        evidence_package=_strong_evidence(),
        review_queue=review_queue,
    )
    _check_shape(fv)
    assert fv["status"] == "needs_review"
    assert fv["recommended_action"] in ("ask_follow_up", "review")
    assert fv["human_review_required"] is True


def test_missing_field_in_review_queue_only():
    """When missing-field signal is only in review_queue, it still triggers."""
    fv = generate_face_validity_check(
        workflow_type="order_builder",
        final_output={"structured_order": {"item": "Iced Latte"}},
        evidence_package=_strong_evidence(),
        review_queue=[{"item": "order_missing_fields"}],
    )
    _check_shape(fv)
    assert fv["status"] == "needs_review"
    assert fv["recommended_action"] in ("ask_follow_up", "review")


# ---------------------------------------------------------------------------
# 5. Orchestrator integration — every workflow attaches face_validity
# ---------------------------------------------------------------------------


def test_manager_readiness_attaches_face_validity():
    r = run_manager_readiness(STORE, DATE, HOUR)
    assert "face_validity" in r, "manager_readiness response missing face_validity"
    _check_shape(r["face_validity"])


def test_barista_recommendation_attaches_face_validity():
    r = run_barista_recommendation(
        STORE, DATE, HOUR,
        "I want something iced, sweet, dairy-free, and medium caffeine.",
    )
    assert "face_validity" in r
    fv = r["face_validity"]
    _check_shape(fv)
    # Customer-facing workflow with a populated review queue should land on needs_review
    assert fv["status"] in ("needs_review", "plausible")


def test_order_builder_attaches_face_validity():
    r = run_order_builder(
        STORE, DATE,
        "grande iced matcha with oat milk, light ice, and vanilla",
    )
    assert "face_validity" in r
    _check_shape(r["face_validity"])


def test_full_workflow_attaches_face_validity():
    r = run_full_workflow(
        STORE, DATE, HOUR,
        "I want something iced, sweet, dairy-free, and medium caffeine.",
        "grande iced chai with almond milk",
    )
    assert "face_validity" in r
    _check_shape(r["face_validity"])


def test_orchestrator_allergy_request_escalates():
    r = run_barista_recommendation(
        STORE, DATE, HOUR,
        "I have a nut allergy and want something dairy-free.",
    )
    fv = r["face_validity"]
    _check_shape(fv)
    assert fv["status"] == "needs_review"
    assert fv["recommended_action"] in ("review", "escalate")
    assert fv["human_review_required"] is True


# ---------------------------------------------------------------------------
# 6. Regression: RAG content must not poison allergy detection
# ---------------------------------------------------------------------------


def test_benign_request_does_not_falsely_escalate():
    """A request with no allergy/medical language must not escalate even when
    RAG retrieves docs whose filenames or snippets mention 'allergen'
    (e.g. `dietary_allergen_guidance.md`).
    """
    r = run_barista_recommendation(
        STORE, DATE, HOUR,
        "something hot and caffeinated",  # no allergy/dietary terms
    )
    fv = r["face_validity"]
    _check_shape(fv)
    # The orchestrator may still mark this as needs_review because the review
    # queue is populated (designed behaviour for customer-facing flows), but
    # the action MUST NOT be escalate — there is no allergy signal.
    assert fv["recommended_action"] != "escalate", (
        f"benign request falsely escalated; concerns={fv['concerns']}"
    )
    # And no allergy/medical concern should appear
    assert not any(
        "allerg" in c.lower() or "medical" in c.lower() for c in fv["concerns"]
    ), f"benign request surfaced an allergy/medical concern: {fv['concerns']}"


def test_full_workflow_benign_request_does_not_escalate():
    """Same regression at the full_workflow level."""
    r = run_full_workflow(
        STORE, DATE, HOUR,
        "something cold and refreshing",
        raw_order="Grande iced coffee",
    )
    fv = r["face_validity"]
    _check_shape(fv)
    assert fv["recommended_action"] != "escalate"
