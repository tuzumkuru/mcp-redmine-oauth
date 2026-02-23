"""Unit tests for MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_redmine_oauth.tools import _format_issue, _format_search_results, MAX_JOURNAL_ENTRIES


# --- search_issues formatting ---


def test_format_search_results_empty():
    data = {"results": [], "total_count": 0, "offset": 0, "limit": 25}
    assert _format_search_results(data) == "No issues found matching the query."


def test_format_search_results_basic():
    data = {
        "results": [
            {
                "id": 1,
                "title": "Bug #42: Login fails",
                "url": "/issues/42",
                "description": "Users cannot log in",
                "datetime": "2025-01-15T10:00:00Z",
            }
        ],
        "total_count": 1,
        "offset": 0,
        "limit": 25,
    }
    result = _format_search_results(data)
    assert "1 result(s)" in result
    assert "Bug #42: Login fails" in result
    assert "2025-01-15" in result
    assert "/issues/42" in result


def test_format_search_results_pagination():
    data = {
        "results": [{"title": f"Issue #{i}", "url": f"/issues/{i}"} for i in range(25)],
        "total_count": 50,
        "offset": 0,
        "limit": 25,
    }
    result = _format_search_results(data)
    assert "50 result(s)" in result
    assert "offset=25" in result


def test_format_search_results_with_offset():
    data = {
        "results": [{"title": "Issue #26", "url": "/issues/26"}],
        "total_count": 50,
        "offset": 25,
        "limit": 25,
    }
    result = _format_search_results(data)
    assert "26–26" in result


def test_format_search_results_truncates_long_descriptions():
    data = {
        "results": [
            {
                "title": "Long issue",
                "url": "/issues/1",
                "description": "x" * 300,
            }
        ],
        "total_count": 1,
        "offset": 0,
        "limit": 25,
    }
    result = _format_search_results(data)
    assert "…" in result
    assert "x" * 201 not in result


# --- journal truncation ---


def test_format_issue_truncates_journals():
    journals = [
        {"user": {"name": f"User {i}"}, "created_on": "2025-01-01", "notes": f"Note {i}"}
        for i in range(40)
    ]
    issue = {
        "id": 1,
        "subject": "Test",
        "journals": journals,
    }
    result = _format_issue(issue)
    assert f"Note {MAX_JOURNAL_ENTRIES - 1}" in result
    assert f"Note {MAX_JOURNAL_ENTRIES}" not in result
    assert "15 more entries (truncated)" in result


def test_format_issue_no_truncation_under_limit():
    journals = [
        {"user": {"name": "Alice"}, "created_on": "2025-01-01", "notes": "Hello"}
        for _ in range(5)
    ]
    issue = {"id": 1, "subject": "Test", "journals": journals}
    result = _format_issue(issue)
    assert "truncated" not in result


# --- format_issue basic ---


def test_format_issue_minimal():
    issue = {"id": 42, "subject": "Test issue"}
    result = _format_issue(issue)
    assert "# Issue #42 — Test issue" in result


def test_format_issue_custom_fields():
    issue = {
        "id": 1,
        "subject": "With fields",
        "custom_fields": [{"name": "Severity", "value": "High"}],
    }
    result = _format_issue(issue)
    assert "**Severity:** High" in result


def test_format_issue_full_fields():
    issue = {
        "id": 10,
        "subject": "Full issue",
        "project": {"name": "Alpha"},
        "tracker": {"name": "Bug"},
        "status": {"name": "In Progress"},
        "priority": {"name": "High"},
        "author": {"name": "Alice"},
        "assigned_to": {"name": "Bob"},
        "created_on": "2025-01-01T00:00:00Z",
        "updated_on": "2025-01-02T00:00:00Z",
    }
    result = _format_issue(issue)
    assert "**Project:** Alpha" in result
    assert "**Tracker:** Bug" in result
    assert "**Status:** In Progress" in result
    assert "**Priority:** High" in result
    assert "**Author:** Alice" in result
    assert "**Assigned to:** Bob" in result


def test_format_issue_description():
    issue = {
        "id": 1,
        "subject": "With desc",
        "description": "This is the bug description.",
    }
    result = _format_issue(issue)
    assert "## Description" in result
    assert "This is the bug description." in result


def test_format_issue_journals():
    issue = {
        "id": 1,
        "subject": "With journals",
        "journals": [
            {
                "user": {"name": "Alice"},
                "created_on": "2025-01-01",
                "notes": "First comment",
                "details": [],
            },
            {
                "user": {"name": "Bob"},
                "created_on": "2025-01-02",
                "notes": "",
                "details": [
                    {"name": "status_id", "old_value": "1", "new_value": "2"},
                ],
            },
        ],
    }
    result = _format_issue(issue)
    assert "## Journal / Comments" in result
    assert "### Alice — 2025-01-01" in result
    assert "First comment" in result
    assert "### Bob — 2025-01-02" in result
    assert "status_id: 1 → 2" in result


def test_format_issue_empty_journals_skipped():
    issue = {
        "id": 1,
        "subject": "Empty journal",
        "journals": [
            {"user": {"name": "Alice"}, "created_on": "2025-01-01", "notes": "", "details": []},
        ],
    }
    result = _format_issue(issue)
    assert "### Alice" not in result
