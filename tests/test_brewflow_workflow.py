"""BrewFlow AI — orchestrator workflow tests.

All tests run locally with no external API keys.
Tests verify that each orchestrator function returns a properly structured
workflow response with all required fields.
"""

from __future__ import annotations

import pytest

from scripts.orchestrator import (
    run_barista_recommendation,
    run_full_workflow,
    run_manager_readiness,
    run_order_builder,
)

STORE = "SD001"
DATE = "2024-01-15"
HOUR = 8

# Required top-level keys in every workflow response
_WF_REQUIRED_KEYS = {
    "run_id", "workflow_type", "status", "steps", "final_output",
    "evidence_package", "review_queue", "review_required", "review_actions",
    "audit_log", "assumptions", "warnings", "generated_at",
}

_REVIEW_ACTIONS = {"approve", "edit", "reject_rerun", "escalate"}


def _check_wf_structure(result: dict, workflow_type: str) -> None:
    """Assert that a workflow response has all required fields."""
    missing = _WF_REQUIRED_KEYS - result.keys()
    assert not missing, f"Missing workflow keys: {missing}"
    assert result["workflow_type"] == workflow_type
    assert result["run_id"].startswith("wf-")
    assert isinstance(result["steps"], list)
    assert isinstance(result["audit_log"], list)
    assert isinstance(result["warnings"], list)
    assert set(result["review_actions"]) == _REVIEW_ACTIONS
    assert "evidence_count" in result["evidence_package"]


# ---------------------------------------------------------------------------
# Manager Readiness
# ---------------------------------------------------------------------------


def test_manager_readiness_structure():
    result = run_manager_readiness(STORE, DATE, HOUR)
    _check_wf_structure(result, "manager_readiness")


def test_manager_readiness_step_names():
    result = run_manager_readiness(STORE, DATE, HOUR)
    step_names = [s["step"] for s in result["steps"]]
    assert "detect_rush_period" in step_names
    assert "calculate_staffing_gap" in step_names
    assert "check_inventory_status" in step_names
    assert "retrieve_internal_knowledge" in step_names
    assert "manager_daily_briefing" in step_names


def test_manager_readiness_final_output_fields():
    result = run_manager_readiness(STORE, DATE, HOUR)
    fo = result["final_output"]
    assert "readiness_summary" in fo
    assert "recommended_actions" in fo
    assert "barista_guidance" in fo
    assert "demand_detail" in fo
    assert "staffing_detail" in fo


def test_manager_readiness_barista_guidance():
    result = run_manager_readiness(STORE, DATE, HOUR)
    bg = result["final_output"]["barista_guidance"]
    assert "rush_level" in bg
    assert bg["rush_level"] in ("low", "medium", "high")
    assert "avoid_ingredients" in bg


def test_manager_readiness_evidence_has_data():
    result = run_manager_readiness(STORE, DATE, HOUR)
    ep = result["evidence_package"]
    assert ep["evidence_count"] > 0
    assert len(ep["tool_outputs"]) > 0
    assert len(ep["rag_results"]) > 0


# ---------------------------------------------------------------------------
# Barista Recommendation
# ---------------------------------------------------------------------------


def test_barista_recommendation_structure():
    result = run_barista_recommendation(STORE, DATE, HOUR, "something cold and refreshing",
                                        {"temperature": "cold"})
    _check_wf_structure(result, "barista_recommendation")


def test_barista_recommendation_has_candidates():
    result = run_barista_recommendation(STORE, DATE, HOUR, "iced coffee", {"temperature": "cold"})
    candidates = result["final_output"]["top_candidates"]
    assert len(candidates) > 0


def test_barista_recommendation_dairy_free():
    result = run_barista_recommendation(STORE, DATE, HOUR, "dairy free cold drink", {"dairy_free": True})
    candidates = result["final_output"]["top_candidates"]
    assert len(candidates) > 0
    for c in candidates:
        assert c["vegan"] is True


