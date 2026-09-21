# `scripts/`

The orchestrator. Four functions the UI calls directly:

```python
from scripts.orchestrator import (
    run_manager_readiness,
    run_barista_recommendation,
    run_order_builder,
    run_full_workflow,
)

result = run_full_workflow("SD001", "2024-01-15", 8, "iced drink", raw_order="Grande iced latte")
```

Each function returns UI-ready JSON: `run_id`, `steps`, `final_output`,
`evidence_package`, `review_queue`, `review_actions`, `audit_log`,
`warnings`, `face_validity`.

`build_design_pdf.py` is a documentation helper. It is not part of the
runtime.
