"""DeepEval AI-performance tests for the BrewFlow AI Milestone 04 workflow.

This is the *customised* version of the starter file. `run_workflow()`
calls the real BrewFlow orchestrator (`scripts.orchestrator.run_full_workflow`)
and `TEST_CASES` contains 10 realistic scenarios drawn from the workflow
documented in `test_report.md` and `failure_cases.md`.

The suite is marked ``integration`` because DeepEval scoring makes real
LLM calls. It is **skipped by default** so the rest of the local test
suite (95 tests in `test_mcp_tools.py`, `test_rag_retrieval.py`,
`test_brewflow_workflow.py`, `test_face_validity.py`, `test_ui_routes.py`)
can run offline without API keys.

Run this DeepEval suite explicitly when you have `TRITONAI_API_KEY`
configured::

    uv run pytest -m integration tests/test_workflow.py

Per-run results land in ``tests/results/<date>.jsonl``; the human
summary lives in ``test_report.md``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# 10 real BrewFlow AI test cases.
# Each case names the failure it covers (mapped to `failure_cases.md`).
# At least 2 cases are explicitly tied to a row in failure_cases.md.
# ---------------------------------------------------------------------------
TEST_CASES: list[dict] = [
    {
        "id": "TC-01-normal-happy-path",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 8,
        "input": "I want an iced latte, something smooth and lightly sweet.",
        "raw_order": "grande iced vanilla latte with oat milk",
        "preferences": {
            "temperature": "iced", "sweetness": "medium",
            "milk_preference": "oat milk", "caffeine": "medium",
            "coffee_preference": "coffee",
        },
        "expected_behavior": (
            "Workflow runs all three phases. Recommendation returns ranked candidates "
            "with reason codes. Order builder resolves item to an iced espresso drink "
            "with grande size and oat milk. Face validity status is needs_review with "
            "recommended_action 'review' (designed human-approval state)."
        ),
        "retrieval_context": [
            "Barista recommendation guidelines: ask about temperature, sweetness, "
            "and dairy preferences before suggesting a drink.",
            "Drink quality consistency SOP: prepare each drink individually.",
        ],
        "covers_failure": None,
    },
    {
        "id": "TC-02-dairy-free-recommendation",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 8,
        "input": "Iced sweet dairy-free, medium caffeine",
        "raw_order": None,
        "preferences": {"milk_preference": "dairy-free", "temperature": "iced"},
        "expected_behavior": (
            "Order phase skipped. Recommendation candidates all have vegan=True "
            "(dairy-free proxy). Warning surfaces the Vegan=Yes heuristic. "
            "Top candidates include Iced Black Tea, Pink Drink, or similar."
        ),
        "retrieval_context": [
            "Dietary allergen guidance: dairy-free flag uses Vegan=Yes as proxy; "
            "verify specific milk options with the barista before serving.",
        ],
        "covers_failure": "FC-03 wrong dietary restriction match",
    },
    {
        "id": "TC-03-high-caffeine-cold-coffee",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 10,
        "input": "I want something cold, coffee-forward, smooth, and a little sweet.",
        "raw_order": "grande vanilla sweet cream cold brew",
        "preferences": {
            "temperature": "iced", "sweetness": "medium",
            "caffeine": "high", "coffee_preference": "coffee",
        },
        "expected_behavior": (
            "Cold-coffee candidates rank top (Nitro Cold Brew, Cold Brew Coffee). "
            "Reason codes include has_caffeine. Order parses sweet cream as a "
            "customization. Face validity is needs_review/review."
        ),
        "retrieval_context": [
            "Customization policy: sweet cream is a paid add-on and should appear "
            "in the prep notes verbatim.",
        ],
        "covers_failure": None,
    },
    {
        "id": "TC-04-oat-milk-inventory-aware",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 8,
        "input": "I want something iced, espresso-based, sweet, and made with oat milk.",
        "raw_order": "grande iced brown sugar oatmilk shaken espresso",
        "preferences": {
            "temperature": "iced", "sweetness": "sweet",
            "milk_preference": "oat milk", "caffeine": "high",
            "coffee_preference": "coffee",
        },
        "expected_behavior": (
            "Inventory check runs against the current snapshot. If oat milk is "
            "low or critical-low, an inventory warning surfaces and the candidate "
            "is down-ranked. Otherwise the order parses cleanly."
        ),
        "retrieval_context": [
            "Inventory substitution SOP: when a key milk ingredient is low, "
            "offer the next in-stock alternative before confirming the drink.",
        ],
        "covers_failure": "FC-02 stale inventory snapshot",
    },
    {
        "id": "TC-05-allergy-sensitive-escalates",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 8,
        "input": "I have a nut allergy and want something dairy-free.",
        "raw_order": None,
        "preferences": {"milk_preference": "dairy-free"},
        "expected_behavior": (
            "Allergy language is detected. Face validity status is needs_review "
            "and recommended_action is 'escalate' (NOT just 'review'). The "
            "review queue contains a 'recommendation_allergy_review' item. The "
            "warnings list includes an allergy-language entry. The system never "
            "auto-approves any allergen-flagged recommendation."
        ),
        "retrieval_context": [
            "Dietary allergen guidance: do not guarantee allergen-free preparation. "
            "Route the customer to the official Starbucks allergen guide and flag "
            "the order for human review.",
        ],
        "covers_failure": "FC-08 false allergy escalation regression locked in here",
    },
    {
        "id": "TC-06-missing-size-followup",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 8,
        "input": "Something hot for the morning.",
        "raw_order": "iced latte with oat milk",
        "preferences": None,
        "expected_behavior": (
            "Order builder detects missing size. missing_fields contains 'size'. "
            "follow_up_question is populated (e.g. 'What size would you like — "
            "Short, Tall, Grande, or Venti?'). Face validity recommended_action "
            "is 'ask_follow_up'. Review queue contains an order_missing_fields "
            "item with the follow-up question attached."
        ),
        "retrieval_context": [
            "Order confirmation standard: required fields include size, "
            "temperature, and milk type. If any are missing, ask before "
            "submitting the order to the barista station.",
        ],
        "covers_failure": "FC-01 item name and required-field detection",
    },
    {
        "id": "TC-07-unknown-item-fallback",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 8,
        "input": "Surprise me with something refreshing.",
        "raw_order": "large unicorn cloud drink with rainbow foam",
        "preferences": None,
        "expected_behavior": (
            "Item resolution falls back via menu search. item_resolution.candidates "
            "is populated with the closest menu matches. Status downgrades to "
            "warning or needs_review. The barista is shown the candidate list to "
            "pick from rather than the system inventing an item."
        ),
        "retrieval_context": [
            "Item name mapping: when a customer-typed name does not match any "
            "canonical menu item, surface the closest candidates and ask the "
            "barista to confirm before proceeding.",
        ],
        "covers_failure": "FC-01 item name not resolved",
    },
    {
        "id": "TC-08-manager-readiness-rush",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 8,
        "input": "Run the pre-rush manager readiness check.",
        "raw_order": None,
        "preferences": None,
        "expected_behavior": (
            "Manager phase reports demand_level=Very High and rush_risk=high with "
            "forecast_orders around 211. Recommended manager actions include "
            "CRITICAL or ACTION items (e.g. remove unavailable ingredients, "
            "high rush expected). Barista guidance rush_level is 'high'."
        ),
        "retrieval_context": [
            "Manager pre-shift checklist: at high-rush hours, confirm staffing "
            "covers the next two hours and pre-stage popular items.",
            "Rush hour service playbook: keep recommendations concise; prefer "
            "in-stock high-margin candidates.",
        ],
        "covers_failure": None,
    },
    {
        "id": "TC-09-weak-data-out-of-range",
        "store_id": "SD001",
        "date": "1900-01-01",
        "hour": 8,
        "input": "Run readiness for a date outside the simulated data range.",
        "raw_order": None,
        "preferences": None,
        "expected_behavior": (
            "Detect_rush_period returns status=warning. Warnings list is non-empty "
            "(missing forecast, missing history). Face validity quality_score is "
            "downgraded toward the weak end. The system does not invent a demand "
            "level — it transparently flags the missing data."
        ),
        "retrieval_context": [
            "Forecast unavailable for the requested date; default to caution and "
            "ask the manager to verify staffing by hand.",
        ],
        "covers_failure": "FC-04 rush misclassification due to sparse history",
    },
    {
        "id": "TC-10-benign-no-false-escalation",
        "store_id": "SD001",
        "date": "2024-01-15",
        "hour": 8,
        "input": "Something hot and caffeinated.",
        "raw_order": "venti hot latte",
        "preferences": {"temperature": "hot", "caffeine": "high"},
        "expected_behavior": (
            "Benign request with no allergy or medical language. Even though "
            "RAG retrieval may surface 'dietary_allergen_guidance.md' for the "
            "recommendation phase, face validity recommended_action MUST NOT "
            "be 'escalate'. It should be 'review' (the designed customer-facing "
            "approval state). This case is the locked-in regression for the "
            "RAG-leak false-escalation bug found and fixed during development."
        ),
        "retrieval_context": [
            "Recommendation guidelines: hot caffeinated drinks include Caffe "
            "Latte, Cappuccino, Caffe Americano, and Caffe Mocha.",
        ],
        "covers_failure": "FC-08 false allergy escalation from RAG content",
    },
]


def run_workflow(case: dict) -> str:
    """Call the BrewFlow orchestrator with the given case and return the
    final-output JSON as a string.

    The string returned here is what DeepEval will score for faithfulness,
    answer relevancy, the project-specific quality rule, and face
    validity. Because BrewFlow's final_output is structured JSON (not a
    natural-language paragraph), we serialize it to a stable JSON string
    so the DeepEval LLM-judge prompts can reason about every field.
    """
    from scripts.orchestrator import run_full_workflow

    result = run_full_workflow(
        store_id=case["store_id"],
        date=case["date"],
        hour=case["hour"],
        customer_request=case["input"],
        raw_order=case.get("raw_order"),
        preferences=case.get("preferences"),
    )
    # Strip the run_id (changes every call) so DeepEval scores stay
    # comparable across runs.
    final_output = result.get("final_output", {})
    face_validity = result.get("face_validity", {})
    review_queue = [
        {"item": q.get("item"), "reason": q.get("reason")}
        for q in result.get("review_queue", [])
    ]
    warnings = result.get("warnings", [])

    payload = {
        "status": result.get("status"),
        "workflow_type": result.get("workflow_type"),
        "final_output": final_output,
        "face_validity": face_validity,
        "review_queue": review_queue,
        "warnings": warnings,
    }
    return json.dumps(payload, default=str, indent=2)


@pytest.mark.integration
@pytest.mark.parametrize("case", TEST_CASES, ids=[c["id"] for c in TEST_CASES])
def test_workflow_case(case: dict) -> None:
    """Run one BrewFlow case end-to-end and score it with DeepEval.

    The local (offline) verification that the workflow shape is correct
    lives in `tests/test_brewflow_workflow.py`. This file is for the
    *AI-performance* layer that needs an LLM judge.
    """

    # Imported inside the test so the suite still *collects* when deepeval
    # isn't installed yet (e.g., on a fresh clone before `uv sync`).
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    actual_output = run_workflow(case)

    test_case = LLMTestCase(
        input=case["input"],
        actual_output=actual_output,
        retrieval_context=case["retrieval_context"],
    )

    # Check 1 of 4: faithfulness — did the AI stay grounded in the evidence?
    faithfulness = FaithfulnessMetric(threshold=0.7)

    # Check 2 of 4: answer relevancy — did the AI address the actual request
    # rather than drifting to a related but less useful topic?
    answer_relevancy = AnswerRelevancyMetric(threshold=0.7)

    # Check 3 of 4: BrewFlow-specific quality rule — the workflow output
    # should be inventory-aware, dietary-aware, escalate allergy/medical
    # language, ask for missing required fields, and surface evidence the
    # human can audit.
    quality_rule = GEval(
        name="BrewFlowQualityRule",
        criteria=(
            "The workflow output is inventory-aware (mentions or down-ranks "
            "low-stock candidates when relevant), dietary-aware (does not "
            "recommend a drink that contradicts a stated dietary preference), "
            "and escalates allergy or medical language to recommended_action "
            "'escalate'. When required order fields are missing, the output "
            "includes a follow_up_question and routes to 'ask_follow_up'. "
            "The output exposes enough evidence (tool outputs, retrieved RAG "
            "documents, warnings) that a barista or manager could audit the "
            "decision."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        threshold=0.7,
    )

    # Check 4 of 4: face validity — would a barista or manager find this
    # workflow output reasonable enough to act on (with the designed human
    # review checkpoint)? The output should not invent items, hallucinate
    # menu facts, or quietly auto-approve a customer-facing recommendation.
    face_validity = GEval(
        name="BrewFlowFaceValidity",
        criteria=(
            "An experienced coffee-shop barista or manager would find this "
            "workflow output reasonable to act on. Direction and magnitude "
            "make sense (e.g. dairy-free preferences produce vegan-flagged "
            "candidates; rush hours produce 'concise' service mode). The "
            "output respects practical constraints: human approval is "
            "required for customer-facing recommendations, allergen-flagged "
            "requests escalate, drinks are still prepared individually. "
            "If the system flagged something as needs_review, that is part "
            "of the designed process, not a failure."
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
