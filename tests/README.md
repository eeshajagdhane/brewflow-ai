# `tests/`

Two kinds of tests live here:

1. **Unit tests** — same rule as M02/M03. Every Python function gets a
   happy-path test plus at least one edge case. Run with `uv run pytest`.
2. **DeepEval AI-performance tests** — new in M04. 8–12 cases that exercise
   your workflow end-to-end and score each answer against rules written
   in natural language. Lives in `test_workflow.py`. Results go in
   `results/`.

`uv run pytest` must be green before you submit.

---

## Unit-test layout

Mirror the source layout:

```
tests/
├── automations/
│   └── test_<name>.py        # one per automation
├── skills/
│   └── test_<name>.py        # one per LLM skill
├── mcp_servers/
│   └── test_<server>.py      # MCP server smoke tests
├── rag/
│   └── test_retrieval.py     # retrieval correctness + empty-result path
├── utils/
│   └── test_<helper>.py      # shared utilities
├── test_orchestrator.py      # end-to-end: at least one full happy-path workflow
├── test_workflow.py          # DeepEval AI-performance suite (M04)
└── results/                  # DeepEval run outputs (JSON/CSV)
```

---

## Run

```bash
uv run pytest                              # full suite (unit; DeepEval is integration-only)
uv run pytest tests/skills                 # just the LLM skills
uv run pytest -m integration               # the network-hitting integration tests
uv run pytest -m integration tests/test_workflow.py   # just the DeepEval suite
```

`conftest.py` (at the repo root) calls `load_dotenv()` so `TRITONAI_API_KEY`
is available to any test that needs it.

---

## Mocking LLM calls in unit tests

Unit tests must run **offline** — no real network calls. The pattern from
the reference repo: each LLM skill checks for a mock environment variable
before calling `utils.connect.ask_json()`. In tests, set the variable to
the expected JSON and the skill returns it verbatim instead of hitting
the network.

If you really want an end-to-end test against TritonAI, mark it
`@pytest.mark.integration` (already configured in `pyproject.toml`) and
run with `uv run pytest -m integration`. The marker keeps these tests off
the default run.

---

## DeepEval AI-performance suite (`test_workflow.py`)

This is the new M04 deliverable. The starter file shows the pattern:

1. **Build a small test set with 8–12 cases.** Each case has:
   - The input the user would give
   - What a good answer looks like (1–2 sentences)
   - The documents/data the AI should be using, if any
   - At least 2 cases tied to a failure listed in `failure_cases.md`

2. **Score each case with 4 checks:**
   1. **Stuck to the evidence?** — does the answer use the provided docs
      or did it invent details?
   2. **Answered the question?** — or did it drift to a related but less
      useful topic?
   3. **Quality rule?** — a plain-English rule turned into a check
      (e.g. *"answer cites the relevant policy, names the customer, ends
      with a clear next step"*).
   4. **Face validity?** — would a person who understands the business
      context find the result reasonable? Direction makes sense, magnitude
      is plausible, and the recommendation respects practical constraints
      (approvals, compliance, staffing, customer expectations). If the
      result is surprising, the reasoning explains why it is still plausible.

3. **Write results to `tests/results/`** and summarize them in
   `test_report.md`.

The DeepEval suite makes **real LLM calls** for both the workflow and
the scorer, so it is marked `@pytest.mark.integration` and skipped by
default. Run it explicitly:

```bash
uv run pytest -m integration tests/test_workflow.py
```

### A test case in practice

```text
Input: "Can a manager override the standard 30-day refund window for a long-time customer?"

Expected behavior: The AI cites the refund policy, notes the manager-override
                   clause, and recommends a next step.

What is checked:
  1. Stuck to the evidence: Does the answer use the refund policy document? (yes/no)
  2. Answered the question:  Does it address the override question,
                             not just refund basics? (yes/no)
  3. Quality rule:           Does it end with a clear next step? (yes/no)
  4. Face validity:          Would this recommendation make sense to a
                             customer support manager? (yes/no)

Result: Pass / Fail (with notes)
```

### Important notes

- A test set where everything passes on day one usually means the tests
  are too easy. The point is to **find weaknesses you would have
  missed**, not to look good in the report.
- DeepEval uses an AI to score another AI's answer, so any single score
  is noisy. **Trends across 8–12 cases** tell you more than any one case.
- Keep the test set in your repo. This is the artifact you would rerun
  whenever a teammate changes a skill, swaps a model, or updates a
  document. That is the difference between *"we built something once"*
  and *"we can keep it working."*

---

## A starter test ships here

- `tests/utils/test_connect.py` confirms that `from utils.connect import ask`
  imports cleanly. Keep it — quickest way to verify your `.venv` is set
  up correctly.
- `tests/test_workflow.py` is a runnable DeepEval skeleton: one example
  case and one example metric. Replace it with your real cases.
