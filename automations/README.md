# `automations/`

> **BrewFlow AI — Active Automations** (see folders below for Python files).
> The course template content below is preserved as reference.

## Active BrewFlow Automations

| Automation | Entry Point | Data Source | Purpose |
|---|---|---|---|
| inventory_monitoring | `inventory_monitoring/run_inventory_monitoring.py` | `store_inventory.csv` | Classify each ingredient: low/healthy/overstock/unavailable |
| staffing_gap_calculator | `staffing_gap_calculator/run_staffing_gap_calculator.py` | `staff_schedule.csv` | Staffing gap and risk for a store/date/hour |
| demand_rush_detection | `demand_rush_detection/run_demand_rush_detection.py` | `daily_sales_forecast.csv` | Demand level and rush risk lookup |
| manager_daily_briefing | `manager_daily_briefing/run_manager_daily_briefing.py` | All four CSVs | Combined pre-shift briefing with recommended manager actions |

All automations are deterministic — no LLM calls. Each returns the standard tool response envelope.

---

An **automation** is a deterministic Python step in your workflow — no LLM
call, no judgement. Examples: look up a customer in a CSV, score keywords,
fill a template, validate a schema, join tables, audit a run.

This folder is **empty**. Add your automations here. There is no upper
limit; in the reference repo most workflow steps are automations.

---

## Required layout

```
automations/<your-step-name>/
├── README.md             # what the automation does + how to run it
└── scripts/<name>.py     # the executable; pure Python, no LLM
```

No `SKILL.md` here — there's no agent decision to make. The orchestrator
just runs the script as a subprocess.

---

## Same contract as a skill

Automations use the **same CLI flags and the same JSON envelope** as skills.
That's deliberate: the orchestrator can run any step the same way. See
[`../skills/README.md`](../skills/README.md) for the flag list and envelope
shape.

The shared CLI parser lives in `utils/` — write it once, import it from
every automation and every skill.

---

## When to choose an automation over a skill

| Use an automation | Use a skill |
| --- | --- |
| Deterministic transform | Genuine judgement call |
| Lookup, join, validation | Classification, drafting, decision under ambiguity |
| Template fill, regex extract | Free-text generation, evaluation, summarisation |
| Easy to unit-test | Needs an LLM to be testable |

LLM calls are slow, costly, and non-deterministic. Use them only where they
add real value.

---

## Reference (read these)

- `customer-ticket-process/automations/classify-prioritize-ticket/` —
  a typical deterministic step: reads upstream rows, applies rules, writes
  one row to `data/working/triage_decisions.csv`, returns a JSON envelope.
- `customer-ticket-process/automations/receive-ticket/` — the simplest
  automation in the reference (~70 lines including the envelope).
- `customer-ticket-process/automations/audit-ticket-process/` — an
  end-of-run audit that summarises everything in `data/working/`. Good
  pattern for your final reporting step.
