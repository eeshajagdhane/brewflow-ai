# Service Recovery Policy

> **Simulated internal guidance for educational prototyping only.**
> Not an official Starbucks policy document.

## Purpose

Defines the steps to take when a customer is dissatisfied due to an unavailable
ingredient, an incorrect order, an extended wait, or any other service failure.

## Recovery Framework: LAIR

1. **Listen** — Let the customer explain the issue without interrupting.
2. **Apologize** — One genuine, brief apology: "I'm sorry for the inconvenience."
3. **Identify** — Determine the root cause: wrong item, unavailable ingredient, long wait.
4. **Resolve** — Take a concrete corrective action (see below).

Do not over-apologize or be defensive. One apology and immediate action is more effective.

## Scenario: Ingredient Unavailable

Customer requests an item whose ingredient is unavailable.

**Response:**
1. "I'm sorry, we're currently out of [ingredient] today."
2. Offer the most similar available alternative: "Can I suggest [alternative] instead? It has a similar [flavor/texture]."
3. If the customer declines: offer a different item from the same category.
4. Do NOT offer a discount unless the manager has explicitly approved a recovery offer.

## Scenario: Order Prepared Incorrectly

Customer received the wrong item or a customization was missed.

**Response:**
1. "I'm sorry about that — let me fix this right away."
2. Prepare the correct drink immediately (do not attempt to modify the existing drink).
3. Do NOT ask the customer to return the incorrect drink if it is a health/safety issue.
4. Log the incident in the order notes.

## Scenario: Extended Wait Time

Customer has been waiting significantly longer than estimated.

**Response:**
1. Proactively acknowledge: "I see you've been waiting. Your [item] will be ready in approximately [X] minutes."
2. If the wait exceeds 10 minutes: apologize and offer to prioritize their order.
3. Do NOT over-promise on timing — give a realistic estimate.

## Scenario: AI Recommendation Error

The AI recommended an item that was unavailable or incorrect.

**Response:**
1. Apologize for the confusion.
2. Offer to run a fresh recommendation: "Let me check what we have available right now."
3. Flag the issue in the workflow audit_log for review.
4. If the customer is upset, escalate to manager.

## Escalation Triggers

Escalate to manager immediately if:
- Customer expresses a health or safety concern (allergy reaction, food safety issue).
- Customer requests a refund or formal complaint.
- The recovery action chosen is outside standard barista authority.
- The AI workflow flagged human_review_required = True and was not reviewed before order preparation.

## Documentation

Log all service recovery events with:
- Timestamp
- Issue type
- Resolution taken
- Customer outcome (satisfied / escalated)
- Workflow changes recommended (e.g. update barista_guidance.avoid_ingredients)
