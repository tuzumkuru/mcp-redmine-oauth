"""Unit tests for the draft tools (prefilled Redmine form links)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qsl, urlsplit

import pytest

from mcp_redmine_oauth.drafts import (
    MAX_LINK_LENGTH,
    NOTHING_SAVED,
    DraftTooLongError,
    build_draft,
    issue_params,
    register_draft_tools,
)

BASE = "https://redmine.example.com"


@pytest.fixture()
def draft_fns():
    """Register the draft tools on a stub and return the tool functions by name."""
    mcp = MagicMock()
    captured = {}

    def capture_tool():
        def decorator(fn):
            captured[fn.__name__] = fn
            return fn

        return decorator

    mcp.tool = capture_tool
    register_draft_tools(mcp, BASE + "/")
    return captured


@pytest.fixture()
def logged_in():
    token = MagicMock()
    token.scopes = []
    with patch("mcp_redmine_oauth.scopes.get_access_token", return_value=token):
        yield


def _link(result: str) -> str:
    return next(line for line in result.splitlines() if line.startswith(BASE))


def _query(url: str) -> list[tuple[str, str]]:
    return parse_qsl(urlsplit(url).query)


# --- issue_params ---


def test_issue_params_skips_none_and_keeps_order():
    params = issue_params({"subject": "Printer offline", "description": None, "priority_id": 3}, None)
    assert params == [("issue[subject]", "Printer offline"), ("issue[priority_id]", "3")]


def test_issue_params_keeps_empty_string_to_clear_a_field():
    assert issue_params({"assigned_to_id": "", "due_date": None}, None) == [("issue[assigned_to_id]", "")]


def test_issue_params_custom_fields_single_and_multi_value():
    params = issue_params({}, {"5": "Ankara", "7": ["a", "b"]})
    assert params == [
        ("issue[custom_field_values][5]", "Ankara"),
        ("issue[custom_field_values][7][]", "a"),
        ("issue[custom_field_values][7][]", "b"),
    ]


# --- build_draft ---


def test_build_draft_encodes_values_and_brackets():
    draft = build_draft(BASE, "/issues/1/edit", [("issue[notes]", "Ölçüm & test #2 = ok")], {})
    assert "issue%5Bnotes%5D=" in draft.url
    assert "[" not in draft.url and "]" not in draft.url
    assert _query(draft.url) == [("issue[notes]", "Ölçüm & test #2 = ok")]
    assert draft.left_out == {}


def test_build_draft_without_params_has_no_query():
    assert build_draft(BASE, "/projects/new", [], {}).url == f"{BASE}/projects/new"


def test_build_draft_leaves_out_long_text_when_link_too_long():
    long_text = "x" * (MAX_LINK_LENGTH + 100)
    params = [("issue[subject]", "Short"), ("issue[description]", long_text)]
    draft = build_draft(BASE, "/projects/p/issues/new", params, {"issue[description]": "Description"})
    assert len(draft.url) <= MAX_LINK_LENGTH
    assert _query(draft.url) == [("issue[subject]", "Short")]
    assert draft.left_out == {"Description": long_text}


def test_build_draft_leaves_out_longest_field_first():
    params = [
        ("issue[description]", "d" * (MAX_LINK_LENGTH - 500)),
        ("issue[notes]", "n" * 1000),
    ]
    draft = build_draft(
        BASE, "/issues/1/edit", params, {"issue[description]": "Description", "issue[notes]": "Notes"}
    )
    assert list(draft.left_out) == ["Description"]
    assert ("issue[notes]", "n" * 1000) in _query(draft.url)


def test_build_draft_raises_when_short_fields_alone_are_too_long():
    params = [("issue[subject]", "s" * (MAX_LINK_LENGTH + 1))]
    with pytest.raises(DraftTooLongError):
        build_draft(BASE, "/projects/p/issues/new", params, {"issue[description]": "Description"})


# --- tools ---


@pytest.mark.asyncio
async def test_draft_new_issue_link(draft_fns, logged_in):
    result = await draft_fns["draft_new_issue"](
        project_id="it-ops",
        subject="Printer offline",
        tracker_id=1,
        assigned_to_id="me",
        custom_fields={"5": "Ankara"},
    )
    url = _link(result)
    assert url.startswith(f"{BASE}/projects/it-ops/issues/new?")
    assert _query(url) == [
        ("issue[tracker_id]", "1"),
        ("issue[subject]", "Printer offline"),
        ("issue[assigned_to_id]", "me"),
        ("issue[custom_field_values][5]", "Ankara"),
    ]
    assert NOTHING_SAVED in result


@pytest.mark.asyncio
async def test_draft_new_issue_escapes_project_identifier(draft_fns, logged_in):
    result = await draft_fns["draft_new_issue"](project_id="a/b", subject="x")
    assert _link(result).startswith(f"{BASE}/projects/a%2Fb/issues/new?")


@pytest.mark.asyncio
async def test_draft_issue_update_link(draft_fns, logged_in):
    result = await draft_fns["draft_issue_update"](issue_id=42, status_id=5, notes="Fixed by restart")
    url = _link(result)
    assert url.startswith(f"{BASE}/issues/42/edit?")
    assert _query(url) == [("issue[status_id]", "5"), ("issue[notes]", "Fixed by restart")]
    assert f"Current state and history: {BASE}/issues/42" in result


@pytest.mark.asyncio
async def test_draft_issue_update_returns_long_notes_separately(draft_fns, logged_in):
    notes = "n" * (MAX_LINK_LENGTH + 10)
    result = await draft_fns["draft_issue_update"](issue_id=42, status_id=5, notes=notes)
    assert _query(_link(result)) == [("issue[status_id]", "5")]
    assert "### Notes" in result
    assert notes in result


@pytest.mark.asyncio
async def test_draft_issue_update_reports_error_when_too_long(draft_fns, logged_in):
    result = await draft_fns["draft_issue_update"](issue_id=42, subject="s" * (MAX_LINK_LENGTH + 1))
    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_draft_new_project_link(draft_fns, logged_in):
    result = await draft_fns["draft_new_project"](name="Lab", identifier="lab", is_public=False)
    url = _link(result)
    assert url.startswith(f"{BASE}/projects/new?")
    assert _query(url) == [
        ("project[name]", "Lab"),
        ("project[identifier]", "lab"),
        ("project[is_public]", "0"),
    ]


@pytest.mark.asyncio
async def test_draft_tools_need_a_login(draft_fns):
    with patch("mcp_redmine_oauth.scopes.get_access_token", return_value=None):
        result = await draft_fns["draft_new_issue"](project_id="p", subject="x")
    assert result.startswith("Error: not authenticated")
