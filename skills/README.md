# `skills/`

Skill contracts for BrewFlow AI. Each folder holds a `SKILL.md` that describes
when to invoke the step, which tools and RAG docs it uses, and the expected
output. The running console does not execute these files; the orchestrator
calls the tools and RAG layer directly and returns structured output.

| Skill | Folder | Role |
|---|---|---|
| product_catalog | `product_catalog/` | Answer menu questions (ingredients, nutrition, dietary) |
| recommendation | `recommendation/` | Inventory-aware drink recommendation |
| order_builder | `order_builder/` | Parse a natural-language order into structured fields |
| order_summary | `order_summary/` | Customer confirmation + barista prep note |
| workflow_orchestrator | `workflow_orchestrator/` | Full workflow chain and handoffs |

After adding a skill, run `bash install.sh` from the repo root to symlink
`SKILL.md` into `.claude/skills/`.
