"""Async HTTP client for the Redmine REST API."""

from __future__ import annotations

from typing import Any

import httpx
from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)


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


class RedmineValidationError(RedmineAPIError):
    """422 Unprocessable Entity — validation failed (e.g. missing required fields)."""

    def __init__(self, status_code: int, message: str, errors: list[str] | None = None):
        self.errors = errors or []
        super().__init__(status_code, message)


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
        logger.info("event=redmine_request method=GET path=%s", path)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        self._raise_for_status(response)
        logger.info("event=redmine_response method=GET path=%s status_code=%d", path, response.status_code)
        return response.json()

    async def post(
        self, path: str, token: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        logger.info("event=redmine_request method=POST path=%s", path)
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
        logger.info("event=redmine_response method=POST path=%s status_code=%d", path, response.status_code)
        return response.json()

    async def put(
        self, path: str, token: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        logger.info("event=redmine_request method=PUT path=%s", path)
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
        logger.info("event=redmine_response method=PUT path=%s status_code=%d", path, response.status_code)
        if response.status_code == 204:
            return None
        return response.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code >= 400:
            logger.warning("event=redmine_error status_code=%d body=%s", response.status_code, response.text[:300])
        if response.status_code == 401:
            raise RedmineAuthError(401, "Authentication failed — token may be expired.")
        if response.status_code == 403:
            raise RedmineForbiddenError(403, "Permission denied.")
        if response.status_code == 404:
            raise RedmineNotFoundError(404, "Resource not found in Redmine.")
        if response.status_code == 422:
            errors = []
            try:
                body = response.json()
                errors = body.get("errors", [])
            except Exception:
                pass
            raise RedmineValidationError(
                422,
                f"Validation failed: {'; '.join(errors) if errors else 'unknown error'}",
                errors=errors,
            )
        if response.status_code >= 500:
            raise RedmineAPIError(
                response.status_code, f"Redmine server error ({response.status_code})."
            )
