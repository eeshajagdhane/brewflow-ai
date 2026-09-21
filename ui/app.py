"""BrewFlow AI Operations Console — Flask UI.

A thin web layer over the existing BrewFlow orchestrator.  Every workflow
route calls the *live* orchestrator function in `scripts.orchestrator` and
returns its JSON envelope verbatim.  No canned outputs.  No external APIs.
No database — UI-side review actions are kept in an in-process audit list.

Run locally::

    uv run python ui/app.py
    # then open http://127.0.0.1:5000

The single HTML page renders six tabs (Full Workflow, Manager, Barista,
Order Builder, Evidence Center, Review Queue) plus an always-visible Audit
Log footer.  All four review actions (approve / edit / reject_rerun /
escalate) post to `/api/review_action` which only updates the UI state and
appends to the audit log.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

# Make the project root importable when running `python ui/app.py` directly.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from flask import Flask, jsonify, render_template, request  # noqa: E402

from scripts.orchestrator import (  # noqa: E402
    run_barista_recommendation,
    run_full_workflow,
    run_manager_readiness,
    run_order_builder,
)


# ---------------------------------------------------------------------------
# In-process audit store for UI-side review actions
# ---------------------------------------------------------------------------
# Each entry is a plain dict: {timestamp, source, action, workflow_type,
# message, payload}.  Cleared on app restart — there is no DB.

_AUDIT_LOG: list[dict] = []
_AUDIT_LOCK = Lock()

# ---------------------------------------------------------------------------
# In-process Order Queue
# ---------------------------------------------------------------------------
# Category display order for smart grouping (lower = earlier in queue)
_CATEGORY_ORDER: dict[str, int] = {
    "Hot Coffee": 0,
    "Cold Coffee": 1,
    "Frappuccino": 2,
    "Hot Tea": 3,
    "Iced Tea": 4,
    "Cold Drinks": 5,
    "Hot Drinks": 6,
    "Bottled Beverages": 7,
    "Bakery": 8,
    "Breakfast": 9,
    "Lunch": 10,
    "Snacks & Sweets": 11,
}

_ORDER_QUEUE: list[dict] = []
_QUEUE_LOCK = Lock()
_queue_counter = 0


def _queue_sort_key(order: dict) -> tuple:
    """Sort: category priority → item name (groups identical drinks) → time added."""
    cat_pri = _CATEGORY_ORDER.get(order.get("category", ""), 99)
    item = (order.get("item") or "").lower()
    ts = order.get("queued_at", "")
    return (cat_pri, item, ts)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_audit(
    source: str,
    action: str,
    message: str,
    workflow_type: str | None = None,
    payload: dict | None = None,
) -> dict:
    """Append a single audit entry and return it."""
    entry = {
        "timestamp": _now_iso(),
        "source": source,
        "action": action,
        "workflow_type": workflow_type,
        "message": message,
        "payload": payload or {},
    }
    with _AUDIT_LOCK:
        _AUDIT_LOG.append(entry)
    return entry


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


# ---- Page ----------------------------------------------------------------


@app.route("/")
def index() -> str:
    return render_template("index.html")


# ---- Helpers -------------------------------------------------------------


def _json_body() -> dict:
    """Pull JSON body even when content-type is loose."""
    return request.get_json(silent=True) or {}


def _safe_call(workflow_label: str, fn, *args, **kwargs):
    """Run an orchestrator function and wrap errors as JSON instead of crashing."""
    try:
        result = fn(*args, **kwargs)
        _record_audit(
            source="orchestrator",
            action="workflow_completed",
            workflow_type=workflow_label,
            message=f"{workflow_label} ran (status={result.get('status')})",
        )
        return jsonify(result), 200
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        _record_audit(
            source="orchestrator",
            action="workflow_error",
            workflow_type=workflow_label,
            message=f"{workflow_label} raised {type(exc).__name__}: {exc}",
            payload={"traceback": tb},
        )
        return (
            jsonify({"error": str(exc), "workflow_type": workflow_label, "traceback": tb}),
            500,
        )


# ---- API: Manager Readiness ---------------------------------------------


@app.route("/api/manager_readiness", methods=["POST"])
def api_manager_readiness():
    body = _json_body()
    store_id = body.get("store_id", "SD001")
    date = body.get("date", "2024-01-15")
    hour = int(body.get("hour", 8))
    return _safe_call("manager_readiness", run_manager_readiness, store_id, date, hour)


# ---- API: Barista Recommendation ----------------------------------------


@app.route("/api/barista_recommendation", methods=["POST"])
def api_barista_recommendation():
    body = _json_body()
    store_id = body.get("store_id", "SD001")
    date = body.get("date", "2024-01-15")
    hour = int(body.get("hour", 8))
    customer_request = body.get("customer_request", "")
    preferences = body.get("preferences") or None
    return _safe_call(
        "barista_recommendation",
        run_barista_recommendation,
        store_id,
        date,
        hour,
        customer_request,
        preferences,
    )


# ---- API: Order Builder --------------------------------------------------


@app.route("/api/order_builder", methods=["POST"])
def api_order_builder():
    body = _json_body()
    store_id = body.get("store_id", "SD001")
    date = body.get("date", "2024-01-15")
    raw_order = body.get("raw_order", "")
    return _safe_call("order_builder", run_order_builder, store_id, date, raw_order)


# ---- API: Full Workflow --------------------------------------------------


@app.route("/api/full_workflow", methods=["POST"])
def api_full_workflow():
    body = _json_body()
    store_id = body.get("store_id", "SD001")
    date = body.get("date", "2024-01-15")
    hour = int(body.get("hour", 8))
    customer_request = body.get("customer_request", "")
    raw_order = body.get("raw_order") or None
    preferences = body.get("preferences") or None
    return _safe_call(
        "full_workflow",
        run_full_workflow,
        store_id,
        date,
        hour,
        customer_request,
        raw_order,
        preferences,
    )


# ---- API: Review actions (UI state + audit only) ------------------------


_ALLOWED_ACTIONS = {"approve", "edit", "reject_rerun", "escalate", "ask_follow_up", "rerun"}


@app.route("/api/review_action", methods=["POST"])
def api_review_action():
    body = _json_body()
    action = str(body.get("action", "")).strip()
    if action not in _ALLOWED_ACTIONS:
        return (
            jsonify({"error": f"Unknown review action: {action!r}", "allowed": sorted(_ALLOWED_ACTIONS)}),
            400,
        )
    workflow_type = body.get("workflow_type")
    target = body.get("target")
    notes = body.get("notes", "")
    entry = _record_audit(
        source="user_review",
        action=action,
        workflow_type=workflow_type,
        message=f"User {action} on {target or workflow_type or 'workflow'}" + (f": {notes}" if notes else ""),
        payload={"target": target, "notes": notes},
    )
    return jsonify({"status": "recorded", "entry": entry}), 200


# ---- API: Audit Log ------------------------------------------------------


@app.route("/api/audit_log", methods=["GET"])
def api_audit_log():
    with _AUDIT_LOCK:
        return jsonify({"audit_log": list(_AUDIT_LOG)}), 200


@app.route("/api/audit_log", methods=["DELETE"])
def api_audit_log_clear():
    with _AUDIT_LOCK:
        _AUDIT_LOG.clear()
    return jsonify({"status": "cleared"}), 200


# ---- API: Order Queue ----------------------------------------------------


@app.route("/api/queue", methods=["GET"])
def api_queue_get():
    with _QUEUE_LOCK:
        sorted_q = sorted(_ORDER_QUEUE, key=_queue_sort_key)
        return jsonify({"queue": sorted_q, "count": len(sorted_q)}), 200


@app.route("/api/queue/add", methods=["POST"])
def api_queue_add():
    global _queue_counter
    body = _json_body()
    item = str(body.get("item") or "").strip()
    if not item:
        return jsonify({"error": "item is required"}), 400
    with _QUEUE_LOCK:
        _queue_counter += 1
        entry = {
            "id": _queue_counter,
            "item": item,
            "category": body.get("category") or "",
            "subcategory": body.get("subcategory") or "",
            "size": body.get("size") or "",
            "milk_type": body.get("milk_type") or "",
            "temperature": body.get("temperature") or "",
            "syrups": body.get("syrups") or [],
            "customizations": body.get("customizations") or [],
            "notes": body.get("notes") or "",
            "workflow_type": body.get("workflow_type") or "",
            "queued_at": _now_iso(),
        }
        _ORDER_QUEUE.append(entry)
    _record_audit(
        source="order_queue",
        action="queued",
        workflow_type=entry["workflow_type"],
        message=f"Queued: {item}",
        payload=entry,
    )
    return jsonify({"status": "queued", "entry": entry}), 200


@app.route("/api/queue/<int:order_id>/done", methods=["DELETE"])
def api_queue_done(order_id: int):
    with _QUEUE_LOCK:
        found = next((o for o in _ORDER_QUEUE if o["id"] == order_id), None)
        if not found:
            return jsonify({"error": f"Order #{order_id} not found"}), 404
        _ORDER_QUEUE[:] = [o for o in _ORDER_QUEUE if o["id"] != order_id]
    _record_audit(
        source="order_queue",
        action="dequeued",
        message=f"Done: #{order_id} {found.get('item', '')}",
        payload=found,
    )
    return jsonify({"status": "done", "removed": found}), 200


@app.route("/api/queue", methods=["DELETE"])
def api_queue_clear():
    with _QUEUE_LOCK:
        _ORDER_QUEUE.clear()
    _record_audit(source="order_queue", action="cleared", message="Order queue cleared")
    return jsonify({"status": "cleared"}), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":  # pragma: no cover
    # Bind to localhost only; debug is fine for the prototype.
    app.run(host="127.0.0.1", port=5000, debug=True)
