"""Async HTTP client for the Redmine REST API."""

from __future__ import annotations

from typing import Any

import httpx


class RedmineAPIError(Exception):
    """Base error for Redmine API failures."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)


class RedmineAuthError(RedmineAPIError):
    """401 Unauthorized — token is invalid or expired."""


class RedmineForbiddenError(RedmineAPIError):
    """403 Forbidden — user lacks permission for this action."""


class RedmineNotFoundError(RedmineAPIError):
    """404 Not Found — resource does not exist."""


class RedmineClient:
    """Thin async wrapper around Redmine's REST API.

    Each call requires a Bearer token so the client is stateless
    with respect to authentication.
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get(
        self, path: str, token: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        self._raise_for_status(response)
        return response.json()

    async def post(
        self, path: str, token: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                json=json,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        self._raise_for_status(response)
        return response.json()

    async def put(
        self, path: str, token: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.base_url}{path}",
                json=json,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        self._raise_for_status(response)
        if response.status_code == 204:
            return None
        return response.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise RedmineAuthError(401, "Authentication failed — token may be expired.")
        if response.status_code == 403:
            raise RedmineForbiddenError(403, "Permission denied.")
        if response.status_code == 404:
            raise RedmineNotFoundError(404, "Resource not found in Redmine.")
        if response.status_code >= 500:
            raise RedmineAPIError(
                response.status_code, f"Redmine server error ({response.status_code})."
            )
