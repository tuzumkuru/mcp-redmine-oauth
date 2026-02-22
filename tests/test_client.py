"""Unit tests for RedmineClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from mcp_redmine_oauth.client import (
    RedmineAPIError,
    RedmineAuthError,
    RedmineClient,
    RedmineForbiddenError,
    RedmineNotFoundError,
)


def _mock_response(status_code: int, json_data: dict | None = None) -> httpx.Response:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


# --- _raise_for_status ---


def test_raise_for_status_401():
    resp = _mock_response(401)
    with pytest.raises(RedmineAuthError) as exc_info:
        RedmineClient._raise_for_status(resp)
    assert exc_info.value.status_code == 401


def test_raise_for_status_403():
    resp = _mock_response(403)
    with pytest.raises(RedmineForbiddenError) as exc_info:
        RedmineClient._raise_for_status(resp)
    assert exc_info.value.status_code == 403


def test_raise_for_status_404():
    resp = _mock_response(404)
    with pytest.raises(RedmineNotFoundError) as exc_info:
        RedmineClient._raise_for_status(resp)
    assert exc_info.value.status_code == 404


def test_raise_for_status_500():
    resp = _mock_response(500)
    with pytest.raises(RedmineAPIError) as exc_info:
        RedmineClient._raise_for_status(resp)
    assert exc_info.value.status_code == 500


def test_raise_for_status_200_no_error():
    resp = _mock_response(200)
    RedmineClient._raise_for_status(resp)  # should not raise


def test_raise_for_status_204_no_error():
    resp = _mock_response(204)
    RedmineClient._raise_for_status(resp)  # should not raise


# --- client construction ---


def test_client_strips_trailing_slash():
    client = RedmineClient(base_url="https://redmine.example.com/")
    assert client.base_url == "https://redmine.example.com"


def test_client_default_timeout():
    client = RedmineClient(base_url="https://redmine.example.com")
    assert client.timeout == 30.0


def test_client_custom_timeout():
    client = RedmineClient(base_url="https://redmine.example.com", timeout=10.0)
    assert client.timeout == 10.0
