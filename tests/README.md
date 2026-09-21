# `tests/`

95 local, deterministic tests. No API keys.

| File | Coverage |
|---|---|
| `test_mcp_tools.py` | All 6 tools + data file checks |
| `test_rag_retrieval.py` | Knowledge-base docs + query scenarios |
| `test_brewflow_workflow.py` | All 4 orchestrator functions |
| `test_face_validity.py` | Face-validity rules + allergy false-positive regression |
| `test_ui_routes.py` | Flask routes hit the live orchestrator |

```bash
uv run pytest tests/ -v
```

`test_workflow.py` is an optional DeepEval suite and is skipped unless
marked. `results/test_summary.md` labels representative cases.
