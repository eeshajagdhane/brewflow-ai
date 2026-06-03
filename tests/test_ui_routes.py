"""BrewFlow AI — UI route tests.

Live tests against the Flask app in `ui/app.py`.  Every route is exercised
through Flask's `test_client()` and the orchestrator is invoked for real —
there is no mocking, no canned data, and no external API.

These tests confirm the UI is correctly wired to the existing backend.
"""

from __future__ import annotations

import json

import pytest

from ui.app import app, _AUDIT_LOG  # noqa: WPS437  (private OK in tests)


STORE = "SD001"
DATE = "2024-01-15"
HOUR = 8


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# App imports + index page
# ---------------------------------------------------------------------------


def test_app_imports_successfully():
    """The Flask app object must exist and have the expected routes."""
    rules = {r.rule for r in app.url_map.iter_rules()}
    expected = {
        "/",
        "/api/manager_readiness",
        "/api/barista_recommendation",
        "/api/order_builder",
        "/api/full_workflow",
        "/api/review_action",
        "/api/audit_log",
    }
    assert expected <= rules, f"missing routes: {expected - rules}"


def test_index_page_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # Sanity: the page contains the title, the tab nav, and the simulated-data note.
    # "Daily Dashboard" is the main tab label; "Full Workflow" still appears inside
    # the collapsible Connected Workflow Demo section and the run button.
    assert "BrewFlow AI" in body
    assert "Operations Console" in body
    assert "Daily Dashboard" in body, "Daily Dashboard tab must be present"
    assert "Full Workflow" in body, "Full Workflow demo section must still be present"
    assert "Simulated Starbucks branch prototype" in body, (
        "simulated-data disclaimer must be visible on the page"
    )
    # Final Order Builder removed from sidebar nav but the view and API remain
    assert "view-order" in body, "Order builder view must still exist in DOM for Barista View"
    assert "Final Order Builder" in body, "Final Order Builder heading still in DOM"


# ---------------------------------------------------------------------------
# /api/manager_readiness
# ---------------------------------------------------------------------------


