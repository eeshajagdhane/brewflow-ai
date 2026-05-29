# Skill: product_catalog

## Purpose

Helps baristas answer customer questions about the Starbucks menu — what items exist,
what they contain, their nutritional information, dietary flags, and available sizes.

## When to Use This Skill

Use this skill when a customer or barista asks:
- "What's in a [drink name]?"
- "Is [item] vegan / gluten-free?"
- "How many calories does a [size] [drink] have?"
- "What sizes is [item] available in?"
- "Does [item] contain dairy / caffeine?"
- "What are the ingredients in [item]?"

## Inputs

| Field | Type | Required | Notes |
|---|---|---|---|
| item_name | string | Yes | Any name — resolved via item_name_mapping.csv |
| attribute | string | No | Optional: "calories", "ingredients", "sizes", "dietary" |

## Data and Tools Used

1. **`get_menu_item_info(item_name)`** — primary lookup tool.
   Returns: canonical_name, category, key_ingredients, vegan, gluten_free, sizes_available, size_nutrition.
2. **`starbucks_menu_full.csv`** — source of all menu data (accessed via the tool, not directly).
3. **`item_name_mapping.csv`** — resolves common names and alternate spellings.

## RAG Documents Used

- `new_barista_menu_training_guide.md` — menu categories and item family descriptions.
- `dietary_allergen_guidance.md` — how to communicate dietary flags to customers.

## Step-by-Step Instructions

1. Call `get_menu_item_info(item_name)`.
2. If status = "needs_review": inform the customer the item was not found.
   Show top candidates from the tool's `candidates` list and ask for clarification.
3. If status = "warning": the item name is ambiguous. Present candidates and ask the customer to clarify.
4. If status = "success":
   a. Report the canonical name, category, and subcategory.
   b. If asked about nutrition: look up the specific size row in `size_nutrition`.
   c. If asked about ingredients: report `key_ingredients`.
   d. If asked about dietary flags: report `vegan` and `gluten_free` from the data.
      **Do NOT invent or guarantee claims not supported by the data.**
   e. If asked about caffeine: report `caffeine_mg` from the relevant size row.
5. Always add: "For official allergen information, please check the Starbucks website."
   when a customer raises a dietary restriction. See dietary_allergen_guidance.md.

## Expected Output Format

```
{
  "canonical_name": "Caramel Macchiato",
  "category": "Hot Coffee",
  "subcategory": "Espresso Drinks",
  "key_ingredients": "Espresso, vanilla syrup, milk, caramel drizzle",
  "vegan": false,
  "gluten_free": true,
  "sizes_available": ["Tall", "Grande", "Venti"],
  "size_nutrition": [
    {"size": "Grande", "calories": 250, "caffeine_mg": 150, "fat_g": 7, "sugar_g": 33}
  ],
  "warnings": []
}
```

## Human Review Requirements

- If `human_review_required = True` from the tool: display a warning to the barista before responding.
- If the customer asks about a specific allergen or medical condition: flag for review.
- Do NOT make guarantees about cross-contact or processing environment safety.

## Edge Cases and Failure Cases

| Scenario | Action |
|---|---|
| Item not in mapping or menu | Return "Item not found." Show closest candidates. |
| Low-confidence mapping | Proceed but display a warning note. |
| Item has multiple size rows | Present all sizes; let the customer select. |
| Customer asks about food item | This skill covers food too — use the same lookup. |
| Caffeine_mg = 0 for a coffee | Flag as potentially incorrect data; say "caffeine information unavailable." |

## Handoff to Next Step

This skill is standalone. If the customer's question leads to a purchase decision,
hand off to the `recommendation` or `order_builder` skill.
