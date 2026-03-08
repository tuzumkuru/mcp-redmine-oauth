"""MCP tools for Redmine issue operations."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from mcp_redmine_oauth.client import (
    RedmineClient,
    RedmineForbiddenError,
    RedmineNotFoundError,
    RedmineValidationError,
)
from mcp_redmine_oauth.scopes import (
    ADD_ISSUES,
    ADD_PROJECT,
    EDIT_ISSUES,
    EDIT_PROJECT,
    EDIT_WIKI_PAGES,
    RENAME_WIKI_PAGES,
    SEARCH_PROJECT,
    VIEW_ISSUES,
    VIEW_PROJECT,
    VIEW_TIME_ENTRIES,
    VIEW_WIKI_PAGES,
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

    # --- Write tools: Issues ---

    @mcp.tool()
    @requires_scopes(ADD_ISSUES)
    async def create_issue(
        project_id: str,
        subject: str,
        tracker_id: int | None = None,
        description: str | None = None,
        priority_id: int | None = None,
        assigned_to_id: int | None = None,
        status_id: int | None = None,
        category_id: int | None = None,
        fixed_version_id: int | None = None,
        parent_issue_id: int | None = None,
    ) -> str:
        """Create a new Redmine issue.

        Args:
            project_id: Project identifier (required).
            subject: Issue subject/title (required).
            tracker_id: Tracker ID (Bug, Feature, etc.). Use redmine://trackers to see IDs.
            description: Issue description text.
            priority_id: Priority ID. Use redmine://enumerations/priorities to see IDs.
            assigned_to_id: User ID to assign the issue to.
            status_id: Status ID. Use redmine://issue-statuses to see IDs.
            category_id: Issue category ID.
            fixed_version_id: Target version/milestone ID.
            parent_issue_id: Parent issue ID for sub-tasks.
        """
        token = get_access_token()

        issue_data: dict = {
            "project_id": project_id,
            "subject": subject,
        }
        if tracker_id is not None:
            issue_data["tracker_id"] = tracker_id
        if description is not None:
            issue_data["description"] = description
        if priority_id is not None:
            issue_data["priority_id"] = priority_id
        if assigned_to_id is not None:
            issue_data["assigned_to_id"] = assigned_to_id
        if status_id is not None:
            issue_data["status_id"] = status_id
        if category_id is not None:
            issue_data["category_id"] = category_id
        if fixed_version_id is not None:
            issue_data["fixed_version_id"] = fixed_version_id
        if parent_issue_id is not None:
            issue_data["parent_issue_id"] = parent_issue_id

        try:
            data = await redmine.post(
                "/issues.json", token=token.token, json={"issue": issue_data}
            )
        except RedmineForbiddenError:
            return "Error: you do not have permission to create issues in this project."
        except RedmineValidationError as e:
            return f"Error: validation failed — {'; '.join(e.errors) if e.errors else 'unknown error'}."
        except RedmineNotFoundError:
            return f"Error: project '{project_id}' not found in Redmine."

        return _format_created_issue(data)

    @mcp.tool()
    @requires_scopes(EDIT_ISSUES)
    async def update_issue(
        issue_id: int,
        notes: str | None = None,
        status_id: int | None = None,
        assigned_to_id: int | None = None,
        priority_id: int | None = None,
        subject: str | None = None,
        description: str | None = None,
        tracker_id: int | None = None,
        category_id: int | None = None,
        fixed_version_id: int | None = None,
    ) -> str:
        """Update an existing Redmine issue.

        Args:
            issue_id: Issue ID to update (required).
            notes: Comment to add to the issue.
            status_id: New status ID. Use redmine://issue-statuses to see IDs.
            assigned_to_id: New assignee user ID.
            priority_id: New priority ID.
            subject: New subject/title.
            description: New description.
            tracker_id: New tracker ID.
            category_id: New category ID.
            fixed_version_id: New target version/milestone ID.
        """
        token = get_access_token()

        issue_data: dict = {}
        if notes is not None:
            issue_data["notes"] = notes
        if status_id is not None:
            issue_data["status_id"] = status_id
        if assigned_to_id is not None:
            issue_data["assigned_to_id"] = assigned_to_id
        if priority_id is not None:
            issue_data["priority_id"] = priority_id
        if subject is not None:
            issue_data["subject"] = subject
        if description is not None:
            issue_data["description"] = description
        if tracker_id is not None:
            issue_data["tracker_id"] = tracker_id
        if category_id is not None:
            issue_data["category_id"] = category_id
        if fixed_version_id is not None:
            issue_data["fixed_version_id"] = fixed_version_id

        if not issue_data:
            return "Error: no fields to update. Provide at least one field to change."

        try:
            await redmine.put(
                f"/issues/{issue_id}.json", token=token.token, json={"issue": issue_data}
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to update issue #{issue_id}."
        except RedmineNotFoundError:
            return f"Error: issue #{issue_id} not found in Redmine."
        except RedmineValidationError as e:
            return f"Error: validation failed — {'; '.join(e.errors) if e.errors else 'unknown error'}."

        updated_fields = list(issue_data.keys())
        return f"Issue #{issue_id} updated successfully. Changed: {', '.join(updated_fields)}."

    # --- Write tools: Projects ---

    @mcp.tool()
    @requires_scopes(ADD_PROJECT)
    async def create_project(
        name: str,
        identifier: str,
        description: str | None = None,
        is_public: bool | None = None,
        parent_id: int | None = None,
        tracker_ids: list[int] | None = None,
    ) -> str:
        """Create a new Redmine project.

        Args:
            name: Display name for the project (required).
            identifier: URL-safe identifier, e.g. "my-project" (required, lowercase, no spaces).
            description: Project description.
            is_public: Whether the project is publicly visible.
            parent_id: Parent project ID for sub-projects.
            tracker_ids: List of tracker IDs to enable. Use redmine://trackers to see IDs.
        """
        token = get_access_token()

        project_data: dict = {
            "name": name,
            "identifier": identifier,
        }
        if description is not None:
            project_data["description"] = description
        if is_public is not None:
            project_data["is_public"] = is_public
        if parent_id is not None:
            project_data["parent_id"] = parent_id
        if tracker_ids is not None:
            project_data["tracker_ids"] = tracker_ids

        try:
            data = await redmine.post(
                "/projects.json", token=token.token, json={"project": project_data}
            )
        except RedmineForbiddenError:
            return "Error: you do not have permission to create projects."
        except RedmineValidationError as e:
            return f"Error: validation failed — {'; '.join(e.errors) if e.errors else 'unknown error'}."

        return _format_created_project(data)

    @mcp.tool()
    @requires_scopes(EDIT_PROJECT)
    async def update_project(
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        is_public: bool | None = None,
        parent_id: int | None = None,
        tracker_ids: list[int] | None = None,
    ) -> str:
        """Update an existing Redmine project.

        Args:
            project_id: Project identifier or numeric ID (required).
            name: New display name.
            description: New description.
            is_public: New visibility setting.
            parent_id: New parent project ID.
            tracker_ids: New list of tracker IDs to enable.
        """
        token = get_access_token()

        project_data: dict = {}
        if name is not None:
            project_data["name"] = name
        if description is not None:
            project_data["description"] = description
        if is_public is not None:
            project_data["is_public"] = is_public
        if parent_id is not None:
            project_data["parent_id"] = parent_id
        if tracker_ids is not None:
            project_data["tracker_ids"] = tracker_ids

        if not project_data:
            return "Error: no fields to update. Provide at least one field to change."

        try:
            await redmine.put(
                f"/projects/{project_id}.json",
                token=token.token,
                json={"project": project_data},
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to update project '{project_id}'."
        except RedmineNotFoundError:
            return f"Error: project '{project_id}' not found in Redmine."
        except RedmineValidationError as e:
            return f"Error: validation failed — {'; '.join(e.errors) if e.errors else 'unknown error'}."

        updated_fields = list(project_data.keys())
        return f"Project '{project_id}' updated successfully. Changed: {', '.join(updated_fields)}."

    # --- Wiki tools ---

    @mcp.tool()
    @requires_scopes(VIEW_WIKI_PAGES)
    async def get_wiki_page(
        project_id: str,
        page_title: str = "Wiki",
    ) -> str:
        """Get a wiki page from a Redmine project.

        Args:
            project_id: Project identifier (required).
            page_title: Wiki page title (default: "Wiki", the main page).
        """
        token = get_access_token()

        try:
            data = await redmine.get(
                f"/projects/{project_id}/wiki/{page_title}.json",
                token=token.token,
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to view wiki pages in project '{project_id}'."
        except RedmineNotFoundError:
            return f"Error: wiki page '{page_title}' not found in project '{project_id}'."

        return _format_wiki_page(data)

    @mcp.tool()
    @requires_scopes(EDIT_WIKI_PAGES)
    async def update_wiki_page(
        project_id: str,
        page_title: str,
        content: str,
        comments: str | None = None,
    ) -> str:
        """Create or update a wiki page in a Redmine project.

        Args:
            project_id: Project identifier (required).
            page_title: Wiki page title (required). Creates page if it doesn't exist.
            content: Wiki page content in Redmine textile/markdown format (required).
            comments: Edit comment describing the change.
        """
        token = get_access_token()

        wiki_data: dict = {"text": content}
        if comments is not None:
            wiki_data["comments"] = comments

        try:
            await redmine.put(
                f"/projects/{project_id}/wiki/{page_title}.json",
                token=token.token,
                json={"wiki_page": wiki_data},
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to edit wiki pages in project '{project_id}'."
        except RedmineNotFoundError:
            return f"Error: project '{project_id}' not found in Redmine."
        except RedmineValidationError as e:
            return f"Error: validation failed — {'; '.join(e.errors) if e.errors else 'unknown error'}."

        return f"Wiki page '{page_title}' in project '{project_id}' saved successfully."

    @mcp.tool()
    @requires_scopes(RENAME_WIKI_PAGES)
    async def rename_wiki_page(
        project_id: str,
        page_title: str,
        new_title: str,
        create_redirect: bool = True,
    ) -> str:
        """Rename a wiki page in a Redmine project.

        Args:
            project_id: Project identifier (required).
            page_title: Current wiki page title (required).
            new_title: New title for the page (required).
            create_redirect: Whether to create a redirect from old title (default: True).
        """
        token = get_access_token()

        # Redmine renames wiki pages via PUT with the new title in the body
        wiki_data: dict = {"title": new_title}
        if not create_redirect:
            wiki_data["redirect_existing_links"] = 0

        try:
            await redmine.put(
                f"/projects/{project_id}/wiki/{page_title}.json",
                token=token.token,
                json={"wiki_page": wiki_data},
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to rename wiki pages in project '{project_id}'."
        except RedmineNotFoundError:
            return f"Error: wiki page '{page_title}' not found in project '{project_id}'."
        except RedmineValidationError as e:
            return f"Error: validation failed — {'; '.join(e.errors) if e.errors else 'unknown error'}."

        redirect_note = " A redirect from the old title was created." if create_redirect else ""
        return f"Wiki page renamed from '{page_title}' to '{new_title}' in project '{project_id}'.{redirect_note}"


def _format_created_issue(data: dict) -> str:
    """Format the response from creating an issue."""
    issue = data.get("issue", {})
    if not issue:
        return "Issue created but response was empty."
    iid = issue.get("id", "?")
    subject = issue.get("subject", "")
    project = issue.get("project", {}).get("name", "")
    return f"Issue #{iid} created successfully in project '{project}': {subject}"


def _format_created_project(data: dict) -> str:
    """Format the response from creating a project."""
    project = data.get("project", {})
    if not project:
        return "Project created but response was empty."
    name = project.get("name", "")
    identifier = project.get("identifier", "")
    pid = project.get("id", "?")
    return f"Project '{name}' (identifier: {identifier}, id={pid}) created successfully."


def _format_wiki_page(data: dict) -> str:
    """Format a wiki page response into readable text."""
    page = data.get("wiki_page", {})
    if not page:
        return "Error: could not retrieve wiki page."

    title = page.get("title", "Untitled")
    version = page.get("version", "?")
    author = page.get("author", {}).get("name", "Unknown")
    updated_on = page.get("updated_on", "N/A")
    text = page.get("text", "")

    lines = [
        f"# {title}",
        "",
        f"**Version:** {version} | **Author:** {author} | **Updated:** {updated_on}",
        "",
    ]
    if text:
        lines.append(text)
    else:
        lines.append("_(empty page)_")

    return "\n".join(lines)


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
