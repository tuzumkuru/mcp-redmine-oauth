"""Unit tests for OAuth scope constants, registry, and requires_scopes decorator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.server.auth import AccessToken

from mcp_redmine_oauth.scopes import (
    ADD_ISSUES,
    EDIT_ISSUES,
    SEARCH_PROJECT,
    VIEW_ISSUES,
    VIEW_PROJECT,
    _registry,
    check_scope,
    get_registered_scopes,
    requires_scopes,
)


def _token(scopes: list[str] | None) -> AccessToken:
    tok = MagicMock(spec=AccessToken)
    tok.scopes = scopes
    return tok


# --- check_scope ---


def test_check_scope_passes_when_granted():
    assert check_scope(_token([VIEW_ISSUES, VIEW_PROJECT]), VIEW_ISSUES) is None


def test_check_scope_returns_error_when_missing():
    result = check_scope(_token([VIEW_PROJECT]), VIEW_ISSUES)
    assert result is not None
    assert "view_issues" in result
    assert "re-authorize" in result


def test_check_scope_multiple_all_present():
    assert check_scope(_token([VIEW_ISSUES, SEARCH_PROJECT]), VIEW_ISSUES, SEARCH_PROJECT) is None


def test_check_scope_multiple_one_missing():
    result = check_scope(_token([VIEW_ISSUES]), VIEW_ISSUES, SEARCH_PROJECT)
    assert result is not None
    assert "search_project" in result


def test_check_scope_empty_scopes_on_token():
    assert check_scope(_token([]), VIEW_ISSUES) is not None


def test_check_scope_none_scopes_on_token():
    assert check_scope(_token(None), VIEW_ISSUES) is not None


# --- get_registered_scopes ---


def test_get_registered_scopes_returns_sorted_list():
    scopes = get_registered_scopes()
    assert isinstance(scopes, list)
    assert scopes == sorted(scopes)


def test_registered_scopes_returns_list_of_strings():
    # get_registered_scopes() always returns a list (possibly empty before register_tools runs)
    scopes = get_registered_scopes()
    assert isinstance(scopes, list)
    assert all(isinstance(s, str) for s in scopes)


def test_requires_scopes_populates_registry():
    """Each @requires_scopes call adds its scopes to get_registered_scopes()."""
    before = set(get_registered_scopes())

    @requires_scopes("scope_a_unique_test", "scope_b_unique_test")
    async def _dummy() -> str:
        return "ok"

    after = set(get_registered_scopes())
    assert "scope_a_unique_test" in after
    assert "scope_b_unique_test" in after
    assert after.issuperset(before)

    # cleanup
    _registry.discard("scope_a_unique_test")
    _registry.discard("scope_b_unique_test")


# --- requires_scopes decorator ---


def test_requires_scopes_registers_to_registry():
    """@requires_scopes adds scopes to _registry at decoration time."""
    _registry.discard("test_scope_xyz")

    @requires_scopes("test_scope_xyz")
    async def _dummy() -> str:
        return "ok"

    assert "test_scope_xyz" in _registry
    _registry.discard("test_scope_xyz")  # cleanup


def test_requires_scopes_stores_on_wrapper():
    @requires_scopes(VIEW_ISSUES)
    async def _dummy() -> str:
        return "ok"

    assert _dummy._required_scopes == [VIEW_ISSUES]


@pytest.mark.asyncio
async def test_requires_scopes_blocks_unauthenticated():
    """When get_access_token() returns None, decorator returns error string."""

    @requires_scopes(VIEW_ISSUES)
    async def _dummy() -> str:
        return "success"

    with patch("mcp_redmine_oauth.scopes.get_access_token", return_value=None):
        result = await _dummy()

    assert "not authenticated" in result


@pytest.mark.asyncio
async def test_requires_scopes_blocks_missing_scope():
    """When token lacks required scope, decorator returns error string."""

    @requires_scopes(VIEW_ISSUES)
    async def _dummy() -> str:
        return "success"

    token = _token([VIEW_PROJECT])  # VIEW_ISSUES missing
    with patch("mcp_redmine_oauth.scopes.get_access_token", return_value=token):
        result = await _dummy()

    assert "view_issues" in result
    assert "re-authorize" in result


@pytest.mark.asyncio
async def test_requires_scopes_passes_with_valid_token():
    """When token has required scope, decorator calls the wrapped function."""

    @requires_scopes(VIEW_ISSUES)
    async def _dummy() -> str:
        return "success"

    token = _token([VIEW_ISSUES])
    with patch("mcp_redmine_oauth.scopes.get_access_token", return_value=token):
        result = await _dummy()

    assert result == "success"


@pytest.mark.asyncio
async def test_requires_scopes_no_args_passes_unauthenticated_check():
    """@requires_scopes() with no scopes still blocks unauthenticated calls."""

    @requires_scopes()
    async def _dummy() -> str:
        return "success"

    with patch("mcp_redmine_oauth.scopes.get_access_token", return_value=None):
        result = await _dummy()

    assert "not authenticated" in result


@pytest.mark.asyncio
async def test_requires_scopes_no_args_allows_authenticated():
    """@requires_scopes() with no scopes allows any authenticated call."""

    @requires_scopes()
    async def _dummy() -> str:
        return "success"

    token = _token([])  # authenticated but no scopes
    with patch("mcp_redmine_oauth.scopes.get_access_token", return_value=token):
        result = await _dummy()

    assert result == "success"
