"""BrewFlow AI RAG retrieval for the internal knowledge base.

Implements deterministic keyword-based scoring — no external APIs, no vector DB.
Every result is traceable to a specific document and section.

Usage::

    from rag.retrieval import retrieve_internal_knowledge
    results = retrieve_internal_knowledge("dairy-free recommendation", top_k=3)
    results = retrieve_internal_knowledge("order confirmation", workflow_step="order_builder")

EXAMPLE.md is excluded from production retrieval.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

KB_DIR = Path(__file__).resolve().parent / "knowledge_base"

# Files excluded from production retrieval
_EXCLUDED_FILES = {"EXAMPLE.md"}

# Workflow step → documents most relevant to that step
_STEP_HINTS: dict[str, list[str]] = {
    "manager_readiness": [
        "manager_pre_shift_checklist.md",
        "rush_hour_service_playbook.md",
        "promotion_decision_policy.md",
        "inventory_substitution_sop.md",
        "post_rush_manager_review_template.md",
    ],
    "barista_recommendation": [
        "barista_recommendation_guidelines.md",
        "dietary_allergen_guidance.md",
        "inventory_substitution_sop.md",
        "rush_hour_service_playbook.md",
        "new_barista_menu_training_guide.md",
    ],
    "order_builder": [
        "order_confirmation_standard.md",
        "customization_policy.md",
        "dietary_allergen_guidance.md",
        "drink_quality_consistency_sop.md",
        "inventory_substitution_sop.md",
    ],
    "order_summary": [
        "order_confirmation_standard.md",
        "drink_quality_consistency_sop.md",
        "customization_policy.md",
        "service_recovery_policy.md",
    ],
    "human_review": [
        "service_recovery_policy.md",
        "dietary_allergen_guidance.md",
        "inventory_substitution_sop.md",
    ],
}

# ---------------------------------------------------------------------------
# Document index (built once at import time)
# ---------------------------------------------------------------------------


def _build_index() -> list[dict]:
    """Parse all KB markdown files into a flat list of section records."""
    index: list[dict] = []
    if not KB_DIR.exists():
        return index

    for md_path in sorted(KB_DIR.glob("*.md")):
        if md_path.name in _EXCLUDED_FILES:
            continue

        raw_text = md_path.read_text(encoding="utf-8")
        lines = raw_text.splitlines()

        # Extract document title (first # heading)
        doc_title = md_path.stem.replace("_", " ").title()
        for line in lines:
            if line.startswith("# "):
                doc_title = line.lstrip("# ").strip()
                break

        # Split into sections by ## headings
        sections: list[tuple[str, str]] = []  # (heading, text)
        current_heading = "Introduction"
        current_lines: list[str] = []

        for line in lines:
            if line.startswith("## "):
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines)))
                current_heading = line.lstrip("# ").strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines)))

        # Full document text (for whole-doc search)
        full_text = raw_text.lower()

        for heading, section_text in sections:
            # Extract a readable snippet (first 300 non-empty chars of section)
            snippet_lines = [l.strip() for l in section_text.splitlines() if l.strip() and not l.startswith(">")]
            snippet = " ".join(snippet_lines)[:300]

            index.append(
                {
                    "filename": md_path.name,
                    "title": doc_title,
                    "section_heading": heading,
                    "snippet": snippet,
                    "full_text": (doc_title + " " + heading + " " + section_text).lower(),
                }
            )

    return index


_INDEX: list[dict] = _build_index()


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Return meaningful lowercase tokens (length ≥ 3, strip stop words)."""
    _STOP = {
        "the", "and", "for", "are", "with", "this", "that", "from",
        "will", "not", "can", "has", "its", "any", "all", "but",
        "you", "our", "use", "may", "per", "see", "if", "is", "in",
        "to", "of", "or", "a", "an", "as", "at", "be", "by", "do",
        "it", "no", "on", "so", "up", "we",
    }
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return [t for t in tokens if t not in _STOP]


def _score_record(record: dict, query_tokens: list[str]) -> tuple[float, list[str]]:
    """Return (score, matched_terms) for a single index record."""
    text = record["full_text"]
    matched: list[str] = []
    score = 0.0

    for token in query_tokens:
        if token in text:
            count = text.count(token)
            # Weight by proximity to title/section_heading
            proximity_bonus = 0.5 if token in (record["title"] + " " + record["section_heading"]).lower() else 0.0
            score += min(count, 4) * 0.25 + proximity_bonus
            matched.append(token)

    return score, matched


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def retrieve_internal_knowledge(
    query: str,
    top_k: int = 3,
    workflow_step: Optional[str] = None,
) -> list[dict]:
    """Return up to top_k knowledge base sections most relevant to query.

    Each result dict:
        {
            "filename":        "barista_recommendation_guidelines.md",
            "title":           "Barista Recommendation Guidelines",
            "section_heading": "Preference-Matching Guidelines",
            "snippet":         "... first 300 chars of section ...",
            "score":           2.75,
            "matched_terms":   ["dairy", "free", "recommendation"],
            "workflow_step":   "barista_recommendation",
        }

    If retrieval confidence is weak (all scores == 0), a warning is included
    in the last result dict.

    Workflow_step hint boosts documents that are most relevant to that step.
    """
    if not _INDEX:
        return [
            {
                "filename": "",
                "title": "Index empty",
                "section_heading": "",
                "snippet": "",
                "score": 0.0,
                "matched_terms": [],
                "workflow_step": workflow_step or "",
                "warning": "Knowledge base index is empty. Ensure rag/knowledge_base/*.md files exist.",
            }
        ]

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # Score all records
    scored: list[tuple[float, list[str], dict]] = []
    for record in _INDEX:
        score, matched = _score_record(record, query_tokens)

        # Workflow step boost
        if workflow_step and workflow_step in _STEP_HINTS:
            if record["filename"] in _STEP_HINTS[workflow_step]:
                score += 1.0

        scored.append((score, matched, record))

    # Sort by score descending, then by filename for deterministic tiebreaking
    scored.sort(key=lambda x: (-x[0], x[2]["filename"], x[2]["section_heading"]))

    # Deduplicate: prefer highest-scoring section per document
    seen_docs: dict[str, tuple[float, list[str], dict]] = {}
    for score, matched, record in scored:
        fname = record["filename"]
        if fname not in seen_docs or score > seen_docs[fname][0]:
            seen_docs[fname] = (score, matched, record)

    top_docs = sorted(seen_docs.values(), key=lambda x: (-x[0], x[2]["filename"]))[:top_k]

    results: list[dict] = []
    for score, matched, record in top_docs:
        results.append(
            {
                "filename": record["filename"],
                "title": record["title"],
                "section_heading": record["section_heading"],
                "snippet": record["snippet"],
                "score": round(score, 3),
                "matched_terms": matched,
                "workflow_step": workflow_step or "",
            }
        )

    # Weak evidence warning
    if results and all(r["score"] == 0 for r in results):
        results[-1]["warning"] = (
            "All retrieval scores are 0. Evidence is weak — do not treat retrieved docs as strong support."
        )

    return results
