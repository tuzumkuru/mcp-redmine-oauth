"""Unit tests for MCP prompts — test that prompts produce well-structured output."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_redmine_oauth.client import RedmineClient
from mcp_redmine_oauth.prompts import register_prompts


@pytest.fixture()
def mock_redmine():
    return AsyncMock(spec=RedmineClient)


@pytest.fixture()
def prompt_fns(mock_redmine):
    """Register prompts and extract the inner functions."""
    mcp = MagicMock()
    captured = {}

    def capture_prompt():
        def decorator(fn):
            captured[fn.__name__] = fn
            return fn
        return decorator

    mcp.prompt = capture_prompt
    register_prompts(mcp, mock_redmine)
    return captured, mock_redmine


def _auth_patches(mock_token):
    """Context manager that patches get_access_token in both scopes and prompts modules."""
    return (
        patch("mcp_redmine_oauth.scopes.get_access_token", return_value=mock_token),
        patch("mcp_redmine_oauth.prompts.get_access_token", return_value=mock_token),
    )


@pytest.mark.asyncio
async def test_summarize_ticket_basic(prompt_fns):
    fns, mock_redmine = prompt_fns
    mock_redmine.get.return_value = {
        "issue": {
            "id": 42,
            "subject": "Login page broken",
            "status": {"name": "In Progress"},
            "priority": {"name": "High"},
            "assigned_to": {"name": "Alice"},
            "description": "Users can't log in since the last deploy.",
            "journals": [
                {
                    "user": {"name": "Bob"},
                    "created_on": "2025-06-15",
                    "notes": "I can reproduce this on Chrome.",
                },
                {
                    "user": {"name": "Alice"},
                    "created_on": "2025-06-16",
                    "notes": "Found the root cause — bad redirect.",
                },
            ],
        }
    }

    mock_token = MagicMock()
    mock_token.token = "test-token"
    mock_token.scopes = ["view_issues"]

    p1, p2 = _auth_patches(mock_token)
    with p1, p2:
        result = await fns["summarize_ticket"](issue_id=42)

    assert "Issue #42" in result
    assert "Login page broken" in result
    assert "In Progress" in result
    assert "Alice" in result
    assert "Bob: I can reproduce this" in result
    assert "one-paragraph summary" in result


@pytest.mark.asyncio
async def test_summarize_ticket_no_journals(prompt_fns):
    fns, mock_redmine = prompt_fns
    mock_redmine.get.return_value = {
        "issue": {
            "id": 10,
            "subject": "Quiet issue",
            "status": {"name": "New"},
            "priority": {"name": "Normal"},
            "description": "",
            "journals": [],
        }
    }

    mock_token = MagicMock()
    mock_token.token = "test-token"
    mock_token.scopes = ["view_issues"]

    p1, p2 = _auth_patches(mock_token)
    with p1, p2:
        result = await fns["summarize_ticket"](issue_id=10)

    assert "(no description)" in result
    assert "(no comments)" in result


@pytest.mark.asyncio
async def test_draft_bug_report_basic(prompt_fns):
    fns, mock_redmine = prompt_fns
    mock_redmine.get.return_value = {
        "project": {
            "id": 1,
            "name": "Alpha",
            "identifier": "alpha",
            "trackers": [
                {"id": 1, "name": "Bug"},
                {"id": 2, "name": "Feature"},
            ],
            "issue_categories": [
                {"id": 10, "name": "Backend"},
            ],
        }
    }

    mock_token = MagicMock()
    mock_token.token = "test-token"
    mock_token.scopes = ["view_project"]

    p1, p2 = _auth_patches(mock_token)
    with p1, p2:
        result = await fns["draft_bug_report"](
            project_id="alpha",
            rough_notes="Login page returns 500 after clicking submit",
        )

    assert "Alpha" in result
    assert "Bug (id=1)" in result
    assert "Feature (id=2)" in result
    assert "Backend (id=10)" in result
    assert "Login page returns 500" in result
    assert "Steps to reproduce" in result
    assert "create_issue" in result


@pytest.mark.asyncio
async def test_draft_bug_report_no_categories(prompt_fns):
    fns, mock_redmine = prompt_fns
    mock_redmine.get.return_value = {
        "project": {
            "id": 1,
            "name": "Simple",
            "identifier": "simple",
            "trackers": [{"id": 1, "name": "Bug"}],
            "issue_categories": [],
        }
    }

    mock_token = MagicMock()
    mock_token.token = "test-token"
    mock_token.scopes = ["view_project"]

    p1, p2 = _auth_patches(mock_token)
    with p1, p2:
        result = await fns["draft_bug_report"](
            project_id="simple",
            rough_notes="Something broke",
        )

    assert "categories:** N/A" in result
