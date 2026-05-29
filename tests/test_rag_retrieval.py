"""BrewFlow AI — RAG retrieval tests.

All tests are deterministic and run locally with no external API keys.
Tests verify that the keyword retrieval returns relevant docs for
key workflow queries and that EXAMPLE.md is excluded.
"""

from __future__ import annotations

import pytest

from rag.retrieval import retrieve_internal_knowledge, _INDEX

KB_DOCS = {
    "barista_recommendation_guidelines.md",
    "customization_policy.md",
    "inventory_substitution_sop.md",
    "rush_hour_service_playbook.md",
    "manager_pre_shift_checklist.md",
    "promotion_decision_policy.md",
    "new_barista_menu_training_guide.md",
    "order_confirmation_standard.md",
    "dietary_allergen_guidance.md",
    "drink_quality_consistency_sop.md",
    "service_recovery_policy.md",
    "post_rush_manager_review_template.md",
}


# ---------------------------------------------------------------------------
# Index sanity
# ---------------------------------------------------------------------------


def test_knowledge_base_index_populated():
    assert len(_INDEX) > 0, "Knowledge base index is empty."


def test_all_12_docs_indexed():
    indexed_files = {r["filename"] for r in _INDEX}
    missing = KB_DOCS - indexed_files
    assert not missing, f"These KB docs were not indexed: {missing}"


def test_example_md_excluded():
    all_files = {r["filename"] for r in _INDEX}
    assert "EXAMPLE.md" not in all_files


# ---------------------------------------------------------------------------
# Dietary query
# ---------------------------------------------------------------------------


def test_dietary_query_returns_dietary_doc():
    results = retrieve_internal_knowledge("dairy free vegan allergen recommendation")
    filenames = [r["filename"] for r in results]
    assert "dietary_allergen_guidance.md" in filenames, \
        f"dietary_allergen_guidance.md not in top results: {filenames}"


def test_dietary_query_score_positive():
    results = retrieve_internal_knowledge("dairy free vegan allergen")
    assert results[0]["score"] > 0


# ---------------------------------------------------------------------------
# Substitution query
# ---------------------------------------------------------------------------


def test_substitution_query_returns_substitution_doc():
    results = retrieve_internal_knowledge("inventory substitution low stock unavailable ingredient")
    filenames = [r["filename"] for r in results]
    assert "inventory_substitution_sop.md" in filenames, \
        f"inventory_substitution_sop.md not in top results: {filenames}"


def test_substitution_query_matched_terms():
    results = retrieve_internal_knowledge("inventory substitution low stock")
    assert len(results) > 0
    # At least one result should have matched relevant terms
    all_matched = [t for r in results for t in r["matched_terms"]]
    assert any(t in all_matched for t in ["inventory", "substitution", "stock"])


# ---------------------------------------------------------------------------
# Rush query
# ---------------------------------------------------------------------------


def test_rush_query_returns_rush_doc():
    results = retrieve_internal_knowledge("rush hour high demand service protocol barista")
    filenames = [r["filename"] for r in results]
    assert "rush_hour_service_playbook.md" in filenames, \
        f"rush_hour_service_playbook.md not in top results: {filenames}"


def test_rush_query_with_workflow_step():
    results = retrieve_internal_knowledge("rush high demand", workflow_step="manager_readiness")
    filenames = [r["filename"] for r in results]
    assert "rush_hour_service_playbook.md" in filenames


# ---------------------------------------------------------------------------
# Order confirmation query
# ---------------------------------------------------------------------------


def test_order_confirmation_query():
    results = retrieve_internal_knowledge("order confirmation standard size temperature milk")
    filenames = [r["filename"] for r in results]
    assert "order_confirmation_standard.md" in filenames, \
        f"order_confirmation_standard.md not in top results: {filenames}"


def test_order_confirmation_with_workflow_step():
    results = retrieve_internal_knowledge("confirm order customer", workflow_step="order_builder")
    filenames = [r["filename"] for r in results]
    assert "order_confirmation_standard.md" in filenames


# ---------------------------------------------------------------------------
# Manager readiness query
# ---------------------------------------------------------------------------


def test_manager_readiness_query():
    results = retrieve_internal_knowledge("manager pre-shift checklist readiness", top_k=3, workflow_step="manager_readiness")
    filenames = [r["filename"] for r in results]
    assert "manager_pre_shift_checklist.md" in filenames


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


def test_result_has_required_keys():
    results = retrieve_internal_knowledge("recommendation dairy")
    assert len(results) > 0
    r = results[0]
    for key in ("filename", "title", "section_heading", "snippet", "score", "matched_terms", "workflow_step"):
        assert key in r, f"Key '{key}' missing from result."


def test_top_k_respected():
    results = retrieve_internal_knowledge("coffee milk sugar", top_k=2)
    assert len(results) <= 2


def test_workflow_step_hint_boosts_relevant_docs():
    """With workflow_step hint, step-specific docs should score higher."""
    with_hint = retrieve_internal_knowledge("recommendation", top_k=5, workflow_step="barista_recommendation")
    without_hint = retrieve_internal_knowledge("recommendation", top_k=5)
    hint_files = [r["filename"] for r in with_hint]
    assert "barista_recommendation_guidelines.md" in hint_files


def test_drink_quality_individual_prep():
    """drink_quality_consistency_sop.md should surface for 'individually prepare' query."""
    results = retrieve_internal_knowledge("prepare individually quality consistency drink")
    filenames = [r["filename"] for r in results]
    assert "drink_quality_consistency_sop.md" in filenames
