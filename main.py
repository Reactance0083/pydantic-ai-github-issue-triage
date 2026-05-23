"""
GitHub Issue → LLM Triage → Linear Scaffold
Receives GitHub webhook events, classifies each issue with pydantic-ai,
and automatically creates Linear tickets with priority, team assignment, and labels.

Setup: expose with ngrok (dev) or any server, paste URL into GitHub repo
Settings → Webhooks. Select "Issues" events.
"""
import hashlib, hmac, os
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pydantic_ai import Agent
from dotenv import load_dotenv
import httpx

load_dotenv()

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
LINEAR_API_KEY        = os.getenv("LINEAR_API_KEY", "")
LINEAR_TEAM_ID        = os.getenv("LINEAR_TEAM_ID", "")

_missing = [k for k, v in {
    "GITHUB_WEBHOOK_SECRET": GITHUB_WEBHOOK_SECRET,
    "LINEAR_API_KEY": LINEAR_API_KEY,
    "LINEAR_TEAM_ID": LINEAR_TEAM_ID,
}.items() if not v]
if _missing:
    raise RuntimeError(f"Missing env vars: {', '.join(_missing)}")


# ── Pydantic output model ─────────────────────────────────────────────────────
class TriageDecision(BaseModel):
    should_create_ticket: bool  # False = skip (duplicates, spam, questions)
    title: str                  # clean 5-10 word ticket title
    priority: int               # 1=urgent 2=high 3=medium 4=low
    label: str                  # bug | feature | improvement | docs | question
    team_area: str              # frontend | backend | infra | data | mobile | unknown
    estimate: int               # story points: 1 2 3 5 8 13
    summary: str                # 2-3 sentence description for the Linear ticket


# ── pydantic-ai classifier ────────────────────────────────────────────────────
classifier = Agent(
    "anthropic:claude-haiku-4-5",
    result_type=TriageDecision,
    system_prompt=(
        "You are a senior engineering manager triaging GitHub issues into Linear tickets. "
        "Assign priority 1 (urgent) only for production outages or data loss. "
        "Assign priority 2 (high) for bugs affecting many users or blocking releases. "
        "Assign priority 3 (medium) for feature requests with clear business value. "
        "Assign priority 4 (low) for minor improvements, typos, and nice-to-haves. "
        "Skip: duplicate issues, questions that belong in discussions, vague issues missing reproduction steps. "
        "Estimate story points honestly — 1=trivial fix, 13=multi-week effort. "
        "Write the summary as if briefing an engineer picking up the ticket cold."
    ),
)


# ── Linear helper ─────────────────────────────────────────────────────────────
PRIORITY_LABELS = {1: "urgent", 2: "high", 3: "medium", 4: "low"}

async def create_linear_ticket(
    decision: TriageDecision, issue_url: str, issue_number: int
) -> str:
    """Creates a Linear issue via GraphQL API and returns the issue URL."""
    mutation = """
    mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                id
                url
                identifier
            }
        }
    }
    """
    variables = {
        "input": {
            "teamId": LINEAR_TEAM_ID,
            "title": decision.title,
            "description": (
                f"{decision.summary}\n\n"
                f"**GitHub Issue:** {issue_url}\n"
                f"**Area:** {decision.team_area} | "
                f"**Estimate:** {decision.estimate} pts | "
                f"**Label:** {decision.label}"
            ),
            "priority": decision.priority,
            "estimate": decision.estimate,
        }
    }

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://api.linear.app/graphql",
            json={"query": mutation, "variables": variables},
            headers={
                "Authorization": LINEAR_API_KEY,
                "Content-Type": "application/json",
            },
        )
        r.raise_for_status()
        data = r.json()
        issue = data.get("data", {}).get("issueCreate", {}).get("issue", {})
        return issue.get("url", "")


# ── GitHub signature verification ─────────────────────────────────────────────
def verify_github_signature(body: bytes, signature: str) -> bool:
    if not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="GitHub Issue Triage → Linear", version="1.0.0")


@app.post("/github/webhook")
async def github_webhook(request: Request, background: BackgroundTasks):
    body      = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event     = request.headers.get("X-GitHub-Event", "")

    if not verify_github_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid GitHub signature")

    if event != "issues":
        return {"ok": True, "skipped": f"event={event}"}

    payload = await request.json()
    action  = payload.get("action", "")

    # Only triage newly opened issues
    if action == "opened":
        background.add_task(process_issue, payload["issue"])

    return {"ok": True}


async def process_issue(issue: dict):
    title  = issue.get("title", "").strip()
    body   = issue.get("body", "").strip() or "(no description)"
    url    = issue.get("html_url", "")
    number = issue.get("number", 0)
    labels = [lbl["name"] for lbl in issue.get("labels", [])]

    prompt = (
        f"GitHub Issue #{number}: {title}\n\n"
        f"Labels: {', '.join(labels) or 'none'}\n\n"
        f"Description:\n{body[:2000]}"  # cap at 2k chars
    )

    result   = await classifier.run(prompt)
    decision = result.data

    if not decision.should_create_ticket:
        return

    linear_url = await create_linear_ticket(decision, url, number)

    # Comment on the GitHub issue so the team knows it's triaged
    repo_api_url = issue.get("repository_url", "")
    if repo_api_url:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{repo_api_url}/issues/{number}/comments",
                json={
                    "body": (
                        f"🤖 **Auto-triaged to Linear**\n\n"
                        f"- **Priority:** {PRIORITY_LABELS.get(decision.priority, 'medium')}\n"
                        f"- **Area:** {decision.team_area}\n"
                        f"- **Estimate:** {decision.estimate} pts\n"
                        f"- **Linear ticket:** {linear_url}"
                    )
                },
                headers={
                    "Authorization": f"token {os.getenv('GITHUB_TOKEN', '')}",
                    "Accept": "application/vnd.github+json",
                },
            )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
