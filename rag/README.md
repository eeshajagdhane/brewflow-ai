# `rag/`

> **BrewFlow AI — Active RAG:** 12 knowledge base documents + `retrieval.py`.
> `knowledge_base/EXAMPLE.md` is the course template — excluded from production retrieval.

## BrewFlow Knowledge Base (12 documents)

| Document | Used In |
|---|---|
| `barista_recommendation_guidelines.md` | recommendation |
| `customization_policy.md` | order_builder |
| `inventory_substitution_sop.md` | manager_readiness, order_builder |
| `rush_hour_service_playbook.md` | manager_readiness, recommendation |
| `manager_pre_shift_checklist.md` | manager_readiness |
| `promotion_decision_policy.md` | manager_readiness |
| `new_barista_menu_training_guide.md` | product_catalog, recommendation |
| `order_confirmation_standard.md` | order_builder, order_summary |
| `dietary_allergen_guidance.md` | recommendation, order_builder |
| `drink_quality_consistency_sop.md` | order_builder, order_summary |
| `service_recovery_policy.md` | recommendation, order_summary |
| `post_rush_manager_review_template.md` | manager_readiness |

## Retrieval Function

```python
from rag.retrieval import retrieve_internal_knowledge
results = retrieve_internal_knowledge("dairy free allergen", top_k=3, workflow_step="barista_recommendation")
```

Deterministic keyword scoring — no vector DB, no API calls. EXAMPLE.md is excluded.

---

**Retrieval Augmented Generation** (RAG) lets your AI coworker answer
questions and complete tasks using **proprietary** company information that
the base model has not seen during training. You build a small knowledge
base, index it, and at query time pull the most relevant chunks into the
prompt.

This folder is **new in M03** — there is no corresponding folder in the
reference repo. You build it from scratch.

---

## What you must deliver

- **`knowledge_base/`** — 10–20 documents representing internal company
  knowledge: HR handbook, IT SOPs, internal policies, product catalog,
  meeting notes, contracts, FAQ for an internal tool, etc.
- **`index/`** — the searchable form of the KB (vector store, keyword
  index, or both). Gitignore large binary indexes.
- **`retrieval.py`** — a Python function
  `retrieve(query: str, top_k: int = 3) -> list[dict]` other code calls.
- **Integration** — at least one of your skills or MCP tools uses
  `retrieve(...)` to ground its answer in the KB.

> **Important pedagogical point.** This corpus is *separate* from `../data/`.
> `data/` simulates the operational data your workflow processes (tickets,
> applications, claims). `rag/knowledge_base/` simulates the **proprietary
> knowledge** an employee would need to *understand* the work — policies,
> playbooks, history. Mixing them defeats the RAG exercise.

---

## Two implementation options

| Approach | When to pick it | Stack |
| --- | --- | --- |
| **Keyword search** | 10–20 short docs, simple queries | polars or pure Python; TF-IDF or bag-of-words |
| **Vector search** | Longer docs, fuzzy semantic queries | OpenAI or HuggingFace embeddings + `faiss`, `chromadb`, or `sqlite-vss` |

Both are acceptable for M03. The vector approach is closer to production
RAG; the keyword approach is faster to ship and easier to debug. **Pick one
and finish it** — don't half-build both.

---

## Document format

Plain text or Markdown. One file per document. Suggested frontmatter so
your retriever can show metadata next to the answer:

```markdown
---
title: VPN troubleshooting playbook
category: IT runbook
last_reviewed: 2026-04-01
audience: tier-1 IT
---

# Title

Body...
```

See `knowledge_base/EXAMPLE.md` for a starter document.

---

## Integration shapes (pick one)

1. **Inside a skill.** A skill's script calls `from rag.retrieval import
   retrieve` and injects the top-k chunks into the LLM prompt. Cleanest.
2. **As an MCP tool.** Expose `retrieve(query, top_k)` as an MCP tool in
   `mcp_servers/tools_server.py`. The model decides when to call it.
3. **Both.** A few skills use it directly *and* the model can call it on
   demand via MCP.

---

## Testing checklist

- A query with an obvious match returns the right document.
- A query with no match returns an **empty** list — the calling skill
  degrades gracefully (says "I don't know" rather than hallucinating).
- The skill that consumes retrieved content cites which doc(s) it used.
- Token budget for retrieved chunks is bounded — large docs are chunked.

---

## Resources

- Overview video: <https://www.youtube.com/watch?v=JB2P5Gk23VI> ("RAG's
  Evolution: From Simple Retrieval to Agentic AI")
- Advanced patterns (optional):
  - LightRAG: <https://www.youtube.com/watch?v=QHlB-RJfx8w>
  - RAG-Anything: <https://www.youtube.com/watch?v=rJCgvnXgOiU>
