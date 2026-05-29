# Inventory Substitution SOP

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

Defines the procedure for handling ingredient shortages and recommending substitutions
when an item's key ingredient is low stock or unavailable.

## Stock Status Definitions

| Status | Definition | Action |
|---|---|---|
| Healthy | Stock above reorder point | No action needed |
| Low Stock | Stock at or below reorder point | Monitor; prefer other items |
| Unavailable (Critical Low) | Stock effectively depleted | Remove from service immediately |
| Overstock | Excess stock | Promote item if margin allows |

## Decision Tree

### Ingredient is Healthy
- Recommend item normally.
- No substitution needed.

### Ingredient is Low Stock
- Do not proactively recommend this item during rush periods.
- If customer specifically requests the item:
  1. Inform barista to check actual physical stock before preparing.
  2. Offer an alternative in the same flavor family as a backup.
  3. Document the low-stock flag in the order evidence.
- Do NOT tell the customer the ingredient is low — only say "Let me check availability."

### Ingredient is Unavailable
- Do NOT prepare or promise the item.
- Apologize and offer an alternative immediately.
- Inform the manager — this should already be flagged in the daily briefing.
- Do not override an unavailable status without explicit manager approval.
  Manager override must be logged in the audit trail.

## Substitution Groups

| Original Ingredient | Acceptable Substitution |
|---|---|
| Oat Milk | Almond Milk, Soy Milk |
| Almond Milk | Oat Milk, Soy Milk |
| Soy Milk | Oat Milk, Almond Milk |
| Whole Milk | 2% Milk |
| 2% Milk | Whole Milk or Nonfat |
| Espresso Beans | No substitute — offer decaf or brewed coffee alternative |
| Matcha Powder | No direct substitute — offer Green Tea |
| Dragonfruit Powder | No substitute — remove Refresher from service |

## Communicating Substitutions

1. Always inform the customer of the substitution before preparing.
2. Use positive language: "We're using oat milk today instead — it works great in this drink."
3. If the customer declines the substitution, offer an alternative item entirely.
4. Record the substitution in the order's customizations and prep_notes fields.

## Escalation

- If more than 3 ingredients are unavailable simultaneously, escalate to manager immediately.
- Manager should update barista_guidance.avoid_ingredients for the current shift.
- See service_recovery_policy.md for customer communication if the store is significantly impacted.
