"""Shared helpers for BrewFlow AI workflow responses.

All MCP tool outputs and orchestrator workflow outputs should be built
through these helpers to guarantee a consistent JSON-serializable structure.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def risk_level_from_status(status: str) -> str:
    """Map a tool/step status string to a risk label."""
    return {
        "success": "low",
        "warning": "medium",
        "needs_review": "high",
        "error": "critical",
    }.get(status, "unknown")


def make_step(
    name: str,
    component_type: str,
    status: str,
    output: Any,
    evidence: Optional[list] = None,
    warnings: Optional[list] = None,
) -> dict:
    """Build a single workflow step record for inclusion in a workflow response."""
    return {
        "step": name,
        "component_type": component_type,  # automation | mcp_tool | rag | skill
        "status": status,
        "risk_level": risk_level_from_status(status),
        "output": output,
        "evidence": evidence or [],
        "warnings": warnings or [],
        "timestamp": now_iso(),
    }


def make_audit_entry(action: str, component: str, status: str, message: str) -> dict:
    """Build a single audit log entry."""
    return {
        "timestamp": now_iso(),
        "action": action,
        "component": component,
        "status": status,
        "message": message,
    }


def make_tool_response(
    status: str,
    data: Optional[Any] = None,
    evidence: Optional[list] = None,
    warnings: Optional[list] = None,
    errors: Optional[list] = None,
    next_actions: Optional[list] = None,
    human_review_required: bool = False,
) -> dict:
    """Build a standard MCP tool / automation response envelope.

    status values: success | warning | needs_review | error
    """
    return {
        "status": status,
        "data": data if data is not None else {},
        "evidence": evidence or [],
        "warnings": warnings or [],
        "errors": errors or [],
        "next_actions": next_actions or [],
        "human_review_required": human_review_required,
    }


def make_workflow_response(
    workflow_type: str,
    status: str,
    steps: list,
    final_output: Any,
    evidence_package: dict,
    review_queue: Optional[list] = None,
    review_required: bool = False,
    review_actions: Optional[list] = None,
    audit_log: Optional[list] = None,
    assumptions: Optional[list] = None,
    warnings: Optional[list] = None,
) -> dict:
    """Build a standard workflow-level response envelope.

    The returned dict is ready to be serialized to JSON and consumed by the UI.
    """
    return {
        "run_id": f"wf-{uuid.uuid4().hex[:12]}",
        "workflow_type": workflow_type,
        "status": status,
        "steps": steps,
        "final_output": final_output,
        "evidence_package": evidence_package,
        "review_queue": review_queue or [],
        "review_required": review_required,
        "review_actions": review_actions or ["approve", "edit", "reject_rerun", "escalate"],
        "audit_log": audit_log or [],
        "assumptions": assumptions or [],
        "warnings": warnings or [],
        "generated_at": now_iso(),
    }
