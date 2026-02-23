"""MCP tools for Redmine issue operations."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from mcp_redmine_oauth.client import RedmineClient, RedmineForbiddenError, RedmineNotFoundError
from mcp_redmine_oauth.scopes import SEARCH_PROJECT, VIEW_ISSUES, requires_scopes

MAX_JOURNAL_ENTRIES = 25


def register_tools(mcp: FastMCP, redmine: RedmineClient) -> None:
    """Register all Redmine tools on the FastMCP server."""

    @mcp.tool()
    @requires_scopes(VIEW_ISSUES)
    async def get_issue_details(issue_id: int) -> str:
        """Fetch full Redmine issue details including description, custom fields,
        and complete journal/comment history.
        """
        token = get_access_token()

        try:
            data = await redmine.get(
                f"/issues/{issue_id}.json",
                token=token.token,
                params={"include": "journals"},
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to view issue #{issue_id}."
        except RedmineNotFoundError:
            return f"Error: issue #{issue_id} not found in Redmine."

        issue = data.get("issue", {})
        return _format_issue(issue)

    @mcp.tool()
    @requires_scopes(VIEW_ISSUES, SEARCH_PROJECT)
    async def search_issues(
        query: str,
        project_id: str | None = None,
        open_issues_only: bool = True,
        offset: int = 0,
        limit: int = 25,
    ) -> str:
        """Search Redmine issues by full-text query. Searches titles and descriptions.

        Args:
            query: Search terms (space-separated, all must match).
            project_id: Optional project identifier to scope the search.
            open_issues_only: If True (default), only return open issues.
            offset: Number of results to skip (for pagination).
            limit: Maximum number of results to return (default 25).
        """
        token = get_access_token()

        params: dict[str, str | int] = {
            "q": query,
            "issues": 1,
            "offset": offset,
            "limit": limit,
        }
        if open_issues_only:
            params["open_issues"] = 1

        path = "/search.json"
        if project_id:
            path = f"/projects/{project_id}/search.json"

        try:
            data = await redmine.get(path, token=token.token, params=params)
        except RedmineForbiddenError:
            return "Error: you do not have permission to search in this project."
        except RedmineNotFoundError:
            return f"Error: project '{project_id}' not found in Redmine."

        return _format_search_results(data)


def _format_search_results(data: dict) -> str:
    """Format Redmine search API response into readable text."""
    results = data.get("results", [])
    total_count = data.get("total_count", 0)
    offset = data.get("offset", 0)
    limit = data.get("limit", 25)

    if not results:
        return "No issues found matching the query."

    lines = [f"Found {total_count} result(s). Showing {offset + 1}–{offset + len(results)}:", ""]

    for i, r in enumerate(results, start=offset + 1):
        title = r.get("title", "No title")
        url = r.get("url", "")
        date = r.get("datetime", "")[:10]
        description = r.get("description", "")
        lines.append(f"{i}. **{title}**")
        if date:
            lines.append(f"   Date: {date}")
        if url:
            lines.append(f"   URL: {url}")
        if description:
            # Truncate long descriptions
            desc = description[:200] + "…" if len(description) > 200 else description
            lines.append(f"   {desc}")
        lines.append("")

    if offset + len(results) < total_count:
        lines.append(
            f"_More results available. Use offset={offset + limit} to see the next page._"
        )

    return "\n".join(lines)


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
        total_journals = len(journals)
        truncated = journals[:MAX_JOURNAL_ENTRIES]

        lines.append("## Journal / Comments")
        for entry in truncated:
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

        if total_journals > MAX_JOURNAL_ENTRIES:
            lines.append(
                f"_... and {total_journals - MAX_JOURNAL_ENTRIES} more entries (truncated)._"
            )

    return "\n".join(lines)
