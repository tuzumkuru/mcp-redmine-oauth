"""MCP resources exposing Redmine reference data."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from mcp_redmine_oauth.client import RedmineClient
from mcp_redmine_oauth.scopes import VIEW_PROJECT, requires_scopes


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
