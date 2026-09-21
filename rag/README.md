# `rag/`

Twelve simulated SOP, policy, and training documents plus keyword retrieval.
`knowledge_base/EXAMPLE.md` is excluded from production retrieval.

Operational CSVs live in `data/`. This folder is the handbook: what a barista
or manager would look up, not the day's inventory.

| Document | Used in |
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

```python
from rag.retrieval import retrieve_internal_knowledge
results = retrieve_internal_knowledge(
    "dairy free allergen", top_k=3, workflow_step="barista_recommendation"
)
```

Scoring is deterministic keyword match. No vector database and no API calls.
