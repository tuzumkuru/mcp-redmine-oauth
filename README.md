# mcp-redmine-oauth — Redmine FastMCP Server with OAuth

A centrally-deployed MCP server for [Redmine](https://www.redmine.org/) with OAuth 2.0 authentication. An administrator deploys it once; users connect by authorizing through Redmine — no API keys or per-user setup required. Built with [FastMCP 3](https://github.com/jlowin/fastmcp).

## How it works

```
MCP Client (Claude Desktop, MCP Inspector, …)
        │  MCP over Streamable HTTP
        │  Authorization: Bearer <fastmcp-jwt>
        ▼
┌─────────────────────────────┐
│      FastMCP 3 Server       │
│  OAuthProxy (port 8000)     │──── token exchange ────▶ Redmine OAuth
│  Token store (in-memory)    │◀─── access token ────────
│                             │
│  Tools                      │──── REST API ───────────▶ Redmine API
└─────────────────────────────┘
```

The MCP client only ever sees a FastMCP-issued JWT. The Redmine OAuth token is stored server-side and never exposed to the client.

## Prerequisites

- Python 3.11+
- A running Redmine 6.1+ instance with **REST API enabled**
- An OAuth application registered in Redmine (see below)

## Redmine Setup

### 1. Enable the REST API

**Administration → Settings → API → Enable REST web service** (check and save).

### 2. Register an OAuth Application

**Administration → Applications → New Application**

| Field | Value |
|---|---|
| Redirect URI | `http://<MCP_BASE_URL>/auth/callback` |
| Confidential client | Yes |
| Scopes | Enable all [required scopes](#required-redmine-scopes) for full functionality |

Copy the generated **Client ID**, **Client Secret**.

## Setup

```bash
git clone https://github.com/tuzumkuru/mcp-redmine-oauth.git
cd mcp-redmine-oauth
cp .env.example .env
```

Fill in your values:

```
REDMINE_URL=http://your-redmine-host
REDMINE_CLIENT_ID=your-client-id
REDMINE_CLIENT_SECRET=your-client-secret
```

## Running

```bash
pip install -e .
mcp-redmine-oauth
```

The MCP server will be available at `http://localhost:8000/mcp`.

To test with [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector
```

Open `http://localhost:6274`, set transport to **Streamable HTTP**, and enter `http://localhost:8000/mcp`.

## Running with Docker

```bash
docker compose up --build
```

The container reads configuration from `.env`. Make sure `MCP_BASE_URL` is set to the externally-reachable URL of the server (not `localhost` if clients connect from other machines).

Set `MCP_HOST_PORT` in `.env` to change the host-side port (default `8000`).

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDMINE_URL` | Yes | — | Base URL of your Redmine instance |
| `REDMINE_CLIENT_ID` | Yes | — | OAuth app Client ID |
| `REDMINE_CLIENT_SECRET` | Yes | — | OAuth app Client Secret |
| `REDMINE_SCOPES` | No | _(all declared)_ | Allowlist filter: space-separated scopes your Redmine app supports (see Scope Handling) |
| `MCP_HOST` | No | `0.0.0.0` | Bind host |
| `MCP_PORT` | No | `8000` | Bind port |
| `MCP_BASE_URL` | No | `http://localhost:MCP_PORT` | Public-facing URL used for OAuth redirects |

## Available Tools & Resources

| Component | Type | Required Scopes | Description |
|---|---|---|---|
| `get_issue_details` | Tool | `view_issues` | Fetch a Redmine issue by ID with description, custom fields, and journals |
| `search_issues` | Tool | `view_issues`, `search_project` | Full-text search across issues with pagination |
| `list_issues` | Tool | `view_issues` | List issues with filters (project, assignee, status, tracker, sort) |
| `get_issue_relations` | Tool | `view_issues` | Get issue relations (blocking, blocked-by, related, etc.) |
| `get_project_details` | Tool | `view_project` | Project details with trackers, categories, and enabled modules |
| `get_project_versions` | Tool | `view_project` | Project versions/milestones with status and due dates |
| `list_time_entries` | Tool | `view_time_entries` | List time entries with filters (project, user, date range) |
| `create_issue` | Tool | `add_issues` | Create a new issue with subject, tracker, priority, assignee, etc. |
| `update_issue` | Tool | `edit_issues` | Update an existing issue (status, assignee, notes, etc.) |
| `create_project` | Tool | `add_project` | Create a new Redmine project |
| `update_project` | Tool | `edit_project` | Update project name, description, visibility, trackers |
| `get_wiki_page` | Tool | `view_wiki_pages` | Get a wiki page from a project |
| `update_wiki_page` | Tool | `edit_wiki_pages` | Create or update a wiki page |
| `rename_wiki_page` | Tool | `rename_wiki_pages` | Rename a wiki page with optional redirect |
| `summarize_ticket` | Prompt | `view_issues` | Generate a concise summary of an issue with next steps |
| `draft_bug_report` | Prompt | `view_project` | Draft a structured bug report from rough notes |
| `redmine://projects/active` | Resource | `view_project` | List active projects |
| `redmine://trackers` | Resource | `view_project` | List available trackers |
| `redmine://issue-statuses` | Resource | `view_issues` | All issue statuses with IDs and closed flags |
| `redmine://enumerations/priorities` | Resource | `view_issues` | Issue priority levels with IDs |
| `redmine://users/me` | Resource | _(auth only)_ | Current authenticated user profile |

Planned: persistent token storage, dynamic tool disabling by scope, structured logging.

## Required Redmine Scopes

Enable these scopes on your Redmine OAuth application (**Administration → Applications**). They are grouped by the Redmine category as shown in the application settings.

### Project

| Redmine Permission | Scope Identifier | Used By |
|---|---|---|
| View projects | `view_project` | `get_project_details`, `get_project_versions`, `redmine://projects/active`, `redmine://trackers`, `draft_bug_report` |
| Search projects | `search_project` | `search_issues` |
| Create project | `add_project` | `create_project` |
| Edit project | `edit_project` | `update_project` |

### Issue tracking

| Redmine Permission | Scope Identifier | Used By |
|---|---|---|
| View Issues | `view_issues` | `get_issue_details`, `search_issues`, `list_issues`, `get_issue_relations`, `redmine://issue-statuses`, `redmine://enumerations/priorities`, `summarize_ticket` |
| Add issues | `add_issues` | `create_issue` |
| Edit issues | `edit_issues` | `update_issue` |

### Time tracking

| Redmine Permission | Scope Identifier | Used By |
|---|---|---|
| View spent time | `view_time_entries` | `list_time_entries` |

### Wiki

| Redmine Permission | Scope Identifier | Used By |
|---|---|---|
| View wiki | `view_wiki_pages` | `get_wiki_page` |
| Edit wiki pages | `edit_wiki_pages` | `update_wiki_page` |
| Rename wiki pages | `rename_wiki_pages` | `rename_wiki_page` |

If a scope is not enabled, the tools that require it will return a descriptive error at call time.

## Scope Handling

Each tool and resource declares its required OAuth scopes via the `@requires_scopes` decorator. The server **automatically collects** all declared scopes and requests them during OAuth authorization.

If your Redmine OAuth app is configured with only a subset of the scopes above, set `REDMINE_SCOPES` to avoid the error *"The requested scope is invalid, unknown, or malformed"*:

```
REDMINE_SCOPES=view_issues view_project
```

When set, only the **intersection** of tool-declared scopes and `REDMINE_SCOPES` is requested. Tools whose scopes aren't fully covered (e.g. `search_issues` needs `search_project`) will return a descriptive error at call time instead of breaking the entire OAuth flow.

When omitted, all tool-declared scopes are requested — this works when your Redmine app has all of them enabled.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the detailed OAuth flow, token storage, and module design.
