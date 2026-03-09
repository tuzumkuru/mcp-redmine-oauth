"""Token storage backends for OAuth state and Redmine scope persistence."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, SupportsFloat
from urllib.parse import urlparse

from key_value.aio.protocols import AsyncKeyValue


class SQLiteTokenStore(AsyncKeyValue):
    """Async key-value store backed by SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        def _init() -> None:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS kv_store (
                        collection TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        expires_at REAL,
                        PRIMARY KEY (collection, key)
                    )
                    """
                )
                conn.commit()

        await asyncio.to_thread(_init)
        self._initialized = True

    @staticmethod
    def _effective_collection(collection: str | None) -> str:
        return collection or "default"

    @staticmethod
    def _is_expired(expires_at: float | None) -> bool:
        return expires_at is not None and expires_at <= time.time()

    async def get(
        self,
        key: str,
        *,
        collection: str | None = None,
    ) -> dict[str, Any] | None:
        value, _ = await self.ttl(key, collection=collection)
        return value

    async def ttl(
        self,
        key: str,
        *,
        collection: str | None = None,
    ) -> tuple[dict[str, Any] | None, float | None]:
        await self._ensure_initialized()
        effective_collection = self._effective_collection(collection)

        def _ttl() -> tuple[dict[str, Any] | None, float | None]:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT value, expires_at FROM kv_store WHERE collection = ? AND key = ?",
                    (effective_collection, key),
                ).fetchone()
                if row is None:
                    return None, None

                raw_value, expires_at = row
                if self._is_expired(expires_at):
                    conn.execute(
                        "DELETE FROM kv_store WHERE collection = ? AND key = ?",
                        (effective_collection, key),
                    )
                    conn.commit()
                    return None, None

                remaining_ttl = None if expires_at is None else max(0.0, expires_at - time.time())
                return json.loads(raw_value), remaining_ttl

        return await asyncio.to_thread(_ttl)

    async def put(
        self,
        key: str,
        value: Mapping[str, Any],
        *,
        collection: str | None = None,
        ttl: SupportsFloat | None = None,
    ) -> None:
        await self._ensure_initialized()
        effective_collection = self._effective_collection(collection)
        expires_at = None if ttl is None else time.time() + float(ttl)

        def _put() -> None:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO kv_store(collection, key, value, expires_at)
                    VALUES(?, ?, ?, ?)
                    ON CONFLICT(collection, key) DO UPDATE SET
                        value = excluded.value,
                        expires_at = excluded.expires_at
                    """,
                    (effective_collection, key, json.dumps(dict(value)), expires_at),
                )
                conn.commit()

        await asyncio.to_thread(_put)

    async def delete(self, key: str, *, collection: str | None = None) -> bool:
        await self._ensure_initialized()
        effective_collection = self._effective_collection(collection)

        def _delete() -> bool:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM kv_store WHERE collection = ? AND key = ?",
                    (effective_collection, key),
                )
                conn.commit()
                return cursor.rowcount > 0

        return await asyncio.to_thread(_delete)

    async def get_many(
        self, keys: Sequence[str], *, collection: str | None = None
    ) -> list[dict[str, Any] | None]:
        return [await self.get(key, collection=collection) for key in keys]

    async def ttl_many(
        self, keys: Sequence[str], *, collection: str | None = None
    ) -> list[tuple[dict[str, Any] | None, float | None]]:
        return [await self.ttl(key, collection=collection) for key in keys]

    async def put_many(
        self,
        keys: Sequence[str],
        values: Sequence[Mapping[str, Any]],
        *,
        collection: str | None = None,
        ttl: SupportsFloat | None = None,
    ) -> None:
        if len(keys) != len(values):
            raise ValueError("keys and values must have same length")
        for key, value in zip(keys, values, strict=True):
            await self.put(key, value, collection=collection, ttl=ttl)

    async def delete_many(self, keys: Sequence[str], *, collection: str | None = None) -> int:
        deleted_count = 0
        for key in keys:
            if await self.delete(key, collection=collection):
                deleted_count += 1
        return deleted_count


def create_token_store(token_store_url: str | None = None) -> AsyncKeyValue:
    """Create a token store backend from TOKEN_STORE_URL."""
    if not token_store_url:
        return SQLiteTokenStore(".data/token_store.db")

    parsed = urlparse(token_store_url)
    if parsed.scheme == "sqlite":
        db_path = parsed.path
        if parsed.netloc and parsed.netloc != "":
            db_path = f"{parsed.netloc}{db_path}"
        if not db_path:
            raise ValueError("TOKEN_STORE_URL sqlite scheme requires a database path")
        if db_path.startswith("/") and token_store_url.startswith("sqlite:///"):
            final_path = db_path
        else:
            final_path = db_path.lstrip("/")
        return SQLiteTokenStore(final_path)

    if parsed.scheme == "redis":
        try:
            from key_value.aio.stores.redis import RedisStore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Redis token store requested but redis dependency is not installed. "
                "Install with: pip install redis"
            ) from exc
        return RedisStore(token_store_url)

    raise ValueError(
        f"Unsupported TOKEN_STORE_URL scheme '{parsed.scheme}'. Use sqlite:// or redis://"
    )
