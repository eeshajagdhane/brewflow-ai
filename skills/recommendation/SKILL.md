# Skill: recommendation

## Purpose

Recommends drinks to a customer based on their stated preferences, current inventory
availability, rush context, and policy guidance from the knowledge base.

This skill produces a natural-language recommendation grounded in structured
tool outputs and RAG evidence.

## When to Use This Skill

Use this skill when:
- A customer says "I'm not sure what to get" or "What do you recommend?"
- A barista needs to suggest an alternative due to an unavailable ingredient.
- A customer states preferences (sweet, cold, dairy-free, low-calorie, etc.).
- The manager's daily briefing has produced `barista_guidance` to incorporate.

## Inputs

| Field | Type | Required | Notes |
|---|---|---|---|
| store_id | string | Yes | For inventory and rush context |
| date | string | Yes | YYYY-MM-DD |
| hour | integer | Yes | 0–23 |
| customer_request | string | Yes | What the customer said |
| preferences | dict | No | Structured preferences (see below) |

Preferences dict keys:
`temperature`, `dairy_free`, `vegan`, `gluten_free`, `caffeine`, `non_coffee`,
`low_calorie`, `flavor`, `keywords`, `food`

## Data and Tools Used

1. **`detect_rush_period(store_id, date, hour)`** — determines service mode.
2. **`search_menu_by_preferences(preferences, store_id, date, hour)`** — returns ranked candidates.
3. **`check_inventory_status(store_id, date)`** — flags low-stock / unavailable ingredients.
4. **`get_menu_item_info(item_name)`** — used to enrich top candidates with nutrition/dietary data.

Do NOT manually read CSVs when a tool can answer the question.

## RAG Documents Used

- `barista_recommendation_guidelines.md` — preference-matching rules.
- `dietary_allergen_guidance.md` — how to communicate dietary constraints.
- `inventory_substitution_sop.md` — what to say when an ingredient is low/unavailable.
- `rush_hour_service_playbook.md` — limit recommendations to 2 during rush.

## Step-by-Step Instructions

1. Call `run_barista_recommendation(store_id, date, hour, customer_request, preferences)`.
   (or chain the individual tool calls if calling directly)
2. Review `rush_risk` from `detect_rush_period`:
   - If "high": limit recommendation to the top 1–2 candidates only.
3. Review `top_candidates` from `search_menu_by_preferences`.
   - If `inventory_safe = False` for a candidate: skip it or flag it with a substitution note.
4. Retrieve guidance from `retrieve_internal_knowledge` for recommendation context.
5. Present the top recommendation in natural language:
   - Name the item.
   - Explain **why** it matches the customer's preferences (cite reason_codes).
   - Mention the size options available.
   - If a substitution is needed: say what and why, per inventory_substitution_sop.md.
6. Offer a backup option if the first is unavailable.
7. Do NOT guarantee allergen or dietary properties — use qualified language ("made without...").

## Expected Output Format (structured section)

```
{
  "summary": "Based on your preference for cold, sweet drinks...",
  "inputs_used": {"preferences": {...}, "store_id": "SD001"},
  "tool_calls_used": ["detect_rush_period", "search_menu_by_preferences", "check_inventory_status"],
  "rag_documents_used": ["barista_recommendation_guidelines.md", "dietary_allergen_guidance.md"],
  "recommendation": {
    "item": "Iced Caramel Macchiato",
    "reason": "Matches cold temperature, sweet/caramel flavor, has caffeine.",
    "inventory_safe": true,
    "sizes_available": ["Tall", "Grande", "Venti"]
  },
  "backup_option": "Pink Drink (dairy-free, no caffeine, fruity)",
  "warnings": ["Oat milk is currently low stock — substitution may be needed."],
  "missing_fields": [],
  "human_review_required": true,
  "handoff_to_next_step": "order_builder"
}
```

## Human Review Requirements

- **Always** require human review before finalizing a recommendation to the customer.
- If any `inventory_safe = False` for top candidates: require human review.
- If customer mentions an allergy: require human review. See dietary_allergen_guidance.md.
- Do NOT present a recommendation that has `human_review_required = True` as final without barista confirmation.

## Edge Cases and Failure Cases

| Scenario | Action |
|---|---|
| No candidates match preferences | Relax one filter; ask the customer to clarify |
| All top candidates are low-stock | Use the backup from healthy-stock items |
| Rush is high and inventory is low | Recommend the simplest, most available item |
| Customer asks for something not on menu | Clarify; suggest closest available item |
| Allergy mentioned | Flag review; do not recommend without human confirmation |

## Handoff to Next Step

Pass to `order_builder` skill with:
- `item`: selected item name
- `preferences`: confirmed size, temperature, milk
- `substitutions`: any substitution agreed with the customer