def test_barista_recommendation_has_rag_guidance():
    result = run_barista_recommendation(STORE, DATE, HOUR, "recommendation")
    assert len(result["final_output"]["rag_guidance"]) > 0


def test_barista_recommendation_always_requires_review():
    result = run_barista_recommendation(STORE, DATE, HOUR, "any drink")
    assert result["review_required"] is True


# ---------------------------------------------------------------------------
# Order Builder
# ---------------------------------------------------------------------------


def test_order_builder_structure():
    result = run_order_builder(STORE, DATE, "Grande iced caramel macchiato")
    _check_wf_structure(result, "order_builder")


def test_order_builder_normal_order():
    result = run_order_builder(STORE, DATE, "Grande iced caramel macchiato with oat milk")
    fo = result["final_output"]
    assert fo["structured_order"]["size"] == "Grande"
    assert fo["structured_order"]["temperature"] == "Iced"
    assert fo["structured_order"]["milk_type"] == "Oat Milk"
    assert "missing_fields" in fo
    assert "prep_notes" in fo


def test_order_builder_missing_size_triggers_review():
    result = run_order_builder(STORE, DATE, "hot caramel macchiato")
    fo = result["final_output"]
    assert "size" in fo["missing_fields"]
    assert fo["follow_up_question"] is not None
    assert result["review_required"] is True


def test_order_builder_allergy_requires_human_review():
    result = run_order_builder(STORE, DATE, "grande latte, I have a nut allergy")
    assert result["review_required"] is True
    allergy_items = [q for q in result["review_queue"] if "allergy" in q.get("item", "")]
    assert len(allergy_items) > 0


def test_order_builder_prep_notes_include_individually():
    result = run_order_builder(STORE, DATE, "Tall hot latte")
    prep_text = " ".join(result["final_output"]["prep_notes"])
    assert "individually" in prep_text.lower()


def test_order_builder_has_rag_confirmation_guidance():
    result = run_order_builder(STORE, DATE, "Grande iced latte")
    assert len(result["final_output"]["rag_confirmation_guidance"]) > 0


def test_order_builder_step_names():
    result = run_order_builder(STORE, DATE, "Venti cold brew")
    step_names = [s["step"] for s in result["steps"]]
    assert "build_and_validate_order" in step_names
    assert "retrieve_internal_knowledge" in step_names


# ---------------------------------------------------------------------------
# Full Workflow
# ---------------------------------------------------------------------------


def test_full_workflow_structure():
    result = run_full_workflow(STORE, DATE, HOUR, "something iced", raw_order="Grande iced latte")
    _check_wf_structure(result, "full_workflow")


def test_full_workflow_has_all_phases():
    result = run_full_workflow(STORE, DATE, HOUR, "cold drink", raw_order="Grande iced latte")
    phases = [s.get("phase") for s in result["steps"]]
    assert "manager_readiness" in phases
    assert "barista_recommendation" in phases
    assert "order_builder" in phases


def test_full_workflow_no_order_skips_order_builder():
    result = run_full_workflow(STORE, DATE, HOUR, "what do you recommend")
    phases = [s.get("phase") for s in result["steps"]]
    assert "order_builder" not in phases


def test_full_workflow_audit_log_populated():
    result = run_full_workflow(STORE, DATE, HOUR, "iced drink", raw_order="Tall iced tea")
    assert len(result["audit_log"]) > 5


def test_full_workflow_evidence_count_increases_with_order():
    r_no_order = run_full_workflow(STORE, DATE, HOUR, "cold drink")
    r_with_order = run_full_workflow(STORE, DATE, HOUR, "cold drink", raw_order="Grande iced latte")
    # With order, there should be more evidence
    assert r_with_order["evidence_package"]["evidence_count"] >= r_no_order["evidence_package"]["evidence_count"]


def test_full_workflow_final_output_has_all_sections():
    result = run_full_workflow(STORE, DATE, HOUR, "recommendation", raw_order="Grande iced coffee")
    fo = result["final_output"]
    assert "manager_readiness" in fo
    assert "recommendation" in fo
    assert "order" in fo
