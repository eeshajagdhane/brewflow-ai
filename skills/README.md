# `skills/`

A **skill** is a folder containing a `SKILL.md` file (which a Claude Code /
Codex agent loads at runtime to decide when the skill applies) and a script
the agent invokes that does the work. In this milestone, skills are the
steps that **need LLM judgement** — classification, drafting, summarising,
decision-making. Deterministic steps go in [`../automations/`](../automations/README.md).

This folder is **empty**. Add your own skills here. Goal: **3–5 connected
skills** that together complete a multi-step portion of your Milestone 01
workflow.

---

## Required layout

```
skills/<your-skill-name>/
├── SKILL.md              # agent contract: when to invoke, expected I/O
├── README.md             # human-readable docs
└── scripts/<name>.py     # the executable; calls an LLM via utils.connect.ask()
```

After you add a skill, run from the repo root:

```bash
bash install.sh
```

This symlinks every `skills/*/SKILL.md` into `.claude/skills/<name>/` so
Claude Code finds it. Re-run after adding new skills.

---

## SKILL.md format

YAML frontmatter + Markdown body. The reference repo's
[`skills/check-faq-resolution/SKILL.md`](../../customer-ticket-process/skills/check-faq-resolution/SKILL.md)
is the model:

```markdown
---
name: your-skill-name
description: One sentence the agent reads to decide whether to invoke this skill.
---

# Title

## Runtime modes
(can be invoked from a terminal, from the orchestrator, or by an agent)

## What the script needs
(CLI flags + required upstream data)

## How to use this skill
(numbered steps the agent should follow)

## What the LLM receives
(what gets stuffed into the prompt)

## Example
(one short example invocation + expected outcome)
```

---

## Standard CLI flags

Every skill script must accept these flags so the orchestrator can drive any
skill the same way. Build them with one shared helper (see
[`../utils/README.md`](../utils/README.md)):

| Flag | Meaning |
| --- | --- |
| `--case-id` | The entity the skill acts on. **Rename to fit your domain** — `--ticket-id`, `--application-id`, `--claim-id`, `--candidate-id`, etc. |
| `--data-dir` | Where to read source data (default `data`) |
| `--out-dir` | Where to write working CSVs (default `data/working`) |
| `--workflow-run-id` | Identifier for one end-to-end run, set by the orchestrator |
| `--step-id` | Identifier for this step within the run |
| `--mode {live,demo}` | live = use only fresh `data/working/`; demo = also accept seeded `data/processed/` |
| `--idempotency-mode {skip,replace}` | Re-running same `(workflow_run_id, step_id)` — skip (default) or rewrite |
| `--json` | Emit a JSON envelope on stdout instead of a human-readable summary |

The reference repo's `customer-ticket-process/utils/ticketing_common.py`
implements `make_skill_parser()` for exactly this set. Copy/adapt that file
to `utils/<project>_common.py` — don't reinvent it.

---

## The JSON envelope

Every skill prints one JSON object on stdout when called with `--json`:

```json
{
  "status": "ok",
  "skill_name": "your-skill-name",
  "workflow_run_id": "wf-...",
  "step_id": "your-skill-name-...",
  "case_id": "CASE-00042",
  "next_action": "name-of-the-next-skill",
  "confidence": 0.91,
  "review_required": false,
  "artifact_refs": ["working/your_decisions.csv"],
  "outputs": {"...": "..."},
  "error": null
}
```

The orchestrator reads `next_action` to decide what to run next. A human
reads `review_required` to know when to step in. Errors return the same
shape with `status="error"`, `error={"code": "...", "message": "..."}`, and
exit code ≠ 0.

---

## Chaining skills (the M03 grade)

A workflow is several skills that hand off to each other. Three handoff
patterns, all in use in the reference repo:

1. **Envelope `next_action`** — skill A writes `next_action: "skill-b"` and
   the orchestrator runs `skill-b` next.
2. **Working CSVs** — skill A appends a row to `data/working/your_decisions.csv`
   and skill B reads the latest row for the same `case_id`.
3. **Audit log** — every skill appends to `data/working/workflow_action_log.csv`
   so you can replay or debug an entire run.

Keep the orchestrator's decision logic in plain Python (see
[`../scripts/README.md`](../scripts/README.md)). LLMs decide *within* a
skill; the orchestrator decides *between* skills.

---

## Skill vs. automation — the rule

Put a step under `skills/` only if a human would need **judgement** to do it.
Otherwise it goes under [`../automations/`](../automations/README.md).
Telltale signs of a real skill: the right answer depends on context, there
is ambiguity, or you would ask a teammate "what do you think?". Telltale
signs of an automation: rules, look-ups, joins, schema validation, template
fills.

The reference repo has **11 steps and only 2 skills**. Most of your steps
should be automations. AI earns its keep on the genuine judgement calls;
the rest of the process stays deterministic, auditable, and fast.

---

## Reference (read these)

- `customer-ticket-process/skills/check-faq-resolution/` — a complete LLM
  skill. Start here. Copy the four files (`SKILL.md`, `README.md`,
  `scripts/check_faq_resolution.py`, plus the entries it adds to
  `utils/ticketing_common.py`), rename, change the LLM prompt, change the
  CLI flag from `--ticket-id` to your domain entity.
- `customer-ticket-process/skills/investigate-specialist-solution/` — a
  second LLM skill that shows how `ask_json()` is used with a structured
  pydantic schema.
