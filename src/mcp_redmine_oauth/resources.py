"""MCP resources exposing Redmine reference data."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from mcp_redmine_oauth.client import RedmineClient
from mcp_redmine_oauth.scopes import VIEW_ISSUES, VIEW_PROJECT, requires_scopes


def register_resources(mcp: FastMCP, redmine: RedmineClient) -> None:
    """Register all Redmine resources on the FastMCP server."""

    @mcp.resource("redmine://projects/active")
    @requires_scopes(VIEW_PROJECT)
    async def active_projects() -> str:
        """Active Redmine projects accessible to the authenticated user."""
        token = get_access_token()
        data = await redmine.get(
            "/projects.json", token=token.token, params={"status": 1}
        )
        return _format_projects(data)

    @mcp.resource("redmine://trackers")
    @requires_scopes(VIEW_PROJECT)
    async def trackers() -> str:
        """Available issue trackers (Bug, Feature, etc.) with their IDs."""
        token = get_access_token()
        data = await redmine.get("/trackers.json", token=token.token)
        return _format_trackers(data)

    @mcp.resource("redmine://users/me")
    @requires_scopes()
    async def current_user() -> str:
        """Profile of the currently authenticated Redmine user."""
        token = get_access_token()
        data = await redmine.get("/users/current.json", token=token.token)
        return _format_user(data)

    @mcp.resource("redmine://issue-statuses")
    @requires_scopes(VIEW_ISSUES)
    async def issue_statuses() -> str:
        """All available issue statuses (New, In Progress, Closed, etc.) with IDs."""
        token = get_access_token()
        data = await redmine.get("/issue_statuses.json", token=token.token)
        return _format_statuses(data)

    @mcp.resource("redmine://enumerations/priorities")
    @requires_scopes(VIEW_ISSUES)
    async def issue_priorities() -> str:
        """Issue priority levels (Low, Normal, High, Urgent, Immediate) with IDs."""
        token = get_access_token()
        data = await redmine.get(
            "/enumerations/issue_priorities.json", token=token.token
        )
        return _format_priorities(data)


def _format_statuses(data: dict) -> str:
    statuses = data.get("issue_statuses", [])
    if not statuses:
        return "No issue statuses found."

    lines = [f"# Issue Statuses ({len(statuses)})", ""]
    for s in statuses:
        name = s.get("name", "Unnamed")
        sid = s.get("id")
        closed = " (closed)" if s.get("is_closed") else ""
        lines.append(f"- **{name}** (id={sid}){closed}")
    return "\n".join(lines)


def _format_priorities(data: dict) -> str:
    priorities = data.get("issue_priorities", [])
    if not priorities:
        return "No priority levels found."

    lines = [f"# Issue Priorities ({len(priorities)})", ""]
    for p in priorities:
        name = p.get("name", "Unnamed")
        pid = p.get("id")
        default = " ← default" if p.get("is_default") else ""
        lines.append(f"- **{name}** (id={pid}){default}")
    return "\n".join(lines)


def _format_projects(data: dict) -> str:
    projects = data.get("projects", [])
    if not projects:
        return "No active projects found."

    lines = [f"# Active Projects ({len(projects)})", ""]
    for p in projects:
        name = p.get("name", "Unnamed")
        identifier = p.get("identifier", "")
        desc = p.get("description", "")
        lines.append(f"- **{name}** (`{identifier}`, id={p.get('id')})")
        if desc:
            short = desc[:120] + "…" if len(desc) > 120 else desc
            lines.append(f"  {short}")
    return "\n".join(lines)


def _format_trackers(data: dict) -> str:
    trackers_list = data.get("trackers", [])
    if not trackers_list:
        return "No trackers found."

    lines = [f"# Trackers ({len(trackers_list)})", ""]
    for t in trackers_list:
        name = t.get("name", "Unnamed")
        tid = t.get("id")
        default_status = t.get("default_status", {}).get("name", "N/A")
        lines.append(f"- **{name}** (id={tid}, default status: {default_status})")
    return "\n".join(lines)


def _format_user(data: dict) -> str:
    user = data.get("user", {})
    if not user:
        return "Error: could not retrieve user profile."

    lines = [
        f"# {user.get('firstname', '')} {user.get('lastname', '')}",
        "",
        f"**Login:** {user.get('login', 'N/A')}",
        f"**ID:** {user.get('id', 'N/A')}",
        f"**Email:** {user.get('mail', 'N/A')}",
        f"**Created:** {user.get('created_on', 'N/A')}",
        f"**Last login:** {user.get('last_login_on', 'N/A')}",
        f"**Admin:** {user.get('admin', False)}",
    ]
    return "\n".join(lines)
