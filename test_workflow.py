"""Offline regression checks. No tickets or provider requests are sent."""
import asyncio
import hashlib
import hmac
import json
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

with patch.dict(os.environ, {key: "offline-test" for key in (
    "ANTHROPIC_API_KEY", "GITHUB_WEBHOOK_SECRET", "LINEAR_API_KEY", "LINEAR_TEAM_ID",
)}):
    import main


class WorkflowTests(unittest.TestCase):
    def test_signature_boundary(self):
        body = b'{"action":"closed"}'
        signature = "sha256=" + hmac.new(main.GITHUB_WEBHOOK_SECRET.encode(), body,
                                         hashlib.sha256).hexdigest()
        client = TestClient(main.app)
        self.assertEqual(client.post("/github/webhook", content=body, headers={
            "X-Hub-Signature-256": signature, "X-GitHub-Event": "issues",
        }).status_code, 200)
        self.assertEqual(client.post("/github/webhook", content=body).status_code, 403)
        self.assertFalse(main.verify_github_signature(body + b" ", signature))

    def test_typed_handoff_empty_body_and_skip(self):
        calls = []
        def handle(request):
            calls.append(request)
            if request.url.host == "api.linear.app":
                return httpx.Response(200, json={"data": {"issueCreate": {
                    "success": True, "issue": {"url": "https://linear.test/issue"},
                }}})
            return httpx.Response(201, json={})
        original_client = httpx.AsyncClient
        def offline_client(**kwargs):
            return original_client(transport=httpx.MockTransport(handle), trust_env=False, **kwargs)
        output = dict(should_create_ticket=True, title="Investigate failed sign in",
                      priority=2, label="bug", team_area="backend", estimate=3,
                      summary="Sign in fails for affected customers.")
        issue = {"title": "Login failure", "body": None, "number": 1,
                 "html_url": "https://github.test/repo/issues/1", "labels": [],
                 "repository_url": "https://api.github.test/repos/test/test"}
        with patch.object(models, "ALLOW_MODEL_REQUESTS", False), \
             patch.object(main.httpx, "AsyncClient", side_effect=offline_client):
            with main.classifier.override(model=TestModel(custom_output_args=output)):
                asyncio.run(main.process_issue(issue))
            self.assertEqual(len(calls), 2)
            ticket = json.loads(calls[0].content)["variables"]["input"]
            self.assertEqual(ticket["priority"], 2)
            self.assertEqual(ticket["teamId"], "offline-test")
            self.assertIn(b"https://linear.test/issue", calls[1].content)
            calls.clear()
            output["should_create_ticket"] = False
            with main.classifier.override(model=TestModel(custom_output_args=output)):
                asyncio.run(main.process_issue(issue))
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
