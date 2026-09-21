# `data/`

Operational records for the workflow. Separate from
[`../rag/knowledge_base/`](../rag/README.md), which holds policy and SOP text.

`data/raw/` is the simulated store: public Starbucks menu plus invented
inventory, staffing, sales forecast, order history, and promotions. Nothing
here is proprietary Starbucks operations data.

```
data/
├── raw/        source CSVs (read-only)
└── working/    written during a run (gitignored)
```
