# Milestone 04 — Student template

This is the **starter template** for Milestone 04 of MGT 449 / MGTA 495. It
builds on the Milestone 03 template (skills, MCP tools, RAG) and adds the
pieces specific to M04: a real user interface, an explicit human-review
plan, evidence/source displays, time/cost/quality reasoning, predicted
failure cases, and an automated DeepEval test suite.

Your assignment brief is in [`milestone04.qmd`](milestone04.qmd). The six
graded deliverables are:

1. **Final Process Redesign** — updated workflow diagram + 1–2 page explanation.
2. **Human Review and Control Plan** — table covering ≥6 process steps.
3. **User Interface** — at least 4 screens (start, AI work, evidence, review).
4. **Evidence and Source Use** — how RAG/tool output is shown to the user.
5. **Time, Cost, and Quality Reasoning** — before/after estimates with assumptions.
6. **Testing AI Performance** — 5+ predicted failures + 8–12 DeepEval test cases with results.

A final presentation pulls these together on **June 4**. There is also a
**May 28 checkpoint** for the RAG + current UI.

---

## Setup

```bash
uv sync                                       # installs deps into .venv (incl. deepeval)
cp .env.example .env && $EDITOR .env          # add TRITONAI_API_KEY
bash install.sh                               # registers skills with Claude Code
                                              #   (run again after you add a skill)
```

If you also want the MCP example to be invokable from Claude Code:

```bash
uv run mcp dev mcp_servers/example_server.py  # opens the MCP inspector
```

`uv run pytest` should pass on a fresh clone.

---

## Folder map

| Folder | What lives here |
| --- | --- |
| [`skills/`](skills/README.md) | LLM-based skills (one folder per skill; each has `SKILL.md` + `scripts/`) |
| [`automations/`](automations/README.md) | Deterministic Python steps (no LLM); same CLI contract as skills |
| [`mcp_servers/`](mcp_servers/README.md) | MCP servers that expose your skills + data as tools |
| [`rag/`](rag/README.md) | Proprietary knowledge base + retrieval code |
| [`ui/`](ui/README.md) | User interface for the workflow (≥4 screens) — **new in M04** |
| [`scripts/`](scripts/README.md) | Orchestrator + glue scripts |
| [`utils/`](utils/README.md) | Shared helpers (`connect.py` for LLM calls is already here) |
| [`data/`](data/README.md) | `raw/`, `processed/`, `working/`, `dictionaries/` data folders |
| [`tests/`](tests/README.md) | pytest + **DeepEval** test cases for AI performance — extended in M04 |
| [`presentation_slides/`](presentation_slides/README.md) | Final presentation materials — **new in M04** |

Top-level deliverable documents (fill these in):

- [`human_review_plan.md`](human_review_plan.md) — table of human review/control points
- [`evidence_and_sources.md`](evidence_and_sources.md) — how data/documents/tools are shown
- [`estimates.md`](estimates.md) — time, cost, and quality assumptions
- [`failure_cases.md`](failure_cases.md) — predicted failures and process handling
- [`test_report.md`](test_report.md) — DeepEval results, failure patterns, before/after

Add your workflow diagram as `ai_process_design.pdf` at the repo root.

Top-level files you should not need to edit:

- `install.sh` — auto-discovers every `skills/*/SKILL.md` and symlinks it into `.claude/skills/`
- `conftest.py` — loads `.env` before pytest collects
- `.env.example` — copy to `.env` and add your key
- `pyproject.toml` — uv-managed dependencies; add to it with `uv add <pkg>`
- `.mcp.json` — registers your MCP servers with Claude Code

---

## What's new in M04 (vs M03)

M03 gave you a working orchestrator with skills, MCP tools, and RAG. M04
asks: *if a real person used this every day, what would the interaction
look like, and how would you know it was working?* That breaks into four
new pieces of work:

### 1. A real UI (`ui/`)

The orchestrator's CLI is not enough. Build at least four screens:

1. **Start screen** (carried from M03, refined) — operator selects/enters the case.
2. **AI work screen** (carried from M03, refined) — operator watches the AI produce output.
3. **Evidence screen** (new) — structured display of retrieved docs, tool output, data rows.
4. **Review screen** (new) — approve / edit / reject / rerun / escalate, with each action wired to a real outcome.

See [`ui/README.md`](ui/README.md) for tool suggestions and the screen contract.

### 2. Human review plan (`human_review_plan.md`)

A table that names ≥6 workflow steps, what the AI does, what the human
does, whether approval is required, what could go wrong, and what happens
when it does. At least 1–2 rows must be explicit review/approval points.

### 3. Evidence and source use (`evidence_and_sources.md`)

A short doc explaining what data/documents/tools the AI uses, how the user
sees the evidence, and what happens when evidence is missing or weak.

### 4. Time, cost, and quality estimates (`estimates.md`)

Two tables: a per-step before/after time table (≥5 rows) and a summary
table. Use **reasoned assumptions and ranges** — not invented company data.

### 5. Failure cases + DeepEval tests (`failure_cases.md`, `tests/`, `test_report.md`)

- List **≥5 realistic failure cases** with consequence and handling.
- Build a **DeepEval test set of 8–12 cases**, run it, and write up the
  results, the 3 most common failure patterns, and one before/after fix.

See [`tests/README.md`](tests/README.md) for the DeepEval starter and
[`tests/test_workflow.py`](tests/test_workflow.py) for a runnable example.

---

## Timeline

- **May 28 (checkpoint):** RAG + current UI demo. Two teams selected to share.
- **June 4 (final):** All deliverables + final presentation. Push to GitHub before class.

---

## Before you submit

- [ ] Workflow diagram + 1–2 page explanation in `ai_process_design.pdf`.
- [ ] `human_review_plan.md` covers ≥6 steps with ≥1–2 review points.
- [ ] `ui/` has at least 4 working screens.
- [ ] `evidence_and_sources.md` answers all 5 questions in the brief.
- [ ] `estimates.md` has the per-step table (≥5 rows) and the summary table.
- [ ] `failure_cases.md` lists ≥5 realistic failures.
- [ ] `tests/test_workflow.py` runs 8–12 DeepEval cases and writes results to `tests/results/`.
- [ ] `test_report.md` summarizes results, top-3 failure patterns, and one before/after fix.
- [ ] `uv run pytest` is green.
- [ ] `presentation_slides/` contains the final deck.

---

## Reading the reference repo

The `customer-ticket-process/` reference repo your instructor shared is
still the worked example for skills, MCP, RAG, and the orchestrator. M04
adds new pieces (UI, review plan, estimates, DeepEval) that are
project-specific — there is no reference to copy from. Start small,
make it work, then make it better.
