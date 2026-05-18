# `ui/`

The user interface for your AI-coworker workflow. M04 requires **at least
four screens or views** — two carried forward from M03 (refined) and two
new for M04. Together they should make clear, to someone who has never
seen the workflow, how an operator starts a case, watches the AI work,
inspects evidence, and approves or rejects the result.

---

## Required screens

1. **Start screen** *(carried from M03, refined)* — operator enters or
   selects the case (customer, ticket, campaign, report, request, …).
   Add input validation, an example case, or a clearer layout.
2. **AI work screen** *(carried from M03, refined)* — shows the AI's
   output: draft, recommendation, classification, summary, forecast,
   action plan. Add step-by-step progress, a confidence indicator, or a
   cleaner result layout.
3. **Evidence screen** *(new)* — *structured* display of what the AI
   used: retrieved documents (with the relevant passage highlighted or
   quoted), source links, data rows, tool outputs, assumptions. The user
   should be able to tell at a glance whether the evidence supports the
   AI's output.
4. **Review screen** *(new)* — approve / edit / reject / rerun /
   escalate. Each control must do something *real*: where does
   "escalate" send the case, what does "rerun" retry, what happens to a
   rejected draft?

---

## Recommended extras

- Dashboard with process metrics
- Log of previous AI actions
- Errors / low-confidence cases view
- Settings (operator-editable instructions)
- Before/after comparison of the old vs new process

You are not restricted to these views — be creative about what makes the
workflow easier to understand and use within your business context.

---

## Tool suggestions

- [Claude Design](https://www.anthropic.com/news/claude-design-anthropic-labs)
- [Google Stitch](https://stitch.withgoogle.com/)
- A small FastAPI + plain HTML/JS app is also fine.

Whatever you pick, the UI must call your orchestrator / skills / RAG
code — not just mock the output.

---

## Suggested layout

```
ui/
├── README.md
├── app.py                  # main entry point
├── screens/
│   ├── start.py
│   ├── ai_work.py
│   ├── evidence.py
│   └── review.py
└── static/                 # any images, css, etc.
```

If you use a different framework, mirror the same idea: one file per
screen so the four required views are easy to find.

---

## How the UI talks to the workflow

Your UI should call:

- The orchestrator (or individual skills) to run the workflow.
- `rag/retrieval.py` to fetch evidence to display.
- The MCP tools (or their underlying Python functions) where appropriate.

Keep business logic out of the UI files — those should be thin views over
the orchestrator and skills.

---

## May 28 checkpoint

By May 28, the UI should include the start + AI-work screens carried
over from M03, plus an in-progress version of the new evidence and
review screens. It does not need to be polished.
