"""DeepEval AI-performance tests for the M04 workflow.

This is a *starter* — it shows the shape of one case and the four
required checks (faithfulness, answer relevancy, quality rule, face
validity) so you can run `uv run pytest -m integration
tests/test_workflow.py` and see results. Replace the placeholder case
with 8-12 real cases drawn from your workflow, and tailor the
``QualityRule`` and ``FaceValidity`` criteria to your business context.
See `tests/README.md` for the full pattern.

The suite is marked ``integration`` because it makes real LLM calls
(both for the workflow under test and for DeepEval's judge model), so it
is skipped by default. Run explicitly:

    uv run pytest -m integration tests/test_workflow.py

Results land in ``tests/results/``; summarize them in ``test_report.md``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Replace this with 8-12 real cases. At least 2 should be tied to a
# failure you listed in failure_cases.md.
# ---------------------------------------------------------------------------
TEST_CASES: list[dict] = [
    {
        "id": "example-01",
        "input": "Can a manager override the standard 30-day refund window for a long-time customer?",
        "expected_behavior": (
            "The AI cites the refund policy, notes the manager-override clause, and recommends a next step."
        ),
        "retrieval_context": [
            # Fill with the actual passages your RAG retriever returned, or
            # load them via rag.retrieval.retrieve(...) at runtime.
            "Refund policy: standard window is 30 days. Manager override "
            "permitted for accounts with 12+ months of active history.",
        ],
        # Optional: tag the case with which failure_cases.md row it covers.
        "covers_failure": None,
    },
]


def run_workflow(case_input: str) -> str:
    """Call *your* workflow / orchestrator with the user input.

    Replace this stub with a real call into ``scripts.orchestrator`` or
    whichever entry point your UI uses. The returned string is what
    DeepEval will score.
    """

    raise NotImplementedError("Wire run_workflow() to your actual orchestrator / skill chain.")


@pytest.mark.integration
@pytest.mark.parametrize("case", TEST_CASES, ids=[c["id"] for c in TEST_CASES])
def test_workflow_case(case: dict) -> None:
    """Run one case end-to-end and score it with DeepEval."""

    # Imported inside the test so the suite still *collects* when deepeval
    # isn't installed yet (e.g., on a fresh clone before `uv sync`).
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    actual_output = run_workflow(case["input"])

    test_case = LLMTestCase(
        input=case["input"],
        actual_output=actual_output,
        retrieval_context=case["retrieval_context"],
    )

    # Check 1 of 4: did the AI stay grounded in the evidence?
    faithfulness = FaithfulnessMetric(threshold=0.7)

    # Check 2 of 4: did the AI answer the question that was asked,
    # rather than drifting to a related but less useful topic?
    answer_relevancy = AnswerRelevancyMetric(threshold=0.7)

    # Check 3 of 4: project-specific quality rule. Replace the criteria
    # string with your own plain-English rule (e.g. "cites the relevant
    # policy, names the customer, and ends with a clear next step").
    quality_rule = GEval(
        name="QualityRule",
        criteria=(
            "The answer cites the relevant source material, addresses the "
            "user's specific situation, and ends with a clear next step."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.7,
    )

    # Check 4 of 4: face validity. Would a person who understands the
    # business context find this answer, recommendation, ranking, or
    # forecast reasonable enough to investigate further? Tailor the
    # criteria to the role you are simulating (support manager, loan
    # officer, recruiter, analyst, etc.).
    face_validity = GEval(
        name="FaceValidity",
        criteria=(
            "The result would seem reasonable to an experienced practitioner "
            "in the business context being studied: the direction of the "
            "answer makes sense, the magnitude is plausible, and the "
            "recommendation respects practical constraints such as "
            "approvals, compliance, staffing, or customer expectations. "
            "If the result is surprising, the reasoning explains why it is "
            "still plausible."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.7,
    )

    metrics = [faithfulness, answer_relevancy, quality_rule, face_validity]
    _record_result(case, actual_output, metrics)

    assert_test(test_case, metrics)


def _record_result(case: dict, output: str, metrics: list) -> None:
    """Append a row to tests/results/<timestamp>.jsonl for the report."""

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = RESULTS_DIR / f"{stamp}.jsonl"
    row = {
        "case_id": case["id"],
        "input": case["input"],
        "output": output,
        "metrics": [
            {
                "name": m.__class__.__name__,
                "score": getattr(m, "score", None),
                "passed": getattr(m, "success", None),
                "reason": getattr(m, "reason", None),
            }
            for m in metrics
        ],
        "covers_failure": case.get("covers_failure"),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
