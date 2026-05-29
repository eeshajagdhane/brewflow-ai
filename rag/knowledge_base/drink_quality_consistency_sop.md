# Drink Quality and Consistency SOP

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

Defines quality standards and preparation protocols for all beverages.
The primary rule: every drink is prepared individually.

## Core Quality Principle

> **Drinks are prepared individually for quality consistency.**
> Do not batch, group, or combine preparations for multiple orders unless
> explicitly part of an approved batch-preparation protocol for specific items.

Rationale: Individual preparation ensures:
- Correct customization per order.
- Consistent temperature and texture.
- Accurate topping and syrup placement.
- No cross-contamination between orders with different dietary requirements.

## Preparation Standards

### Espresso-Based Drinks
- Pull espresso shots fresh for each order. Never use pre-pulled shots that have sat > 10 seconds.
- Steam milk to the correct temperature per size and drink type.
- Add syrups before or after espresso as specified by the drink recipe.
- Confirm customizations (milk type, syrup count, toppings) match the order before handing off.

### Cold Drinks
- Ensure ice is added to the correct amount (standard / light / extra / none per order).
- Cold brew is pre-made in batch but poured per order.
- Shaken drinks must be freshly shaken per order.

### Frappuccinos
- Blend per order — do not pre-blend and hold.
- Confirm cup size, toppings, and whip preference before handing off.

### Hot Tea
- Use fresh water per order; do not reuse water that has sat > 5 minutes.
- Steep time per tea type as per recipe guidance.

## Customization Verification

Before handing off any drink:
1. Read the order label or order_summary output aloud.
2. Confirm: item name, size, temperature, milk, key customizations.
3. If any field was substituted (due to inventory): verbally inform the customer.

## Quality Failure Recovery

If a drink is prepared incorrectly:
1. Acknowledge the error immediately.
2. Prepare a new drink — do not attempt to "fix" the existing one.
3. Log the incident if it results in a customer complaint.
4. See service_recovery_policy.md for communication guidance.

## Note for AI-Assisted Order Building

- The order_builder skill must include "Prepare individually for quality consistency."
  in prep_notes for every order.
- Do not imply that multiple items of the same kind will be prepared together.
