# Order Confirmation Standard

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

Defines the required sequence for confirming a drink order with the customer
before it is prepared. Applies to all orders taken in-person, via mobile, or through AI-assisted tools.

## Mandatory Confirmation Sequence

Before any drink is prepared, confirm all of the following with the customer:

1. **Item name** — state the full name: "One Iced Caramel Macchiato."
2. **Size** — state explicitly: "Grande (16 oz)."
3. **Temperature** — confirm: "Iced." or "Hot."
4. **Milk type** — confirm if non-default: "With oat milk."
5. **Syrups** — list requested syrups and pump counts if modified: "Two pumps vanilla."
6. **Toppings** — list: "Caramel drizzle on top."
7. **Customizations** — list any other modifications: "No whip, light ice."
8. **Quantity** — confirm if more than one: "Two of those."
9. **Substitutions** — call out any substitutions made due to inventory: "We're using almond milk today."
10. **Final confirmation** — always end with: "Does that sound right?" or "Is that everything?"

## Short-Form Confirmation (Rush Mode)

During high-rush periods (rush_risk = "high"), use an abbreviated confirmation:
- "Grande iced oat milk latte — does that look right?"
- Still confirm size, temperature, and milk; skip individual syrup/topping recap unless they differ from default.

## When to Re-Confirm

Re-confirm with the customer if:
- Any ingredient was substituted due to low stock.
- The item was resolved via a menu search fallback (not exact match).
- The order has any human_review_required = True flag.
- The customer has expressed an allergy or dietary restriction.

## What NOT to Say

- Do NOT confirm calorie counts or nutritional values as exact figures.
- Do NOT make allergen guarantees: say "I believe this is made without [allergen]" not "This is [allergen]-free."
- Do NOT promise preparation time during rush — say "It will be ready shortly."

## Barista Prep Notes

After customer confirmation, the prep_notes field of the order should contain:
- The exact milk type.
- Syrup names and modifications.
- Topping list.
- Any special instructions in plain English.
- The note: "Prepare individually for quality consistency."

Example prep_notes:
```
Oat milk. 1 pump vanilla. Caramel drizzle. No whip. Prepare individually for quality consistency.
```
