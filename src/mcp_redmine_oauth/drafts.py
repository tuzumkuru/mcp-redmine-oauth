"""Draft tools: links to a Redmine form filled in with proposed values.

Nothing is written to Redmine. The user opens the link, reviews the form and
submits it, and Redmine saves the change as that user (docs/decisions.md DR-003).
Redmine's new-issue, edit-issue and new-project pages fill the form from
``issue[...]`` / ``project[...]`` values in the query string and save nothing
until the form is submitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote, urlencode

from fastmcp import FastMCP

from mcp_redmine_oauth.scopes import requires_scopes

# Many web servers and proxies reject a request line longer than 8 KB (nginx's
# default large_client_header_buffers is 4 x 8k), so links stay below that.
MAX_LINK_LENGTH = 8000

NOTHING_SAVED = (
    "Nothing has been saved. Show this link to the user: it opens the Redmine form "
    "with these values filled in, and the change is made only when they submit it."
)

CustomFields = dict[str, str | list[str]]


class DraftTooLongError(ValueError):
    """The link is too long even with the long text fields left out."""


@dataclass(frozen=True)
class Draft:
    """A prefilled form link, plus any text that had to be left out of it."""

    url: str
    left_out: dict[str, str] = field(default_factory=dict)


def build_draft(
    base_url: str,
    path: str,
    params: list[tuple[str, str]],
    long_fields: dict[str, str],
) -> Draft:
    """Build a form link, leaving out long text fields if the link is too long.

    Args:
        base_url: Public Redmine URL, without a trailing slash.
        path: Form path, e.g. ``/issues/42/edit``.
        params: Query parameters in form order.
        long_fields: Parameter key → label for fields that may be left out
            (description, notes), longest first when needed.
    """
    url = _link(base_url, path, params)
    if len(url) <= MAX_LINK_LENGTH:
        return Draft(url)

    kept = list(params)
    left_out: dict[str, str] = {}
    present = {key: value for key, value in params if key in long_fields}
    for key in sorted(present, key=lambda k: len(present[k]), reverse=True):
        kept = [(k, v) for k, v in kept if k != key]
        left_out[long_fields[key]] = present[key]
        url = _link(base_url, path, kept)
        if len(url) <= MAX_LINK_LENGTH:
            return Draft(url, left_out)

    raise DraftTooLongError(
        f"The link would be {len(url)} characters, over the {MAX_LINK_LENGTH} limit, "
        "even without the long text fields. Shorten the subject or the custom field values."
    )


def issue_params(fields: dict[str, object], custom_fields: CustomFields | None) -> list[tuple[str, str]]:
    """Turn issue fields into ``issue[...]`` query parameters, skipping ``None``.

    An empty string is kept: it clears that field in the form.
    """
    params = [(f"issue[{name}]", str(value)) for name, value in fields.items() if value is not None]
    for field_id, value in (custom_fields or {}).items():
        key = f"issue[custom_field_values][{field_id}]"
        if isinstance(value, list):
            params.extend((f"{key}[]", str(item)) for item in value)
        else:
            params.append((key, str(value)))
    return params


def format_draft(title: str, draft: Draft, current_page: str | None = None) -> str:
    """Render a draft as the tool result for the model.

    ``current_page`` links the record as it is now, because the prefilled form
    shows neither its history nor the values being replaced.
    """
    lines = [f"Draft: {title}", "", draft.url, "", NOTHING_SAVED]
    if current_page:
        lines += ["", f"Current state and history: {current_page}"]
    if draft.left_out:
        lines += [
            "",
            "The link would have been too long, so this text was left out of the form. "
            "Give it to the user to paste into the named field before submitting:",
        ]
        for label, text in draft.left_out.items():
            lines += ["", f"### {label}", text]
    return "\n".join(lines)


def register_draft_tools(mcp: FastMCP, redmine_public_url: str) -> None:
    """Register the draft tools. They need a login but no Redmine scope."""
    base_url = redmine_public_url.rstrip("/")

    @mcp.tool()
    @requires_scopes()
    async def draft_new_issue(
        project_id: str,
        subject: str,
        tracker_id: int | None = None,
        description: str | None = None,
        priority_id: int | None = None,
        assigned_to_id: int | str | None = None,
        category_id: int | None = None,
        fixed_version_id: int | None = None,
        parent_issue_id: int | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        custom_fields: CustomFields | None = None,
    ) -> str:
        """Propose a new Redmine issue as a link to the new-issue form, filled in.

        Nothing is saved: the user reviews the form and creates the issue. Use this
        instead of create_issue when the user should decide. Show the returned link
        to the user. Keep long text short: a link longer than about 8,000 characters
        fails, so text that does not fit is returned separately for the user to paste.

        Args:
            project_id: Project identifier or ID.
            subject: Issue subject.
            tracker_id: Tracker ID (see redmine://trackers).
            description: Issue description.
            priority_id: Priority ID (see redmine://enumerations/priorities).
            assigned_to_id: User ID, or "me" for the user opening the link.
            category_id: Issue category ID.
            fixed_version_id: Target version ID.
            parent_issue_id: Parent issue ID.
            start_date: Start date, YYYY-MM-DD.
            due_date: Due date, YYYY-MM-DD.
            custom_fields: Custom field ID → value, or a list of values for a
                multi-value field.
        """
        params = issue_params(
            {
                "tracker_id": tracker_id,
                "subject": subject,
                "description": description,
                "priority_id": priority_id,
                "assigned_to_id": assigned_to_id,
                "category_id": category_id,
                "fixed_version_id": fixed_version_id,
                "parent_issue_id": parent_issue_id,
                "start_date": start_date,
                "due_date": due_date,
            },
            custom_fields,
        )
        path = f"/projects/{quote(str(project_id), safe='')}/issues/new"
        return _draft_result(
            f"new issue in project {project_id}",
            base_url,
            path,
            params,
            {"issue[description]": "Description"},
        )

    @mcp.tool()
    @requires_scopes()
    async def draft_issue_update(
        issue_id: int,
        notes: str | None = None,
        status_id: int | None = None,
        assigned_to_id: int | str | None = None,
        priority_id: int | None = None,
        subject: str | None = None,
        description: str | None = None,
        tracker_id: int | None = None,
        category_id: int | None = None,
        fixed_version_id: int | None = None,
        parent_issue_id: int | None = None,
        start_date: str | None = None,
        due_date: str | None = None,
        done_ratio: int | None = None,
        custom_fields: CustomFields | None = None,
    ) -> str:
        """Propose a change to a Redmine issue as a link to its edit form, filled in.

        Nothing is saved: the user reviews the form and submits it. Use this instead
        of update_issue when the user should decide. Pass only the fields to change;
        an empty string clears a field. Show the returned link to the user, and list
        each change as old value → new value, because the form shows only the new
        values. The result also links the issue page, with its current description
        and history. Keep long text short: a link longer than about 8,000 characters
        fails, so text that does not fit is returned separately for the user to paste.

        Args:
            issue_id: Issue ID.
            notes: Comment to add.
            status_id: New status ID (see redmine://issue-statuses).
            assigned_to_id: User ID, or "me" for the user opening the link.
            priority_id: Priority ID (see redmine://enumerations/priorities).
            subject: New subject.
            description: New description; replaces the current one.
            tracker_id: Tracker ID (see redmine://trackers).
            category_id: Issue category ID.
            fixed_version_id: Target version ID.
            parent_issue_id: Parent issue ID.
            start_date: Start date, YYYY-MM-DD.
            due_date: Due date, YYYY-MM-DD.
            done_ratio: Percent done, 0 to 100 in steps of 10.
            custom_fields: Custom field ID → value, or a list of values for a
                multi-value field.
        """
        params = issue_params(
            {
                "tracker_id": tracker_id,
                "subject": subject,
                "description": description,
                "status_id": status_id,
                "priority_id": priority_id,
                "assigned_to_id": assigned_to_id,
                "category_id": category_id,
                "fixed_version_id": fixed_version_id,
                "parent_issue_id": parent_issue_id,
                "start_date": start_date,
                "due_date": due_date,
                "done_ratio": done_ratio,
                "notes": notes,
            },
            custom_fields,
        )
        return _draft_result(
            f"change to issue #{issue_id}",
            base_url,
            f"/issues/{int(issue_id)}/edit",
            params,
            {"issue[description]": "Description", "issue[notes]": "Notes"},
            current_page=f"{base_url}/issues/{int(issue_id)}",
        )

    @mcp.tool()
    @requires_scopes()
    async def draft_new_project(
        name: str,
        identifier: str | None = None,
        description: str | None = None,
        is_public: bool | None = None,
        parent_id: int | None = None,
    ) -> str:
        """Propose a new Redmine project as a link to the new-project form, filled in.

        Nothing is saved: the user reviews the form and creates the project. Use this
        instead of create_project when the user should decide. Show the returned link
        to the user. The link works only for users allowed to add projects, or
        subprojects of the parent; others get an error from Redmine. Redmine has no
        prefilled form for changing a project's settings, so there is no draft tool
        for that.

        Args:
            name: Project name.
            identifier: Project identifier (lower case letters, digits, dashes).
            description: Project description.
            is_public: Whether the project is public.
            parent_id: Parent project ID.
        """
        values: dict[str, object] = {
            "name": name,
            "identifier": identifier,
            "description": description,
            "is_public": None if is_public is None else int(is_public),
            "parent_id": parent_id,
        }
        params = [(f"project[{key}]", str(value)) for key, value in values.items() if value is not None]
        return _draft_result(
            f"new project {name}",
            base_url,
            "/projects/new",
            params,
            {"project[description]": "Description"},
        )


def _draft_result(
    title: str,
    base_url: str,
    path: str,
    params: list[tuple[str, str]],
    long_fields: dict[str, str],
    current_page: str | None = None,
) -> str:
    try:
        draft = build_draft(base_url, path, params, long_fields)
    except DraftTooLongError as err:
        return f"Error: {err}"
    return format_draft(title, draft, current_page)


def _link(base_url: str, path: str, params: list[tuple[str, str]]) -> str:
    if not params:
        return f"{base_url}{path}"
    # Brackets are encoded too: some terminals and Markdown renderers end a link at "[" or "]"
    query = urlencode(params, quote_via=quote, safe="")
    return f"{base_url}{path}?{query}"
