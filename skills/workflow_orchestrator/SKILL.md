# Skill: workflow_orchestrator

## Purpose

Describes the complete BrewFlow AI workflow — how skills, automations, MCP tools,
and RAG retrieval are chained together from manager readiness through order confirmation.

This skill is a design document for the orchestrator logic in `scripts/orchestrator.py`.
It does not duplicate tool logic; it describes how they connect.

## Workflow Overview

```
Manager Readiness
  ├── detect_rush_period
  ├── calculate_staffing_gap
  ├── check_inventory_status
  ├── retrieve_internal_knowledge (manager policies)
  └── manager_daily_briefing
        └── barista_guidance ──────────────────────────────┐
                                                            ▼
Barista Recommendation                            (rush_level informs tone)
  ├── detect_rush_period
  ├── retrieve_internal_knowledge (recommendation + dietary + rush)
  ├── search_menu_by_preferences
  └── check_inventory_status
        └── top_candidates ────────────────────────────────┐
                                                            ▼
Order Builder
  ├── build_and_validate_order
  ├── get_menu_item_info
  ├── check_inventory_status
  └── retrieve_internal_knowledge (confirmation + quality SOP)
        └── structured_order ──────────────────────────────┐
                                                            ▼
Order Summary
  └── (uses structured_order from order_builder)
        └── customer_confirmation + barista_prep_note ─────┐
                                                            ▼
Human Review / Evidence Package
  ├── review_queue (items flagged for review)
  ├── evidence_package (all tool outputs + RAG results)
  ├── audit_log (all actions timestamped)
  └── review_actions: approve | edit | reject_rerun | escalate
```

## Handoff Requirements

| From | To | What is Passed |
|---|---|---|
| manager_daily_briefing | recommendation | `barista_guidance` dict (rush_level, avoid_ingredients, caution_ingredients, promotion_items) |
| recommendation | order_builder | `item`, `preferences`, `substitutions` |
| order_builder | order_summary | `structured_order`, `prep_notes`, `inventory_warnings` |
| order_summary | finalized | `customer_confirmation`, `barista_prep_note`, `audit_entry` |

## Evidence and Audit Requirements

Every workflow step must:
1. Append its tool outputs to `evidence_package.tool_outputs`.
2. Append retrieved RAG docs to `evidence_package.rag_results`.
3. Append an audit entry to `audit_log`.
4. Include `warnings` in the step record.

The evidence package enables the human reviewer to trace every output back to
a specific data source or knowledge base document.

## Human Review Triggers

Human review is required when:
- `human_review_required = True` from any tool call (allergy, unavailable ingredient).
- `missing_fields` is not empty in the order_builder output.
- `staffing_gap < -1` during a high-rush period.
- Any `inventory_unavailable` items exist at shift start.

## Running the Orchestrator

```python
from scripts.orchestrator import (
    run_manager_readiness,
    run_barista_recommendation,
    run_order_builder,
    run_full_workflow,
)

# Pre-shift readiness
result = run_manager_readiness("SD001", "2024-01-15", 8)

# Recommendation for a customer
result = run_barista_recommendation("SD001", "2024-01-15", 8, "something cold", {"temperature": "cold"})

# Order from raw text
result = run_order_builder("SD001", "2024-01-15", "Grande iced latte with oat milk")

# Complete workflow
result = run_full_workflow("SD001", "2024-01-15", 8, "iced drink",
                           raw_order="Grande iced latte with oat milk",
                           preferences={"temperature": "cold"})
```

## What This Skill Does NOT Do

- It does not make LLM calls.
- It does not read CSV files directly (tools and automations do that).
- It does not maintain state between workflow runs (each run is independent).
- It does not produce UI output (the future UI calls these functions and renders the output).
