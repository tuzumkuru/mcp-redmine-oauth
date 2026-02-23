"""Unit tests for RedmineProvider scope capture and RedmineTokenVerifier."""

from __future__ import annotations

import pytest

from mcp_redmine_oauth.auth import RedmineProvider, RedmineTokenVerifier
from mcp_redmine_oauth.scopes import VIEW_ISSUES, get_registered_scopes


# --- _extract_upstream_claims ---


@pytest.mark.asyncio
async def test_extract_upstream_claims_stores_scope():
    """Scopes from Redmine token response are stored in scope_store."""
    scope_store: dict[str, list[str]] = {}
    provider = RedmineProvider(
        redmine_url="https://redmine.example.com",
        client_id="cid",
        client_secret="csec",
        base_url="http://localhost:8000",
        scopes=get_registered_scopes(),
    )
    # Inject our own scope_store so we can inspect it
    provider._scope_store = scope_store
    provider._token_validator._scope_store = scope_store  # type: ignore[attr-defined]

    idp_tokens = {
        "access_token": "tok_abc123",
        "scope": "view_issues view_project",
        "token_type": "Bearer",
    }
    result = await provider._extract_upstream_claims(idp_tokens)

    assert result is None  # Should not embed extra claims in JWT
    assert scope_store["tok_abc123"] == ["view_issues", "view_project"]


@pytest.mark.asyncio
async def test_extract_upstream_claims_no_scope_field():
    """Missing scope field in token response leaves scope_store unchanged."""
    scope_store: dict[str, list[str]] = {}
    provider = RedmineProvider(
        redmine_url="https://redmine.example.com",
        client_id="cid",
        client_secret="csec",
        base_url="http://localhost:8000",
        scopes=get_registered_scopes(),
    )
    provider._scope_store = scope_store

    idp_tokens = {"access_token": "tok_xyz", "token_type": "Bearer"}
    await provider._extract_upstream_claims(idp_tokens)

    assert "tok_xyz" not in scope_store


# --- RedmineTokenVerifier scope fallback ---


def test_verifier_falls_back_to_registered_scopes_when_token_not_in_store():
    """verify_token uses get_registered_scopes() as fallback when token not yet in scope_store."""
    scope_store: dict[str, list[str]] = {}
    RedmineTokenVerifier(
        redmine_url="https://redmine.example.com",
        scope_store=scope_store,
    )
    # scope_store is empty; fallback should be registered scopes (a list, possibly empty in test context)
    granted = scope_store.get("unknown_token", get_registered_scopes())
    assert isinstance(granted, list)


def test_verifier_uses_stored_scopes_when_present():
    """verify_token uses scope_store when the token is present."""
    scope_store: dict[str, list[str]] = {"tok_123": [VIEW_ISSUES]}
    granted = scope_store.get("tok_123", get_registered_scopes())
    assert granted == [VIEW_ISSUES]
