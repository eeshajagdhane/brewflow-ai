# Skill: order_summary

## Purpose

Creates a customer-facing confirmation statement and a barista-facing
preparation note for a finalized order. This skill is the final checkpoint
before an order is sent to the barista for preparation.

## When to Use This Skill

Use this skill after `order_builder` has produced a complete `structured_order`
with no missing fields and all inventory issues resolved.

## Inputs

| Field | Type | Required | Notes |
|---|---|---|---|
| structured_order | dict | Yes | Output from order_builder skill |
| substitutions | list | No | Any ingredient substitutions made |
| customer_name | string | No | For personalized confirmation |

## Data and Tools Used

This skill uses the `order_builder` output — no additional tool calls are needed.

The following are already captured in `structured_order`:
- item, size, temperature, milk_type, quantity, syrups, toppings, customizations, prep_notes

## RAG Documents Used

- `order_confirmation_standard.md` — the mandatory confirmation sequence.
- `drink_quality_consistency_sop.md` — prep note format and "individually" requirement.
- `customization_policy.md` — how to communicate syrups and toppings in confirmation.

## Step-by-Step Instructions

1. Read the `order_confirmation_standard.md` confirmation sequence.
2. Build the **customer-facing confirmation**:
   - State: item name, size, temperature, milk (if non-default), syrups, toppings, customizations.
   - If quantity > 1: say "two [item]s" etc.
   - If any substitution was made: state it clearly.
   - End with a confirmation question: "Does that sound right?"
3. Build the **barista-facing prep note**:
   - Start with size and temperature.
   - List milk type, syrups with pump counts, toppings.
   - Include all customizations in barista shorthand.
   - End with "Prepare individually for quality consistency."
4. Flag for human approval if:
   - `human_review_required = True` was carried forward from order_builder.
   - A substitution was made and the customer has not yet confirmed it.
5. Once the customer confirms: mark the order as finalized.

## Expected Output Format

### Customer-Facing Confirmation
```
"To confirm: one Grande Iced Caramel Macchiato with oat milk,
caramel drizzle, no whip. Does that sound right?"
```

### Barista Prep Note
```
Grande / Iced / Caramel Macchiato
Milk: Oat Milk
Syrups: Caramel (2 pumps — standard)
Toppings: Caramel drizzle
Mods: No whip
Prepare individually for quality consistency.
```

### Structured Output
```
{
  "summary": "Order confirmed: Grande Iced Caramel Macchiato, oat milk, no whip.",
  "inputs_used": {"structured_order": {...}},
  "tool_calls_used": [],
  "rag_documents_used": ["order_confirmation_standard.md", "drink_quality_consistency_sop.md"],
  "customer_confirmation": "...",
  "barista_prep_note": "...",
  "substitutions": [],
  "warnings": [],
  "human_review_required": false,
  "handoff_to_next_step": "finalized"
}
```

## Human Review Requirements

- If an allergy/medical flag was set in `order_builder`: do NOT finalize without manager confirmation.
- If a substitution was made: require explicit customer confirmation before finalizing.
- Do NOT print or display the prep note to the customer — it is barista-only.

## Edge Cases and Failure Cases

| Scenario | Action |
|---|---|
| Customer says "no" to confirmation | Return to order_builder to modify |
| Customer adds a customization during confirmation | Update structured_order and re-confirm |
| Substitution rejected by customer | Offer a different item; restart recommendation |
| Prep note exceeds normal complexity | Flag for senior barista attention |

## Handoff to Next Step

This is the final skill in the order workflow.
After customer confirmation, pass the finalized order to the POS / ticket system.
Log the completed order in the audit trail.
