"""MCP tools for Redmine issue operations."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from mcp_redmine_oauth.client import RedmineClient, RedmineForbiddenError, RedmineNotFoundError
from mcp_redmine_oauth.scopes import (
    SEARCH_PROJECT,
    VIEW_ISSUES,
    VIEW_PROJECT,
    VIEW_TIME_ENTRIES,
    requires_scopes,
)

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

    @mcp.tool()
    @requires_scopes(VIEW_ISSUES)
    async def list_issues(
        project_id: str | None = None,
        assigned_to_id: str | None = None,
        status_id: str | None = None,
        tracker_id: int | None = None,
        sort: str | None = None,
        offset: int = 0,
        limit: int = 25,
    ) -> str:
        """List Redmine issues with optional filters.

        Args:
            project_id: Project identifier to scope results.
            assigned_to_id: User ID, or "me" for the current user's issues.
            status_id: Status ID, "open", "closed", or "*" for all.
            tracker_id: Tracker ID to filter by.
            sort: Sort field and direction, e.g. "updated_on:desc", "priority:asc".
            offset: Number of results to skip (for pagination).
            limit: Maximum number of results to return (default 25).
        """
        token = get_access_token()

        params: dict[str, str | int] = {"offset": offset, "limit": limit}
        if project_id:
            params["project_id"] = project_id
        if assigned_to_id:
            params["assigned_to_id"] = assigned_to_id
        if status_id:
            params["status_id"] = status_id
        if tracker_id is not None:
            params["tracker_id"] = tracker_id
        if sort:
            params["sort"] = sort

        try:
            data = await redmine.get("/issues.json", token=token.token, params=params)
        except RedmineForbiddenError:
            return "Error: you do not have permission to list issues."

        return _format_issue_list(data)

    @mcp.tool()
    @requires_scopes(VIEW_ISSUES)
    async def get_issue_relations(issue_id: int) -> str:
        """Get relations for a Redmine issue (blocking, blocked-by, related, etc.).

        Args:
            issue_id: The issue ID to get relations for.
        """
        token = get_access_token()

        try:
            data = await redmine.get(
                f"/issues/{issue_id}/relations.json", token=token.token
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to view issue #{issue_id} relations."
        except RedmineNotFoundError:
            return f"Error: issue #{issue_id} not found in Redmine."

        return _format_relations(issue_id, data)

    @mcp.tool()
    @requires_scopes(VIEW_PROJECT)
    async def get_project_details(project_id: str) -> str:
        """Get detailed information about a Redmine project including trackers,
        issue categories, and enabled modules.

        Args:
            project_id: Project identifier or numeric ID.
        """
        token = get_access_token()

        try:
            data = await redmine.get(
                f"/projects/{project_id}.json",
                token=token.token,
                params={"include": "trackers,issue_categories,enabled_modules"},
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to view project '{project_id}'."
        except RedmineNotFoundError:
            return f"Error: project '{project_id}' not found in Redmine."

        return _format_project(data)

    @mcp.tool()
    @requires_scopes(VIEW_PROJECT)
    async def get_project_versions(project_id: str) -> str:
        """Get versions (milestones/releases) for a Redmine project.

        Args:
            project_id: Project identifier or numeric ID.
        """
        token = get_access_token()

        try:
            data = await redmine.get(
                f"/projects/{project_id}/versions.json", token=token.token
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to view project '{project_id}' versions."
        except RedmineNotFoundError:
            return f"Error: project '{project_id}' not found in Redmine."

        return _format_versions(project_id, data)

    @mcp.tool()
    @requires_scopes(VIEW_TIME_ENTRIES)
    async def list_time_entries(
        project_id: str | None = None,
        user_id: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        offset: int = 0,
        limit: int = 25,
    ) -> str:
        """List time entries with optional filters.

        Args:
            project_id: Project identifier to scope results.
            user_id: User ID, or "me" for the current user's entries.
            from_date: Start date filter (YYYY-MM-DD).
            to_date: End date filter (YYYY-MM-DD).
            offset: Number of results to skip (for pagination).
            limit: Maximum number of results to return (default 25).
        """
        token = get_access_token()

        params: dict[str, str | int] = {"offset": offset, "limit": limit}
        if project_id:
            params["project_id"] = project_id
        if user_id:
            params["user_id"] = user_id
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        try:
            data = await redmine.get(
                "/time_entries.json", token=token.token, params=params
            )
        except RedmineForbiddenError:
            return "Error: you do not have permission to view time entries."

        return _format_time_entries(data)


def _format_issue_list(data: dict) -> str:
    """Format Redmine issue listing response into readable text."""
    issues = data.get("issues", [])
    total_count = data.get("total_count", 0)
    offset = data.get("offset", 0)
    limit = data.get("limit", 25)

    if not issues:
        return "No issues found matching the filters."

    lines = [f"Found {total_count} issue(s). Showing {offset + 1}–{offset + len(issues)}:", ""]

    for issue in issues:
        iid = issue.get("id", "?")
        subject = issue.get("subject", "No subject")
        status = issue.get("status", {}).get("name", "")
        priority = issue.get("priority", {}).get("name", "")
        assignee = issue.get("assigned_to", {}).get("name", "Unassigned")
        updated = issue.get("updated_on", "")[:10]

        lines.append(f"- **#{iid}** {subject}")
        parts = []
        if status:
            parts.append(f"Status: {status}")
        if priority:
            parts.append(f"Priority: {priority}")
        parts.append(f"Assigned: {assignee}")
        if updated:
            parts.append(f"Updated: {updated}")
        lines.append(f"  {' | '.join(parts)}")

    if offset + len(issues) < total_count:
        lines.append("")
        lines.append(
            f"_More results available. Use offset={offset + limit} to see the next page._"
        )

    return "\n".join(lines)


def _format_relations(issue_id: int, data: dict) -> str:
    """Format issue relations into readable text."""
    relations = data.get("relations", [])
    if not relations:
        return f"Issue #{issue_id} has no relations."

    lines = [f"# Relations for Issue #{issue_id}", ""]
    for r in relations:
        rel_type = r.get("relation_type", "related")
        issue_from = r.get("issue_id", "?")
        issue_to = r.get("issue_to_id", "?")
        delay = r.get("delay")

        if issue_from == issue_id:
            lines.append(f"- **{rel_type}** → #{issue_to}")
        else:
            lines.append(f"- **{rel_type}** ← #{issue_from}")
        if delay:
            lines.append(f"  Delay: {delay} day(s)")

    return "\n".join(lines)


def _format_project(data: dict) -> str:
    """Format a single project with includes into readable text."""
    project = data.get("project", {})
    if not project:
        return "Error: could not retrieve project details."

    lines = [
        f"# {project.get('name', 'Unnamed')}",
        "",
        f"**Identifier:** {project.get('identifier', 'N/A')}",
        f"**ID:** {project.get('id', 'N/A')}",
        f"**Status:** {'active' if project.get('status') == 1 else 'closed/archived'}",
        f"**Created:** {project.get('created_on', 'N/A')}",
        f"**Updated:** {project.get('updated_on', 'N/A')}",
    ]

    homepage = project.get("homepage")
    if homepage:
        lines.append(f"**Homepage:** {homepage}")

    description = project.get("description", "")
    if description:
        lines.append("")
        lines.append(description)

    # Trackers
    trackers = project.get("trackers", [])
    if trackers:
        lines.append("")
        lines.append("## Trackers")
        for t in trackers:
            lines.append(f"- {t.get('name', 'Unnamed')} (id={t.get('id')})")

    # Issue categories
    categories = project.get("issue_categories", [])
    if categories:
        lines.append("")
        lines.append("## Issue Categories")
        for c in categories:
            lines.append(f"- {c.get('name', 'Unnamed')} (id={c.get('id')})")

    # Enabled modules
    modules = project.get("enabled_modules", [])
    if modules:
        lines.append("")
        lines.append("## Enabled Modules")
        for m in modules:
            lines.append(f"- {m.get('name', 'unknown')}")

    return "\n".join(lines)


def _format_versions(project_id: str, data: dict) -> str:
    """Format project versions into readable text."""
    versions = data.get("versions", [])
    if not versions:
        return f"No versions found for project '{project_id}'."

    lines = [f"# Versions for '{project_id}'", ""]
    for v in versions:
        name = v.get("name", "Unnamed")
        status = v.get("status", "N/A")
        due_date = v.get("due_date", "No due date")
        sharing = v.get("sharing", "none")
        description = v.get("description", "")

        lines.append(f"- **{name}** (id={v.get('id')}, status: {status})")
        lines.append(f"  Due: {due_date} | Sharing: {sharing}")
        if description:
            short = description[:120] + "…" if len(description) > 120 else description
            lines.append(f"  {short}")

    return "\n".join(lines)


def _format_time_entries(data: dict) -> str:
    """Format time entries listing into readable text."""
    entries = data.get("time_entries", [])
    total_count = data.get("total_count", 0)
    offset = data.get("offset", 0)
    limit = data.get("limit", 25)

    if not entries:
        return "No time entries found."

    total_hours = sum(e.get("hours", 0) for e in entries)
    lines = [
        f"Found {total_count} time entry/entries. "
        f"Showing {offset + 1}–{offset + len(entries)} "
        f"({total_hours:.2f} hours on this page):",
        "",
    ]

    for e in entries:
        user = e.get("user", {}).get("name", "Unknown")
        project = e.get("project", {}).get("name", "")
        issue = e.get("issue", {}).get("id")
        hours = e.get("hours", 0)
        activity = e.get("activity", {}).get("name", "")
        spent_on = e.get("spent_on", "")
        comments = e.get("comments", "")

        issue_ref = f" (issue #{issue})" if issue else ""
        lines.append(f"- **{hours:.2f}h** — {user} on {spent_on}{issue_ref}")
        parts = []
        if project:
            parts.append(f"Project: {project}")
        if activity:
            parts.append(f"Activity: {activity}")
        if parts:
            lines.append(f"  {' | '.join(parts)}")
        if comments:
            short = comments[:120] + "…" if len(comments) > 120 else comments
            lines.append(f"  \"{short}\"")

    if offset + len(entries) < total_count:
        lines.append("")
        lines.append(
            f"_More results available. Use offset={offset + limit} to see the next page._"
        )

    return "\n".join(lines)


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
