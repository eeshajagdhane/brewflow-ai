# Dietary and Allergen Guidance

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

Defines how baristas and AI-assisted tools should handle customer dietary
restrictions and allergen questions. Safety-first approach: when in doubt, defer.

## Core Principles

1. **Never make medical guarantees.** The AI and barista cannot guarantee that a
   drink is free from any specific allergen due to shared equipment and supply chain variability.
2. **Always direct to official sources.** Customers with serious allergies should review
   the official Starbucks allergen guide before ordering.
3. **Prefer positive language.** Say "this item is made without [ingredient]" not
   "this item is [allergen]-free."
4. **Flag for human review.** Any order that contains allergy or medical language
   (e.g. "I'm allergic to nuts", "I have celiac disease") must have human_review_required = True.

## Common Dietary Preferences

### Dairy-Free
- Suggest plant-based milk: Oat Milk, Almond Milk, Soy Milk, Coconut Milk.
- Confirm whipped cream is removed if ordering items that include it by default.
- Note: plant-based milks may be handled on shared equipment. Inform the customer.
- Do not guarantee dairy-free status.

### Vegan
- Items marked Vegan = Yes in the menu contain no animal products.
- Customizing to remove dairy or honey components may make other items vegan — but confirm ingredients.
- Honey is an ingredient in some syrups; sugar-free alternatives may be available.

### Gluten-Free
- Items marked Gluten_Free = Yes in the menu are prepared without gluten-containing ingredients.
- Cross-contact with gluten is possible in shared prep environments.
- Bakery items are NOT recommended for customers with celiac disease unless clearly labeled.

### Nut Allergy
- Almond Milk contains almonds. Do not suggest it to customers with nut allergies.
- Hazelnut syrup contains nut derivatives. Avoid for nut allergy customers.
- Recommend plain oat milk or soy milk as safer alternatives — but still note cross-contact risk.

### Lactose Intolerance
- Plant-based milks (oat, almond, soy) are lactose-free.
- Lactose-free dairy milk may not be available at all locations — confirm with store.
- Whipped cream contains dairy; request removal.

## What to Say to a Customer

**Customer says:** "I'm allergic to nuts."
**Correct response:** "I can suggest drinks made without nut-based ingredients. For milk, I'd recommend oat or soy milk instead of almond. However, our store uses shared equipment, so I can't guarantee there's no cross-contact. For confirmed allergen information, please check the official Starbucks allergen guide."

**Customer says:** "Is this dairy-free?"
**Correct response:** "This item can be made with oat or almond milk instead of dairy. However, we cannot guarantee it is completely free of dairy due to shared equipment."

## Escalation

- If the customer expresses a severe allergy or medical condition: escalate to manager immediately.
- Do not prepare the order until manager reviews and approves.
- Log the escalation in the audit trail.