def test_api_manager_readiness_returns_workflow_shape(client):
    r = client.post(
        "/api/manager_readiness",
        json={"store_id": STORE, "date": DATE, "hour": HOUR},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()
    assert data["workflow_type"] == "manager_readiness"
    assert "final_output" in data
    assert "evidence_package" in data
    assert "review_queue" in data
    assert "audit_log" in data
    assert "face_validity" in data
    # face_validity shape
    fv = data["face_validity"]
    for k in ("status", "confidence", "evidence_quality", "anchors_used", "recommended_action"):
        assert k in fv


def test_api_manager_readiness_uses_defaults(client):
    """Even with no body, defaults kick in and the call succeeds."""
    r = client.post("/api/manager_readiness", json={})
    assert r.status_code == 200
    assert r.get_json()["workflow_type"] == "manager_readiness"


# ---------------------------------------------------------------------------
# /api/barista_recommendation
# ---------------------------------------------------------------------------


def test_api_barista_recommendation_returns_candidates(client):
    r = client.post(
        "/api/barista_recommendation",
        json={
            "store_id": STORE,
            "date": DATE,
            "hour": HOUR,
            "customer_request": "I want something iced, sweet, dairy-free, and medium caffeine.",
            "preferences": {"milk_preference": "dairy-free"},
        },
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()
    assert data["workflow_type"] == "barista_recommendation"
    fo = data["final_output"]
    assert "top_candidates" in fo
    assert isinstance(fo["top_candidates"], list)
    assert "face_validity" in data
    # Review is always required on customer-facing recommendation
    assert data["review_required"] is True


def test_api_barista_recommendation_allergy_escalates(client):
    r = client.post(
        "/api/barista_recommendation",
        json={
            "store_id": STORE,
            "date": DATE,
            "hour": HOUR,
            "customer_request": "I have a nut allergy and want something dairy-free.",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    fv = data["face_validity"]
    assert fv["status"] == "needs_review"
    assert fv["recommended_action"] == "escalate"


# ---------------------------------------------------------------------------
# /api/order_builder
# ---------------------------------------------------------------------------


def test_api_order_builder_returns_structured_order(client):
    r = client.post(
        "/api/order_builder",
        json={
            "store_id": STORE,
            "date": DATE,
            "raw_order": "grande iced matcha with oat milk, light ice, and vanilla",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["workflow_type"] == "order_builder"
    so = data["final_output"]["structured_order"]
    assert so["size"] == "Grande"
    assert so["temperature"] == "Iced"
    assert so["milk_type"] == "Oat Milk"


def test_api_order_builder_missing_size_followup(client):
    r = client.post(
        "/api/order_builder",
        json={"store_id": STORE, "date": DATE, "raw_order": "iced latte with oat milk"},
    )
    assert r.status_code == 200
    data = r.get_json()
    fo = data["final_output"]
    assert "size" in fo["missing_fields"]
    assert fo["follow_up_question"]


# ---------------------------------------------------------------------------
# /api/full_workflow
# ---------------------------------------------------------------------------


def test_api_full_workflow_runs_all_phases(client):
    r = client.post(
        "/api/full_workflow",
        json={
            "store_id": STORE,
            "date": DATE,
            "hour": HOUR,
            "customer_request": "iced sweet dairy-free medium caffeine",
            "raw_order": "grande iced chai with almond milk",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["workflow_type"] == "full_workflow"
    fo = data["final_output"]
    assert "manager_readiness" in fo
    assert "recommendation" in fo
    assert "order" in fo
    assert fo["order"] is not None  # raw_order was provided
    phases = {s.get("phase") for s in data["steps"]}
    assert {"manager_readiness", "barista_recommendation", "order_builder"} <= phases


def test_api_full_workflow_no_raw_order_skips_order(client):
    r = client.post(
        "/api/full_workflow",
        json={
            "store_id": STORE,
            "date": DATE,
            "hour": HOUR,
            "customer_request": "what do you recommend",
        },
    )
    assert r.status_code == 200
    fo = r.get_json()["final_output"]
    assert fo["order"] is None


# ---------------------------------------------------------------------------
# /api/review_action
# ---------------------------------------------------------------------------


def test_api_review_action_records_and_returns_entry(client):
    # Clear log first so the test is deterministic
    client.delete("/api/audit_log")

    r = client.post(
        "/api/review_action",
        json={
            "action": "approve",
            "workflow_type": "barista_recommendation",
            "target": "recommendation_candidates",
            "notes": "",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "recorded"
    assert data["entry"]["action"] == "approve"
    assert data["entry"]["source"] == "user_review"


def test_api_review_action_rejects_unknown_action(client):
    r = client.post("/api/review_action", json={"action": "deleteEverything"})
    assert r.status_code == 400
    body = r.get_json()
    assert "error" in body
    assert "allowed" in body


# ---------------------------------------------------------------------------
# /api/audit_log
# ---------------------------------------------------------------------------


def test_api_audit_log_accumulates_entries(client):
    client.delete("/api/audit_log")
    # A workflow run should add an entry
    client.post("/api/manager_readiness", json={"store_id": STORE, "date": DATE, "hour": HOUR})
    # A review action should add another
    client.post(
        "/api/review_action",
        json={"action": "approve", "workflow_type": "manager_readiness", "target": "summary"},
    )
    r = client.get("/api/audit_log")
    assert r.status_code == 200
    log = r.get_json()["audit_log"]
    assert len(log) >= 2
    sources = {e["source"] for e in log}
    assert "orchestrator" in sources
    assert "user_review" in sources


def test_api_audit_log_clear(client):
    client.post("/api/review_action", json={"action": "approve", "target": "x"})
    client.delete("/api/audit_log")
    r = client.get("/api/audit_log")
    assert r.get_json()["audit_log"] == []
