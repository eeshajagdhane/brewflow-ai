# Rush Hour Service Playbook

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

Defines service protocols for high-demand periods to maintain quality and throughput.
Use when rush_risk = "high" or demand_level = "Very High" / "Extreme".

## Identifying a Rush Period

Rush conditions are flagged when:
- demand_level is "Very High" or "Extreme" (from detect_rush_period / demand_rush_detection)
- rush_risk = "high"
- Actual orders per hour exceeds forecast by > 15%
- A local event is flagged (local_event_flag = "Yes")

## Barista Protocols During Rush

### Recommendations
- Limit drink recommendations to 2 items maximum.
- Lead with the fastest-to-prepare option in the requested category.
- Avoid recommending highly customized drinks (more than 2 modifications) — politely suggest a simpler alternative.
- Confirm size and temperature immediately; do not leave these open.

### Order Taking
- Repeat the full order back before preparing (see order_confirmation_standard.md).
- If an item requires inventory confirmation, do not hold up the queue — flag for manager and offer alternatives.
- Prioritize mobile and drive-through orders if configured.

### Communication
- Inform customers of expected wait times if > 5 minutes.
- Use clear, brief language: "Your Grande Iced Latte will be ready in about 4 minutes."
- Do NOT apologize excessively — one brief acknowledgment is sufficient.

## Manager Protocols During Rush

- Verify all baristas are on station and know the current rush level.
- Monitor the espresso station stock every 30 minutes during a rush.
- If staffing_gap < 0 and demand_level = "Very High":
  - Consider assigning the manager to a barista support role.
  - Temporarily simplify the menu by pausing items with complex preparation.
- Communicate delays proactively to waiting customers.
- After the rush: complete the post_rush_manager_review_template.md checklist.

## Inventory During Rush

- Do not offer items with low-stock ingredients during rush unless no alternatives exist.
- If an ingredient runs out mid-rush, update barista_guidance.avoid_ingredients immediately.
- See inventory_substitution_sop.md for substitution decisions.

## Post-Rush

- Log the peak hour, actual demand, staffing coverage, and any incidents.
- Use post_rush_manager_review_template.md to structure the review.
- Restock depleted ingredients before the next forecast peak window.
