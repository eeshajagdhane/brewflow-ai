# `automations/`

Deterministic Python steps. No LLM. Each returns the standard tool envelope.

| Automation | Entry point | Data | Purpose |
|---|---|---|---|
| inventory_monitoring | `inventory_monitoring/run_inventory_monitoring.py` | `store_inventory.csv` | Classify ingredients: low / healthy / overstock / unavailable |
| staffing_gap_calculator | `staffing_gap_calculator/run_staffing_gap_calculator.py` | `staff_schedule.csv` | Staffing gap and risk for a store / date / hour |
| demand_rush_detection | `demand_rush_detection/run_demand_rush_detection.py` | `daily_sales_forecast.csv` | Demand level and rush risk |
| manager_daily_briefing | `manager_daily_briefing/run_manager_daily_briefing.py` | All four CSVs | Combined pre-shift briefing |

Use an automation when the step is a lookup, join, threshold, or template fill.
Use a skill contract when the step needs judgement.
