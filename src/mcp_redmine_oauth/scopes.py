"""OAuth scope constants, decorator, and enforcement helpers for Redmine MCP tools.

Usage — declare scopes directly on each tool or resource:

    @mcp.tool()
    @requires_scopes(VIEW_ISSUES)
    async def get_issue_details(issue_id: int) -> str:
        ...  # auth + scope check handled by decorator

server.py collects all declared scopes automatically via get_registered_scopes().
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from fastmcp.server.auth import AccessToken
from fastmcp.server.dependencies import get_access_token

# --- Scope constants ---

VIEW_PROJECT = "view_project"
VIEW_ISSUES = "view_issues"
SEARCH_PROJECT = "search_project"  # Required for /search.json and project-scoped search
ADD_ISSUES = "add_issues"          # Phase 4: create_issue
EDIT_ISSUES = "edit_issues"        # Phase 4: update_issue


# --- Global scope registry (populated at decoration time) ---

_registry: set[str] = set()


def get_registered_scopes() -> list[str]:
    """Return all scopes declared via @requires_scopes across all registered tools.

    Call this after register_tools() and register_resources() to get the complete set
    of scopes to request during OAuth.
    """
    return sorted(_registry)


# --- Decorator ---


def requires_scopes(*scopes: str) -> Callable:
    """Declare required OAuth scopes on a tool or resource.

    At decoration time: registers scopes to the global registry so server.py can
    collect them to build the OAuth scope request.

    At call time: checks that the request is authenticated and that the token has
    all required scopes; returns a descriptive error string otherwise.

    Usage::

        @mcp.tool()
        @requires_scopes(VIEW_ISSUES, SEARCH_PROJECT)
        async def search_issues(query: str) -> str:
            token = get_access_token()  # guaranteed non-None here
            ...
    """
    _registry.update(scopes)

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            token = get_access_token()
            if token is None:
                return "Error: not authenticated. Please complete the OAuth flow first."
            if scopes:
                if err := check_scope(token, *scopes):
                    return err
            return await fn(*args, **kwargs)

        wrapper._required_scopes = list(scopes)  # type: ignore[attr-defined]
        return wrapper

    return decorator


# --- Enforcement helper (used internally by requires_scopes and by auth.py) ---


def check_scope(token: AccessToken, *required: str) -> str | None:
    """Return an error string if any required scope is missing, else None."""
    granted = set(token.scopes or [])
    missing = [s for s in required if s not in granted]
    if missing:
        return (
            f"Error: requires OAuth scope(s): {', '.join(missing)}. "
            "Please re-authorize with the required permissions."
        )
    return None
