# Manager Pre-Shift Checklist

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

A structured checklist that managers complete before each shift opens, using
data from the manager_daily_briefing automation and BrewFlow readiness tools.

## Step 1: Demand Check

- Run detect_rush_period / manager_daily_briefing for the upcoming 2-hour window.
- Note: demand_level, rush_risk, forecast_orders.
- If rush_risk = "high": activate rush_hour_service_playbook.md protocols.
- If local_event_flag = "Yes": brief baristas on expected volume increase.

## Step 2: Staffing Check

- Run calculate_staffing_gap for the opening shift hour.
- Note: required_staff, scheduled_staff, staffing_gap, callout_count.
- If staffing_gap < 0:
  - Attempt to call in backup staff.
  - If backup unavailable, reduce menu complexity for the first 2 hours.
  - Log the gap and decision in the manager audit trail.
- If callout_count > 0: verify who called out and confirm remaining coverage.

## Step 3: Inventory Check

- Run check_inventory_status / run_inventory_monitoring for today's date.
- Review: unavailable list, low_stock list.
- For every unavailable ingredient:
  - Remove affected items from barista guidance.
  - Update barista_guidance.avoid_ingredients.
  - Consider substitution per inventory_substitution_sop.md.
- For low stock items: alert baristas and initiate reorder if possible.

## Step 4: Promotions Review

- Check active_promotions from manager_daily_briefing output.
- For each promotion:
  - Confirm inventory levels support the promotion.
  - If inventory_risk = "High" for a promotion: pause or limit the promotion.
  - Brief baristas on active promotions to suggest during appropriate interactions.
- See promotion_decision_policy.md for full decision criteria.

## Step 5: Communicate to Baristas

- Hold a 5-minute pre-shift stand-up covering:
  1. Expected demand level and rush windows.
  2. Any staffing changes or coverage gaps.
  3. Items to avoid (unavailable) and caution (low stock).
  4. Active promotions to suggest.
  5. Any special customer notes or local events.

## Sign-Off

Before opening, confirm:
- [ ] Demand briefing reviewed.
- [ ] Staffing gaps addressed.
- [ ] Unavailable items removed from service.
- [ ] Baristas briefed.
- [ ] Espresso station stocked.
- [ ] Promotion items confirmed available.
