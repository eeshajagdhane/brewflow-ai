"""Evidence packaging utilities for BrewFlow AI.

Formats data from tool calls, RAG retrieval, and human-review history
into a UI-ready evidence structure that supports the human review queue.
"""

from __future__ import annotations

from typing import Any, Optional


def build_evidence_package(
    tool_outputs: list[dict],
    rag_results: list[dict],
    assumptions: Optional[list[str]] = None,
    warnings: Optional[list[str]] = None,
) -> dict:
    """Combine tool outputs and RAG results into a structured evidence package.

    Args:
        tool_outputs: List of dicts returned by MCP tools or automations.
                      Each should have at least {"tool": str, "status": str}.
        rag_results:  List of dicts returned by retrieve_internal_knowledge.
                      Each should have at least {"filename": str, "snippet": str}.
        assumptions:  Any assumptions the workflow made when data was missing.
        warnings:     Warnings surfaced during evidence collection.

    Returns a UI-ready evidence package dict with pre-computed quality score.
    `rag_snippets` is provided as an alias for `rag_results` for UI convenience.
    """
    package = {
        "tool_outputs": tool_outputs,
        "rag_results": rag_results,
        "rag_snippets": rag_results,
        "assumptions": assumptions or [],
        "warnings": warnings or [],
        "evidence_count": len(tool_outputs) + len(rag_results),
    }
    quality = evidence_quality_score(package)
    package["quality_score"] = quality["score"]
    package["quality_label"] = quality["quality"]
    package["quality_recommendation"] = quality["recommendation"]
    return package


def evidence_quality_score(evidence_package: dict) -> dict:
    """Score the quality of an evidence package (0.0–1.0).

    Scoring logic:
      - Each tool output contributes +0.2 (capped at 0.6).
      - Each RAG result contributes +0.15 (capped at 0.45).
      - Each warning deducts 0.05; each assumption deducts 0.03.
    """
    tool_count = len(evidence_package.get("tool_outputs", []))
    rag_count = len(evidence_package.get("rag_results", []))
    warning_count = len(evidence_package.get("warnings", []))
    assumption_count = len(evidence_package.get("assumptions", []))

    raw_score = min(0.6, tool_count * 0.2) + min(0.45, rag_count * 0.15)
    penalty = min(0.3, warning_count * 0.05 + assumption_count * 0.03)
    score = max(0.0, raw_score - penalty)

    if score >= 0.65:
        quality = "strong"
    elif score >= 0.35:
        quality = "moderate"
    else:
        quality = "weak"

    return {
        "score": round(score, 2),
        "quality": quality,
        "tool_evidence_count": tool_count,
        "rag_evidence_count": rag_count,
        "warning_count": warning_count,
        "assumption_count": assumption_count,
        "recommendation": (
            "Evidence is sufficient for automated decision."
            if quality == "strong"
            else "Human review recommended before finalizing."
            if quality == "moderate"
            else "Insufficient evidence — human review required."
        ),
    }


def summarize_evidence_for_review(evidence_package: dict) -> dict:
    """Produce a compact summary of the evidence package for display in a review UI."""
    quality = evidence_quality_score(evidence_package)

    tool_summaries = [
        {
            "tool": t.get("tool", t.get("source", "unknown")),
            "status": t.get("status", "unknown"),
            "summary": t.get("summary", str(t.get("data", ""))[:120]),
        }
        for t in evidence_package.get("tool_outputs", [])
    ]

    rag_summaries = [
        {
            "doc": r.get("filename", "unknown"),
            "title": r.get("title", ""),
            "snippet": str(r.get("snippet", ""))[:200],
            "score": r.get("score", 0),
            "workflow_step": r.get("workflow_step", ""),
        }
        for r in evidence_package.get("rag_results", [])
    ]

    return {
        "quality": quality,
        "tool_evidence": tool_summaries,
        "rag_evidence": rag_summaries,
        "assumptions": evidence_package.get("assumptions", []),
        "warnings": evidence_package.get("warnings", []),
    }
