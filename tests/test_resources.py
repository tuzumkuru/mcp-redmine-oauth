"""Unit tests for MCP resource formatters."""

from __future__ import annotations

from mcp_redmine_oauth.resources import (
    _format_priorities,
    _format_projects,
    _format_statuses,
    _format_trackers,
    _format_user,
)


# --- _format_projects ---


def test_active_projects_empty():
    assert _format_projects({"projects": []}) == "No active projects found."


def test_active_projects_basic():
    data = {
        "projects": [
            {"id": 1, "name": "Alpha", "identifier": "alpha", "description": "First project"},
            {"id": 2, "name": "Beta", "identifier": "beta", "description": ""},
        ]
    }
    result = _format_projects(data)
    assert "Active Projects (2)" in result
    assert "**Alpha** (`alpha`, id=1)" in result
    assert "First project" in result
    assert "**Beta** (`beta`, id=2)" in result


def test_active_projects_long_description_truncated():
    data = {
        "projects": [
            {"id": 1, "name": "Long", "identifier": "long", "description": "a" * 200},
        ]
    }
    result = _format_projects(data)
    assert "…" in result


# --- _format_trackers ---


def test_trackers_empty():
    assert _format_trackers({"trackers": []}) == "No trackers found."


def test_trackers_basic():
    data = {
        "trackers": [
            {"id": 1, "name": "Bug", "default_status": {"id": 1, "name": "New"}},
            {"id": 2, "name": "Feature", "default_status": {"id": 1, "name": "New"}},
        ]
    }
    result = _format_trackers(data)
    assert "Trackers (2)" in result
    assert "**Bug** (id=1, default status: New)" in result
    assert "**Feature** (id=2, default status: New)" in result


# --- _format_user ---


def test_current_user_empty():
    assert _format_user({"user": {}}) == "Error: could not retrieve user profile."


def test_current_user_basic():
    data = {
        "user": {
            "id": 5,
            "login": "jdoe",
            "firstname": "John",
            "lastname": "Doe",
            "mail": "jdoe@example.com",
            "created_on": "2024-01-01T00:00:00Z",
            "last_login_on": "2025-06-15T12:00:00Z",
            "admin": False,
        }
    }
    result = _format_user(data)
    assert "# John Doe" in result
    assert "**Login:** jdoe" in result
    assert "**ID:** 5" in result
    assert "**Email:** jdoe@example.com" in result
    assert "**Admin:** False" in result


# --- _format_statuses ---


def test_statuses_empty():
    assert _format_statuses({"issue_statuses": []}) == "No issue statuses found."


def test_statuses_basic():
    data = {
        "issue_statuses": [
            {"id": 1, "name": "New", "is_closed": False},
            {"id": 2, "name": "In Progress", "is_closed": False},
            {"id": 5, "name": "Closed", "is_closed": True},
        ]
    }
    result = _format_statuses(data)
    assert "Issue Statuses (3)" in result
    assert "**New** (id=1)" in result
    assert "(closed)" not in result.split("New")[1].split("\n")[0]
    assert "**Closed** (id=5) (closed)" in result


def test_statuses_no_closed_flag():
    data = {"issue_statuses": [{"id": 1, "name": "Open"}]}
    result = _format_statuses(data)
    assert "(closed)" not in result


# --- _format_priorities ---


def test_priorities_empty():
    assert _format_priorities({"issue_priorities": []}) == "No priority levels found."


def test_priorities_basic():
    data = {
        "issue_priorities": [
            {"id": 1, "name": "Low", "is_default": False},
            {"id": 2, "name": "Normal", "is_default": True},
            {"id": 3, "name": "High", "is_default": False},
        ]
    }
    result = _format_priorities(data)
    assert "Issue Priorities (3)" in result
    assert "**Low** (id=1)" in result
    assert "**Normal** (id=2) ← default" in result
    assert "**High** (id=3)" in result
    assert "default" not in result.split("High")[1]


def test_priorities_no_default():
    data = {"issue_priorities": [{"id": 1, "name": "Normal"}]}
    result = _format_priorities(data)
    assert "default" not in result
