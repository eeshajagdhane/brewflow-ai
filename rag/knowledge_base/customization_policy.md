# Customization Policy

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

Defines acceptable drink customizations, how to confirm them with the customer,
and how to communicate them to the barista preparing the order.

## Standard Customizations

### Milk Swaps
- Available: Whole Milk, 2% Milk, Nonfat (Skim) Milk, Oat Milk, Almond Milk, Soy Milk, Coconut Milk.
- Default milk is 2% for most espresso drinks unless specified.
- Charge may apply for non-dairy milk alternatives (check current pricing).
- If a milk alternative is low stock, suggest the next available alternative and note the substitution.

### Syrup Pumps
- Standard pumps: Tall=1, Grande=2, Venti=3.
- Customer may request fewer pumps ("half sweet"), more pumps ("extra"), or a specific syrup.
- Sugar-free syrups available for certain flavors (vanilla, caramel) — confirm availability.
- Do not add syrups not listed in the menu without manager approval.

### Temperature and Ice
- Hot: served steaming at standard temperature.
- Iced: served over ice, cold.
- Light ice: standard cold preparation with less ice — may taste more diluted.
- Extra ice: standard preparation with more ice.
- No ice: available; note that drink volume may not increase to compensate.

### Whipped Cream
- Default: included on Frappuccinos, some hot drinks.
- No whip: remove whipped cream on request, no charge.
- Extra whip: additional charge may apply.

### Size and Temperature Clarification
- Always confirm size if not provided: Short (8 oz), Tall (12 oz), Grande (16 oz), Venti (20 oz hot / 24 oz cold), Trenta (30 oz, cold only).
- Venti hot and Venti cold are different volumes — confirm if customer is switching between formats.
- If the menu item is not available in a requested size, inform the customer of available sizes.

### Toppings
- Cold foam, sweet cream, caramel drizzle, mocha drizzle: available as add-ons.
- Cinnamon powder, nutmeg: available at no charge on most drinks.

## What NOT to Customize

- Do not modify espresso shot count beyond what the menu supports without barista guidance.
- Do not invent combinations not offered on the menu.
- If a customization would make a drink unrecognizable from its menu description, flag for barista confirmation.

## Documenting Customizations in Order Builder

Every confirmed customization must appear in the structured_order output:
- milk_type: the selected milk
- syrups: list of requested syrups (names only)
- toppings: list of confirmed toppings
- customizations: any other modifier (light ice, no whip, extra foam, decaf)
- prep_notes: human-readable barista instructions
