# `utils/`

Shared helpers used by the orchestrator, tools, and tests.

| File | Purpose |
|---|---|
| `data_loader.py` | Load CSVs from `data/raw/` |
| `menu_matching.py` | Item-name resolution |
| `inventory_matching.py` | Ingredient mapping + latest-prior snapshot fallback |
| `workflow_common.py` | Step, audit, tool, and workflow envelopes |
| `evidence.py` | Evidence package and quality score |
| `face_validity.py` | Deterministic plausibility verdict on every run |
| `connect.py` | Optional OpenAI-compatible LLM client (not used by the console) |

Face validity is a review layer, not a skill or a tool. It reads artifacts
the orchestrator already built and returns status, confidence, anchors,
reasons, and concerns for the UI card.
