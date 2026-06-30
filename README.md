> **Commercial status:** Deferred code reference. This repository is not the current flagship and should not be promoted as commercially ready until its package, listing, README, and download flow are re-verified.


## Current Status

This repository is a deferred code reference, not the current Stage 1 flagship. It may be useful for learning, but it should not be promoted as commercially ready until its package, listing, README, and download flow are re-verified.

# GitHub Issue → LLM Triage → Linear (pydantic-ai + FastAPI)

Automatically triages GitHub issues into Linear tickets. Uses `pydantic-ai` to classify each issue, assign priority, estimate story points, and route to the correct team — all without human intervention.

## What It Does

1. Receives GitHub Issues webhook events
2. Verifies HMAC-SHA256 signature
3. Classifies the issue with `claude-haiku-4-5` via pydantic-ai
4. If worth creating → creates a Linear ticket with priority, estimate, and area tag
5. Comments on the GitHub issue with a link to the Linear ticket

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your credentials
uvicorn main:app --reload --port 8001
```

Expose with ngrok, then configure in GitHub:
```
Repo → Settings → Webhooks → Add webhook
  Payload URL: https://YOUR_NGROK_URL/github/webhook
  Content type: application/json
  Secret: (set this as GITHUB_WEBHOOK_SECRET in .env)
  Events: Issues only
```

## Structured Output (pydantic-ai)

```python
class TriageDecision(BaseModel):
    should_create_ticket: bool
    title: str           # clean 5-10 word ticket title
    priority: int        # 1=urgent 2=high 3=medium 4=low
    label: str           # bug | feature | improvement | docs | question
    team_area: str       # frontend | backend | infra | data | mobile
    estimate: int        # story points: 1 2 3 5 8 13
    summary: str         # 2-3 sentence description for the Linear ticket
```

## Priority Mapping

| Linear Priority | When |
|----------------|------|
| 1 — Urgent | Production outage, data loss |
| 2 — High | Bug affecting many users, release blocker |
| 3 — Medium | Feature request with clear value |
| 4 — Low | Minor improvement, typo, nice-to-have |

## What Gets Skipped

- Duplicates (LLM detects similar existing issues)
- Vague bug reports missing reproduction steps
- Questions that belong in GitHub Discussions
- Spam / test issues

## Architecture

```
GitHub → POST /github/webhook → verify signature
          → triage (pydantic-ai, async background task)
          → create_linear_ticket() via GraphQL
          → comment on GitHub issue with Linear URL
```

## Customization

- Add `GITHUB_TOKEN` to `.env` to enable the auto-comment feature
- Extend `TriageDecision` with `assignee_id` to auto-assign Linear tickets
- Add `label_ids` mapping in `create_linear_ticket()` to set Linear labels

## Requirements

- Python 3.11+
- GitHub repo with webhook permissions
- Linear workspace with API access
- Anthropic API key (uses claude-haiku-4-5, ~$0.001/100 issues)

---

## Get the Complete Bundle

All 5 templates are available individually or as a **$39 bundle** (saves $15 vs individual).

| Template | Price | Link |
|----------|-------|------|
| Slack → Notion Automation | $9 | [Buy on Gumroad](https://reactance0083.gumroad.com/l/cdonwt) |
| GitHub Issue → Linear Triage | $9 | [Buy on Gumroad](https://reactance0083.gumroad.com/l/axgwj) |
| Multi-LLM Cost Optimizer | $29 only for the verified Multi-LLM flagship | [Buy on Gumroad](https://reactance0083.gumroad.com/l/ztmlv) |
| Web Scraper + Semantic Search | $9 | [Buy on Gumroad](https://reactance0083.gumroad.com/l/esjukw) |
| Prompt Engineering Runbook | $15 | [Buy on Gumroad](https://reactance0083.gumroad.com/l/mdsbpc) |
| **Complete Bundle (all 5)** | **$39** | [Buy on Gumroad](https://reactance0083.gumroad.com/l/pydantic-ai-fastapi-bundle) |

Buying includes: all source files, README, requirements.txt, .env.example, and lifetime updates.

> **Free to use** — the source is here on GitHub. Buying supports continued development and gets you a clean download with everything packaged.

---

*Built by [Wade Allen](https://github.com/Reactance0083) — AI Workflow Architect*
