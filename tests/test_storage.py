from __future__ import annotations

import asyncio

from mcp_redmine_oauth.storage import SQLiteTokenStore, create_token_store


def test_sqlite_store_persists_across_instances(tmp_path):
    db_path = tmp_path / "token_store.db"

    async def _run() -> None:
        first = SQLiteTokenStore(str(db_path))
        await first.put("abc", {"scopes": ["view_issues"]}, collection="scope_store")

        second = SQLiteTokenStore(str(db_path))
        loaded = await second.get("abc", collection="scope_store")
        assert loaded == {"scopes": ["view_issues"]}

    asyncio.run(_run())


def test_create_token_store_defaults_to_sqlite():
    store = create_token_store(None)
    assert isinstance(store, SQLiteTokenStore)


def test_create_token_store_sqlite_url_relative_path():
    store = create_token_store("sqlite://.data/custom.db")
    assert isinstance(store, SQLiteTokenStore)
    assert store.db_path == ".data/custom.db"
