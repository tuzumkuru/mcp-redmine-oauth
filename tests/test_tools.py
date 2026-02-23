"""Unit tests for MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_redmine_oauth.tools import (
    MAX_JOURNAL_ENTRIES,
    _format_issue,
    _format_issue_list,
    _format_project,
    _format_relations,
    _format_search_results,
    _format_time_entries,
    _format_versions,
)


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


# --- list_issues formatting ---


def test_format_issue_list_empty():
    data = {"issues": [], "total_count": 0, "offset": 0, "limit": 25}
    assert _format_issue_list(data) == "No issues found matching the filters."


def test_format_issue_list_basic():
    data = {
        "issues": [
            {
                "id": 42,
                "subject": "Fix login bug",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "assigned_to": {"name": "Alice"},
                "updated_on": "2025-06-15T10:00:00Z",
            },
            {
                "id": 43,
                "subject": "Add dark mode",
                "status": {"name": "New"},
                "priority": {"name": "Normal"},
                "updated_on": "2025-06-14T08:00:00Z",
            },
        ],
        "total_count": 2,
        "offset": 0,
        "limit": 25,
    }
    result = _format_issue_list(data)
    assert "2 issue(s)" in result
    assert "**#42** Fix login bug" in result
    assert "Status: In Progress" in result
    assert "Priority: High" in result
    assert "Assigned: Alice" in result
    assert "**#43** Add dark mode" in result
    assert "Assigned: Unassigned" in result


def test_format_issue_list_pagination():
    data = {
        "issues": [{"id": i, "subject": f"Issue {i}"} for i in range(25)],
        "total_count": 50,
        "offset": 0,
        "limit": 25,
    }
    result = _format_issue_list(data)
    assert "50 issue(s)" in result
    assert "offset=25" in result


def test_format_issue_list_no_pagination_when_all_shown():
    data = {
        "issues": [{"id": 1, "subject": "Only issue"}],
        "total_count": 1,
        "offset": 0,
        "limit": 25,
    }
    result = _format_issue_list(data)
    assert "offset=" not in result


# --- get_issue_relations formatting ---


def test_format_relations_empty():
    assert _format_relations(42, {"relations": []}) == "Issue #42 has no relations."


def test_format_relations_outgoing():
    data = {
        "relations": [
            {"relation_type": "blocks", "issue_id": 42, "issue_to_id": 99},
        ]
    }
    result = _format_relations(42, data)
    assert "**blocks** → #99" in result


def test_format_relations_incoming():
    data = {
        "relations": [
            {"relation_type": "blocks", "issue_id": 10, "issue_to_id": 42},
        ]
    }
    result = _format_relations(42, data)
    assert "**blocks** ← #10" in result


def test_format_relations_with_delay():
    data = {
        "relations": [
            {"relation_type": "precedes", "issue_id": 42, "issue_to_id": 43, "delay": 3},
        ]
    }
    result = _format_relations(42, data)
    assert "Delay: 3 day(s)" in result


# --- get_project_details formatting ---


def test_format_project_empty():
    assert _format_project({"project": {}}) == "Error: could not retrieve project details."


def test_format_project_basic():
    data = {
        "project": {
            "id": 1,
            "name": "Alpha",
            "identifier": "alpha",
            "status": 1,
            "created_on": "2024-01-01",
            "updated_on": "2025-01-01",
            "description": "Main project",
        }
    }
    result = _format_project(data)
    assert "# Alpha" in result
    assert "**Identifier:** alpha" in result
    assert "**Status:** active" in result
    assert "Main project" in result


def test_format_project_with_includes():
    data = {
        "project": {
            "id": 1,
            "name": "Alpha",
            "identifier": "alpha",
            "status": 1,
            "created_on": "2024-01-01",
            "updated_on": "2025-01-01",
            "trackers": [{"id": 1, "name": "Bug"}, {"id": 2, "name": "Feature"}],
            "issue_categories": [{"id": 10, "name": "Backend"}],
            "enabled_modules": [{"name": "issue_tracking"}, {"name": "wiki"}],
        }
    }
    result = _format_project(data)
    assert "## Trackers" in result
    assert "Bug (id=1)" in result
    assert "## Issue Categories" in result
    assert "Backend (id=10)" in result
    assert "## Enabled Modules" in result
    assert "issue_tracking" in result
    assert "wiki" in result


def test_format_project_closed_status():
    data = {
        "project": {
            "id": 1, "name": "Old", "identifier": "old",
            "status": 5, "created_on": "2024-01-01", "updated_on": "2025-01-01",
        }
    }
    result = _format_project(data)
    assert "closed/archived" in result


# --- get_project_versions formatting ---


def test_format_versions_empty():
    assert _format_versions("alpha", {"versions": []}) == "No versions found for project 'alpha'."


def test_format_versions_basic():
    data = {
        "versions": [
            {
                "id": 1,
                "name": "v1.0",
                "status": "open",
                "due_date": "2025-12-31",
                "sharing": "none",
                "description": "First release",
            },
            {
                "id": 2,
                "name": "v2.0",
                "status": "locked",
                "due_date": None,
                "sharing": "hierarchy",
                "description": "",
            },
        ]
    }
    result = _format_versions("alpha", data)
    assert "Versions for 'alpha'" in result
    assert "**v1.0** (id=1, status: open)" in result
    assert "Due: 2025-12-31" in result
    assert "First release" in result
    assert "**v2.0** (id=2, status: locked)" in result


# --- list_time_entries formatting ---


def test_format_time_entries_empty():
    data = {"time_entries": [], "total_count": 0, "offset": 0, "limit": 25}
    assert _format_time_entries(data) == "No time entries found."


def test_format_time_entries_basic():
    data = {
        "time_entries": [
            {
                "id": 1,
                "user": {"name": "Alice"},
                "project": {"name": "Alpha"},
                "issue": {"id": 42},
                "hours": 2.5,
                "activity": {"name": "Development"},
                "spent_on": "2025-06-15",
                "comments": "Fixed login bug",
            },
            {
                "id": 2,
                "user": {"name": "Bob"},
                "project": {"name": "Alpha"},
                "hours": 1.0,
                "activity": {"name": "Review"},
                "spent_on": "2025-06-15",
                "comments": "",
            },
        ],
        "total_count": 2,
        "offset": 0,
        "limit": 25,
    }
    result = _format_time_entries(data)
    assert "2 time entry/entries" in result
    assert "3.50 hours on this page" in result
    assert "**2.50h** — Alice on 2025-06-15 (issue #42)" in result
    assert "Development" in result
    assert '"Fixed login bug"' in result
    assert "**1.00h** — Bob on 2025-06-15" in result
    assert "issue #" not in result.split("Bob")[1]  # Bob has no issue


def test_format_time_entries_pagination():
    data = {
        "time_entries": [
            {"id": i, "user": {"name": "User"}, "hours": 1.0, "spent_on": "2025-01-01"}
            for i in range(25)
        ],
        "total_count": 50,
        "offset": 0,
        "limit": 25,
    }
    result = _format_time_entries(data)
    assert "offset=25" in result


def test_format_time_entries_long_comment_truncated():
    data = {
        "time_entries": [
            {
                "id": 1,
                "user": {"name": "Alice"},
                "hours": 1.0,
                "spent_on": "2025-01-01",
                "comments": "x" * 200,
            }
        ],
        "total_count": 1,
        "offset": 0,
        "limit": 25,
    }
    result = _format_time_entries(data)
    assert "…" in result
