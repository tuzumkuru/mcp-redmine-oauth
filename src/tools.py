"""MCP tools for Redmine issue operations."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from client import RedmineClient, RedmineForbiddenError


def register_tools(mcp: FastMCP, redmine: RedmineClient) -> None:
    """Register all Redmine tools on the FastMCP server."""

    @mcp.tool()
    async def get_issue_details(issue_id: int) -> str:
        """Fetch full Redmine issue details including description, custom fields,
        and complete journal/comment history.
        """
        token = get_access_token()
        if token is None:
            return "Error: not authenticated. Please complete the OAuth flow first."

        try:
            data = await redmine.get(
                f"/issues/{issue_id}.json",
                token=token.token,
                params={"include": "journals"},
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to view issue #{issue_id}."

        issue = data.get("issue", {})
        return _format_issue(issue)


def _format_issue(issue: dict) -> str:
    """Format a Redmine issue dict into readable text for the LLM."""
    lines = [
        f"# Issue #{issue.get('id')} — {issue.get('subject', 'No subject')}",
        "",
        f"**Project:** {issue.get('project', {}).get('name', 'N/A')}",
        f"**Tracker:** {issue.get('tracker', {}).get('name', 'N/A')}",
        f"**Status:** {issue.get('status', {}).get('name', 'N/A')}",
        f"**Priority:** {issue.get('priority', {}).get('name', 'N/A')}",
        f"**Author:** {issue.get('author', {}).get('name', 'N/A')}",
        f"**Assigned to:** {issue.get('assigned_to', {}).get('name', 'Unassigned')}",
        f"**Created:** {issue.get('created_on', 'N/A')}",
        f"**Updated:** {issue.get('updated_on', 'N/A')}",
        "",
    ]

    # Custom fields
    custom_fields = issue.get("custom_fields", [])
    if custom_fields:
        lines.append("## Custom Fields")
        for cf in custom_fields:
            lines.append(f"- **{cf.get('name')}:** {cf.get('value', '')}")
        lines.append("")

    # Description
    description = issue.get("description", "")
    if description:
        lines.append("## Description")
        lines.append(description)
        lines.append("")

    # Journal entries (comments + changes)
    journals = issue.get("journals", [])
    if journals:
        lines.append("## Journal / Comments")
        for entry in journals:
            author = entry.get("user", {}).get("name", "Unknown")
            date = entry.get("created_on", "")
            notes = entry.get("notes", "")

            details = entry.get("details", [])
            changes = [
                f"  - {d.get('name')}: {d.get('old_value', '')} → {d.get('new_value', '')}"
                for d in details
            ]

            if notes or changes:
                lines.append(f"### {author} — {date}")
                if notes:
                    lines.append(notes)
                if changes:
                    lines.extend(changes)
                lines.append("")

    return "\n".join(lines)
