"""Retrieval entry point for the proprietary knowledge base in ``rag/knowledge_base/``.

Replace the TODO body with your real retriever (keyword or vector — see
``rag/README.md``). Keep the signature stable so callers don't break when
you swap the implementation.

Run directly for a quick smoke test::

    uv run python rag/retrieval.py
"""

from __future__ import annotations

from pathlib import Path

KB_DIR = Path(__file__).resolve().parent / "knowledge_base"
INDEX_DIR = Path(__file__).resolve().parent / "index"


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """Return up to ``top_k`` chunks most relevant to ``query``.

    Each item should be a dict with at least:

        {
            "doc_id": "VPN-PLAYBOOK",
            "title":  "VPN troubleshooting playbook",
            "snippet": "If the client fails on first connect, ...",
            "score":  0.83,
        }

    The empty list is a valid return value when nothing matches. Callers
    must handle that case explicitly.
    """
    # TODO: implement. Suggested approaches in rag/README.md.
    _ = (query, top_k, KB_DIR, INDEX_DIR)
    return []


if __name__ == "__main__":
    sample_query = "How do I reset a user's VPN access?"
    results = retrieve(sample_query, top_k=3)
    print(f"query: {sample_query!r}")
    print(f"results: {results}")
    if not results:
        print("(empty — retrieval.py is a stub. See rag/README.md for the two implementation options.)")
