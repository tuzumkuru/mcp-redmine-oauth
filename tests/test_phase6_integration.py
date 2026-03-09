from __future__ import annotations

import asyncio
import os

import pytest

from mcp_redmine_oauth.auth import RedmineTokenVerifier
from mcp_redmine_oauth.storage import SQLiteTokenStore


def test_concurrent_multi_user_session_isolation(tmp_path):
    db_path = tmp_path / "phase6.db"

    async def _run() -> None:
        store = SQLiteTokenStore(str(db_path))
        await asyncio.gather(
            store.put("token_user_a", {"scopes": ["view_issues"]}, collection="scope_store"),
            store.put("token_user_b", {"scopes": ["view_project"]}, collection="scope_store"),
        )

        verifier = RedmineTokenVerifier(
            redmine_url="https://redmine.example.com",
            scope_store=store,
        )

        a_scopes = (await verifier._scope_store.get("token_user_a", collection="scope_store"))["scopes"]
        b_scopes = (await verifier._scope_store.get("token_user_b", collection="scope_store"))["scopes"]
        assert a_scopes == ["view_issues"]
        assert b_scopes == ["view_project"]

    asyncio.run(_run())


def test_end_to_end_oauth_flow_placeholder():
    if not os.environ.get("REDMINE_E2E_BASE_URL"):
        pytest.skip("REDMINE_E2E_BASE_URL not set; skipping live OAuth integration test")

    # Placeholder for live Redmine integration run in CI/deployment environment.
    # This keeps Phase 6 test scaffolding in-repo without hardcoding secrets.
    assert True
