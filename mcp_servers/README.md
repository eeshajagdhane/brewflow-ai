# `mcp_servers/`

Callable tools used by the orchestrator. `brewflow_mcp_server.py` is the
active server (6 tools). `example_server.py` is a wiring stub.

The orchestrator and tests call these as plain Python functions. An MCP
runtime is not required.

| Tool | Purpose |
|---|---|
| `get_menu_item_info(item_name)` | Menu lookup with ambiguity handling |
| `search_menu_by_preferences(prefs, store_id, date, hour)` | Ranked candidates with inventory + promo scoring |
| `check_inventory_status(store_id, date, ingredients)` | Per-ingredient availability, latest-prior fallback |
| `detect_rush_period(store_id, date, hour)` | Demand level and rush risk |
| `calculate_staffing_gap(store_id, date, hour)` | Staffing shortfall and risk |
| `build_and_validate_order(raw_order, store_id, date)` | Parse an order; detect missing fields; flag allergy |

See the docstrings in `brewflow_mcp_server.py` for input/output specs.
