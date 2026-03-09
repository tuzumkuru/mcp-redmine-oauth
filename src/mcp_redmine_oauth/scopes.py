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
from fastmcp.server.context import Context
from fastmcp.server.dependencies import get_access_token, get_context

# --- Scope constants ---

VIEW_PROJECT = "view_project"
VIEW_ISSUES = "view_issues"
SEARCH_PROJECT = "search_project"  # Required for /search.json and project-scoped search
VIEW_TIME_ENTRIES = "view_time_entries"  # Phase 4: list_time_entries
ADD_ISSUES = "add_issues"               # Phase 5: create_issue
EDIT_ISSUES = "edit_issues"             # Phase 5: update_issue
ADD_PROJECT = "add_project"             # Phase 5: create_project
EDIT_PROJECT = "edit_project"           # Phase 5: update_project
VIEW_WIKI_PAGES = "view_wiki_pages"     # Phase 5: get_wiki_page
EDIT_WIKI_PAGES = "edit_wiki_pages"     # Phase 5: update_wiki_page
RENAME_WIKI_PAGES = "rename_wiki_pages" # Phase 5: rename_wiki_page


# --- Global scope registry (populated at decoration time) ---

_registry: set[str] = set()
_scope_requirements_by_tool: dict[str, list[str]] = {}
_scope_visibility_applied_sessions: set[str] = set()

# Optional allowlist: when set, only these scopes are requested from Redmine.
# Scopes declared by tools but not in this set won't be requested during OAuth;
# those tools will return a scope-missing error at call time.
_allowed_scopes: set[str] | None = None


def set_allowed_scopes(scopes: list[str]) -> None:
    """Set the allowlist of scopes the Redmine OAuth app supports.

    When set, get_effective_scopes() returns only the intersection of declared
    tool scopes and this allowlist.  When not set, all declared scopes are used.
    """
    global _allowed_scopes
    _allowed_scopes = set(scopes)


def get_registered_scopes() -> list[str]:
    """Return all scopes declared via @requires_scopes across all registered tools.

    Call this after register_tools() and register_resources() to get the complete set.
    Used by verify_token fallback — always returns the full set regardless of allowlist.
    """
    return sorted(_registry)


def get_effective_scopes() -> list[str]:
    """Return the scopes to actually request during OAuth authorization.

    If an allowlist is set (via set_allowed_scopes), returns the intersection of
    declared tool scopes and the allowlist.  Otherwise returns all declared scopes.
    """
    if _allowed_scopes is not None:
        return sorted(_registry & _allowed_scopes)
    return sorted(_registry)


async def _disable_tools_for_missing_scopes(token: AccessToken, context: Context | None) -> None:
    """Disable out-of-scope tools per session on first authenticated request."""
    if context is None or context.session_id is None:
        return
    session_id = str(context.session_id)
    if session_id in _scope_visibility_applied_sessions:
        return

    granted = set(token.scopes or [])
    tools_to_disable = {
        tool_name
        for tool_name, required_scopes in _scope_requirements_by_tool.items()
        if required_scopes and not set(required_scopes).issubset(granted)
    }

    if tools_to_disable:
        await context.disable_components(names=tools_to_disable, components={"tool"})

    _scope_visibility_applied_sessions.add(session_id)


# --- Decorator ---


def requires_scopes(*scopes: str) -> Callable:
    """Declare required OAuth scopes on a tool or resource.

    At decoration time: registers scopes to the global registry so server.py can
    collect them to build the OAuth scope request.

    At call time: checks that the request is authenticated and that the token has
    all required scopes; returns a descriptive error string otherwise.
    """
    _registry.update(scopes)

    def decorator(fn: Callable) -> Callable:
        _scope_requirements_by_tool[fn.__name__] = list(scopes)

        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            token = get_access_token()
            if token is None:
                return "Error: not authenticated. Please complete the OAuth flow first."

            context = kwargs.get("context")
            if not isinstance(context, Context):
                context = get_context()
            await _disable_tools_for_missing_scopes(token, context)

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
