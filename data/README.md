# `data/`

The operational data your workflow processes — cases, customers, dictionaries,
and the working rows your steps write during a run.

This is **separate** from [`../rag/knowledge_base/`](../rag/README.md).
`data/` holds operational records; `rag/` holds proprietary reference
knowledge. Don't mix them — they serve different parts of the assignment.

---

## Required layout

```
data/
├── raw/            # source-of-truth synthetic tables (people, cases, lookup tables)
├── processed/      # synthetic historical tables, one per workflow step
├── dictionaries/   # reference enumerations (categories, priorities, statuses)
└── working/        # written by skills + automations during a run (gitignored)
```

`working/` is regenerated on every run. Put a `.gitignore` inside it (this
template ships one) so nothing here is committed.

`processed/` is **synthetic history** — pre-seeded rows you generate so a
single step can be run in "demo" mode against a believable backlog without
re-running every upstream step.

---

## Adding your data

If your M02 work produced realistic synthetic tables (numpy + polars +
plotnine), reuse them — copy or symlink the generator under `data/` and
write the outputs to `data/raw/`. If not, two patterns from the reference
repo are worth copying:

| Pattern | What it does | Reference file |
| --- | --- | --- |
| Generator | One script that produces every CSV deterministically for a given seed. | `customer-ticket-process/data/generate_human_ticket_data.py` |
| Validator | One script that asserts schema + referential integrity and exits non-zero on any failure. | `customer-ticket-process/data/validate_human_ticket_data.py` |

Pair them. Run the validator in CI / before every demo run.

---

## Schema documentation

For every CSV you ship under `raw/` or `processed/`, document in this
README:

- **File name**
- **Primary key** column(s)
- **Foreign keys** to other tables
- **One-line purpose**
- **Which skill or automation writes it** (only for `processed/` and
  `working/`)

See `customer-ticket-process/data/README.md` for the schema-table format
to copy.

---

## What goes in `working/`

Each skill or automation appends **one row** per `(workflow_run_id,
step_id)` to a step-specific CSV under `working/`, plus one row to a shared
`workflow_action_log.csv`. The `utils/<project>_common.py` helpers
(`append_csv_row`, `append_action_log`) make this safe under concurrent
runs.

Working files are **not committed** — they're per-run scratch data.
