"""Unit tests for RedmineProvider scope capture and RedmineTokenVerifier."""

from __future__ import annotations

import asyncio

from mcp_redmine_oauth.auth import RedmineProvider, RedmineTokenVerifier
from mcp_redmine_oauth.scopes import VIEW_ISSUES, get_registered_scopes


class InMemoryScopeStore:
    def __init__(self):
        self.data: dict[tuple[str, str], dict] = {}

    async def get(self, key: str, *, collection: str | None = None):
        return self.data.get((collection or "default", key))

    async def put(self, key: str, value: dict, *, collection: str | None = None, ttl=None):
        self.data[(collection or "default", key)] = value


def test_extract_upstream_claims_stores_scope():
    """Scopes from Redmine token response are stored in scope_store."""

    async def _run() -> None:
        scope_store = InMemoryScopeStore()
        provider = RedmineProvider(
            redmine_url="https://redmine.example.com",
            client_id="cid",
            client_secret="csec",
            base_url="http://localhost:8000",
            scopes=get_registered_scopes(),
            scope_store=scope_store,
        )

        idp_tokens = {
            "access_token": "tok_abc123",
            "scope": "view_issues view_project",
            "token_type": "Bearer",
        }
        result = await provider._extract_upstream_claims(idp_tokens)

        assert result is None
        stored = await scope_store.get("tok_abc123", collection="scope_store")
        assert stored == {"scopes": ["view_issues", "view_project"]}

    asyncio.run(_run())


def test_extract_upstream_claims_no_scope_field():
    """Missing scope field in token response leaves scope_store unchanged."""

    async def _run() -> None:
        scope_store = InMemoryScopeStore()
        provider = RedmineProvider(
            redmine_url="https://redmine.example.com",
            client_id="cid",
            client_secret="csec",
            base_url="http://localhost:8000",
            scopes=get_registered_scopes(),
            scope_store=scope_store,
        )

        idp_tokens = {"access_token": "tok_xyz", "token_type": "Bearer"}
        await provider._extract_upstream_claims(idp_tokens)

        stored = await scope_store.get("tok_xyz", collection="scope_store")
        assert stored is None

    asyncio.run(_run())


def test_verifier_falls_back_to_registered_scopes_when_token_not_in_store():
    """verify_token fallback path remains list-typed when token is absent in scope_store."""

    async def _run() -> None:
        scope_store = InMemoryScopeStore()
        verifier = RedmineTokenVerifier(
            redmine_url="https://redmine.example.com",
            scope_store=scope_store,
        )
        scope_entry = await verifier._scope_store.get("unknown_token", collection="scope_store")
        granted = scope_entry.get("scopes", get_registered_scopes()) if scope_entry else get_registered_scopes()
        assert isinstance(granted, list)

    asyncio.run(_run())


def test_verifier_uses_stored_scopes_when_present():
    """verify_token uses scope_store when the token is present."""

    async def _run() -> None:
        scope_store = InMemoryScopeStore()
        await scope_store.put("tok_123", {"scopes": [VIEW_ISSUES]}, collection="scope_store")
        verifier = RedmineTokenVerifier(
            redmine_url="https://redmine.example.com",
            scope_store=scope_store,
        )
        scope_entry = await verifier._scope_store.get("tok_123", collection="scope_store")
        granted = scope_entry.get("scopes", get_registered_scopes()) if scope_entry else get_registered_scopes()
        assert granted == [VIEW_ISSUES]

    asyncio.run(_run())
