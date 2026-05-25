"""
GitHub Issue -> Linear Triage  |  pydantic-ai + FastAPI
Receives GitHub webhook events, classifies each issue with pydantic-ai,
and automatically creates prioritised Linear tickets with team assignment.

Full working source: https://reactance0083.gumroad.com/l/axgwj
"""
# ── Preview scaffold (non-functional) ────────────────────────────────────────
from fastapi import FastAPI, Request
from pydantic import BaseModel
from pydantic_ai import Agent
import httpx

app = FastAPI(title="GitHub -> Linear Triage")

class TriageResult(BaseModel):
    priority: str          # urgent | high | medium | low
    team: str              # backend | frontend | infra | product
    labels: list[str]
    linear_title: str
    linear_description: str

# The full version includes:
#   - GitHub webhook HMAC-SHA256 signature verification
#   - pydantic-ai agent with structured TriageResult output
#   - Linear GraphQL mutations to create issues with priority + team
#   - Duplicate detection to skip already-triaged issues
#   - .env-driven config for GITHUB_WEBHOOK_SECRET, LINEAR_API_KEY, LINEAR_TEAM_ID

@app.post("/webhook/github")
async def handle_github_webhook(request: Request):
    raise NotImplementedError("Full source at https://reactance0083.gumroad.com/l/axgwj")

@app.get("/health")
async def health():
    return {"status": "ok"}
