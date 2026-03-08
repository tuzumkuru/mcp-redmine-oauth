"""MCP prompts for Redmine — reusable prompt templates for common workflows."""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from mcp_redmine_oauth.client import RedmineClient, RedmineForbiddenError, RedmineNotFoundError
from mcp_redmine_oauth.scopes import VIEW_ISSUES, VIEW_PROJECT, requires_scopes


def register_prompts(mcp: FastMCP, redmine: RedmineClient) -> None:
    """Register all Redmine prompts on the FastMCP server."""

    @mcp.prompt()
    @requires_scopes(VIEW_ISSUES)
    async def summarize_ticket(issue_id: int) -> str:
        """Generate a concise summary of a Redmine issue including status, key
        discussion points, and next steps.

        Args:
            issue_id: The Redmine issue ID to summarize.
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
        subject = issue.get("subject", "No subject")
        status = issue.get("status", {}).get("name", "N/A")
        priority = issue.get("priority", {}).get("name", "N/A")
        assignee = issue.get("assigned_to", {}).get("name", "Unassigned")
        description = issue.get("description", "")
        journals = issue.get("journals", [])

        # Build context for the LLM
        journal_notes = []
        for j in journals[-15:]:  # Last 15 entries for context
            notes = j.get("notes", "")
            if notes:
                author = j.get("user", {}).get("name", "Unknown")
                journal_notes.append(f"- {author}: {notes}")

        prompt = f"""Please summarize the following Redmine issue concisely.

**Issue #{issue_id}: {subject}**
- Status: {status}
- Priority: {priority}
- Assigned to: {assignee}

**Description:**
{description or '(no description)'}

**Recent discussion ({len(journal_notes)} comments):**
{chr(10).join(journal_notes) if journal_notes else '(no comments)'}

Provide:
1. A one-paragraph summary of what this issue is about
2. Current status and blockers (if any)
3. Suggested next steps"""

        return prompt

    @mcp.prompt()
    @requires_scopes(VIEW_PROJECT)
    async def draft_bug_report(project_id: str, rough_notes: str) -> str:
        """Draft a structured bug report from rough notes, using the project's
        available trackers and priorities.

        Args:
            project_id: The project identifier where the bug will be filed.
            rough_notes: Rough description of the bug — symptoms, steps, context.
        """
        token = get_access_token()

        # Fetch project details for context (trackers, categories)
        try:
            project_data = await redmine.get(
                f"/projects/{project_id}.json",
                token=token.token,
                params={"include": "trackers,issue_categories"},
            )
        except RedmineForbiddenError:
            return f"Error: you do not have permission to view project '{project_id}'."
        except RedmineNotFoundError:
            return f"Error: project '{project_id}' not found in Redmine."

        project = project_data.get("project", {})
        project_name = project.get("name", project_id)
        trackers = project.get("trackers", [])
        categories = project.get("issue_categories", [])

        tracker_list = ", ".join(
            f"{t['name']} (id={t['id']})" for t in trackers
        ) or "N/A"
        category_list = ", ".join(
            f"{c['name']} (id={c['id']})" for c in categories
        ) or "N/A"

        prompt = f"""Please draft a structured bug report for project "{project_name}" based on the rough notes below.

**Available trackers:** {tracker_list}
**Available categories:** {category_list}

**Rough notes:**
{rough_notes}

Please produce:
1. **Subject** — a clear, concise one-line title
2. **Tracker** — suggest which tracker to use (with ID)
3. **Priority** — suggest a priority level (Low/Normal/High/Urgent/Immediate)
4. **Description** — a well-structured bug report with:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment details (if inferable from notes)
5. **Category** — suggest a category if applicable (with ID)

Format the output so it can be directly used with the `create_issue` tool."""

        return prompt
