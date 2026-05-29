# Promotion Decision Policy

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

Defines when and how to apply active promotions, based on inventory risk,
demand conditions, and staffing levels.

## When to Apply a Promotion

Apply an active promotion when ALL of the following are true:
1. The promotion is within its active date range.
2. The promoted item's key ingredients are Healthy or Overstocked.
3. The store is not currently in a high-rush, understaffed state.
4. The customer has shown interest in the item or item category.

## When NOT to Apply a Promotion

- **inventory_risk = "High"**: Do not actively promote this item.
  - If a customer requests it: serve normally, but do not upsell.
- **Demand level = "Very High" + staffing_gap < 0**: Pause complex promotions.
  - Simplify the transaction; do not introduce promotional complexity during understaffed rush.
- **Ingredient is Low Stock or Unavailable**: Do not promote that item.
  - Promoting a low-stock item will deplete it faster and risk disappointing later customers.

## Overstock Opportunity

- When an ingredient is Overstocked: consider suggesting that item proactively.
- Cross-reference with promotion_margins.csv:
  - If gross_margin_pct is positive and inventory_risk is Low: recommend promoting.
  - If gross_margin_pct is negative or zero: do not recommend a further discount.

## Communicating Promotions to Customers

- Use natural, helpful language: "We're featuring [item] this week — it's great if you enjoy [flavor]."
- Do not pressure customers; one mention is sufficient.
- If the customer declines, proceed with their original request.

## Decision Summary Table

| Inventory Status | Rush Risk | Staff Gap | Promote? |
|---|---|---|---|
| Healthy / Overstock | Low | ≥ 0 | Yes |
| Healthy / Overstock | High | ≥ 0 | With caution |
| Healthy / Overstock | High | < 0 | No — simplify |
| Low Stock | Any | Any | No |
| Unavailable | Any | Any | No |

## Evidence Requirements

When a promotion is applied, the following must be recorded in the workflow evidence:
- Promotion name and item.
- Inventory status at time of recommendation.
- Demand level and staffing gap at time of recommendation.
- Whether the customer accepted or declined.
