# GitHub Issue Triage to Linear

A FastAPI integration reference that turns new GitHub issues into typed classification and Linear handoffs.

**[Portfolio](https://github.com/Reactance0083)** · **Status: implementation reference; live integration not revalidated in this refresh**

## Implemented flow

1. Receive `POST /github/webhook` and verify the HMAC signature.
2. Select newly opened issues.
3. Classify the issue using a PydanticAI agent.
4. Create a Linear issue in the configured team when the model requests it.
5. Attempt a GitHub comment with the Linear link.

The model returns title, priority, label, team area, estimate, summary, and a create/skip decision. **The team is configured with `LINEAR_TEAM_ID`; the predicted area and label are written into the description rather than applied as team routing or Linear labels.**

## Setup

```bash
python -m venv .venv
# Activate the environment for your shell.
python -m pip install -r requirements.txt
# Copy .env.example to .env and configure the variables below.
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

The application is in `main.py`. Configure `GITHUB_WEBHOOK_SECRET`, `LINEAR_API_KEY`, `LINEAR_TEAM_ID`, and `ANTHROPIC_API_KEY`. Posting comments additionally requires a suitable `GITHUB_TOKEN`.

Use a test GitHub repository and Linear team for live verification. Receiving an eligible event can create an issue and comment.

## What to inspect

- `TriageDecision`: structured model output.
- `verify_github_signature`: signed-event validation.
- `process_issue`: model decision and handoff.
- `create_linear_ticket`: GraphQL integration and source traceability.

## Limits

The source has no durable queue, event deduplication, reviewer approval step, or independently validated classification accuracy. Current provider compatibility needs verification; the PydanticAI calls use `result_type` and `result.data`.

GraphQL application-level errors, missing returned issue URLs, GitHub comment responses, and prompt-injection handling need hardening before production use. A model's duplicate/spam assessment is not a deterministic duplicate detector.

Developed with AI assistance. Documentation reviewed against source on November 10, 2026.
