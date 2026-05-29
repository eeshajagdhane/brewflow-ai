# Barista Recommendation Guidelines

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

This document guides baristas on how to recommend drinks based on customer preferences.
Use it alongside the BrewFlow AI recommendation skill to produce helpful, accurate suggestions.

## Core Recommendation Principles

- Always ask at least one clarifying question before recommending: hot or cold? caffeine or not?
- Base every recommendation on available menu data, not guesswork or assumptions.
- If inventory data flags an ingredient as unavailable, do not recommend that item without manager approval.
- Never guarantee nutritional or allergen content — direct the customer to official sources.

## Preference-Matching Guidelines

### Temperature
- Hot preference → suggest Hot Coffee, Hot Tea, or Hot Drinks category items.
- Cold/iced preference → suggest Cold Coffee, Iced Tea, Cold Drinks, or Frappuccino.
- If customer is unsure, ask whether they prefer a warming or refreshing drink.

### Caffeine
- Wants caffeine → espresso-based drinks (latte, macchiato, Americano) or Cold Brew.
- Wants no/low caffeine → herbal teas, Passion Tango, Refreshers (no espresso).
- Wants decaf → any espresso drink can typically be ordered decaf (confirm with barista).

### Sweetness
- Sweet → flavored lattes with vanilla, caramel, or hazelnut syrup; Frappuccino range.
- Less sweet → plain brewed coffee, Americano, unsweetened tea.
- Fruity → Refreshers, Pink Drink, Iced Passion Tango Tea Lemonade.

### Dairy-Free / Vegan
- Suggest items marked Vegan=Yes in the menu, or items where milk can be swapped to oat/almond/soy.
- Flag that cross-contact cannot be guaranteed — see dietary_allergen_guidance.md.
- Do NOT promise dairy-free in a shared equipment environment.

### Non-Coffee / Coffee-Averse
- Suggest: herbal teas, matcha lattes, chai lattes, Refreshers, hot chocolate.
- Avoid: any drink with espresso, cold brew, or brewed coffee as a key ingredient.

### Low Calorie
- Prioritize items with ≤ 150 kcal per serving size.
- Unsweetened teas, plain cold brew, and iced coffee (no milk/syrup) are typically low-calorie.
- Mention that syrup and milk choices significantly affect calorie counts.

## During Rush Periods

- Keep recommendations to 2–3 options maximum.
- Lead with the most popular, fastest-to-prepare option.
- If rush risk is HIGH (per demand_rush_detection), avoid recommending highly customized drinks unless customer specifically requests.
- Reference rush_hour_service_playbook.md for rush-specific protocols.

## Handoff to Order Builder

- Once a recommendation is accepted, pass the item name and customer preferences to the order_builder skill.
- Include: item name, size preference, temperature, milk type, any syrups or customizations confirmed.
