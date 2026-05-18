"""Minimal orchestrator stub — replace with your real driver.

What this stub does:

* Defines an empty ``STEP_SCRIPTS`` dict (insertion order = run order).
* Subprocesses each registered step with ``--json``, ``--case-id``,
  ``--workflow-run-id``, ``--step-id``.
* Parses the JSON envelope and reads ``envelope["next_action"]`` to decide
  whether to continue.

What it does **not** do: branching, human-in-the-loop pauses, isolated
``/tmp`` runs, scenario suites, a web UI. Add those when you need them.
See ``scripts/README.md`` and the reference orchestrator in
``customer-ticket-process/scripts/orchestrator.py`` for the full pattern.

Usage::

    uv run python scripts/orchestrator.py --case-id CASE-00042
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Register your skills and automations here. Insertion order is run order.
# Replace with real entries, e.g.:
#
#   STEP_SCRIPTS["classify-case"] = (
#       REPO_ROOT / "automations" / "classify-case" / "scripts" / "classify_case.py"
#   )
STEP_SCRIPTS: dict[str, Path] = {}


def run_step(name: str, script: Path, case_id: str, run_id: str) -> dict:
    """Run one step as a subprocess and return its JSON envelope."""
    cmd = [
        sys.executable,
        str(script),
        "--json",
        "--case-id",
        case_id,
        "--workflow-run-id",
        run_id,
        "--step-id",
        f"{name}-{run_id[:8]}",
        "--data-dir",
        str(REPO_ROOT / "data"),
        "--out-dir",
        str(REPO_ROOT / "data" / "working"),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), check=False)
    stdout = (completed.stdout or "").strip()
    if not stdout:
        return {
            "status": "error",
            "error": {
                "code": "no_output",
                "message": (completed.stderr or "").strip() or "step produced no output",
            },
            "exit_code": completed.returncode,
        }
    try:
        return json.loads(stdout.splitlines()[-1])
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "error": {"code": "invalid_envelope", "message": str(exc)},
            "exit_code": completed.returncode,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case-id",
        default="CASE-00001",
        help="Identifier of the case to run the workflow on.",
    )
    args = parser.parse_args()

    if not STEP_SCRIPTS:
        print(
            "no steps registered yet — edit STEP_SCRIPTS in this file "
            "and add an entry per skill/automation. See scripts/README.md."
        )
        return 0

    run_id = f"wf-{uuid.uuid4().hex[:12]}"
    print(f"workflow_run_id={run_id} case_id={args.case_id}")
    for name, script in STEP_SCRIPTS.items():
        print(f"\n--- step: {name} ---")
        envelope = run_step(name, script, args.case_id, run_id)
        print(json.dumps(envelope, indent=2))
        if envelope.get("status") != "ok":
            print(f"step {name} failed — stopping.")
            return 1
        if envelope.get("next_action") in {"done", "closed", None}:
            print(f"workflow finished after {name}.")
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
