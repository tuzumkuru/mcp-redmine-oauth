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
| `redmine://projects/active` | Resource | `view_project` | List active projects |
| `redmine://trackers` | Resource | `view_project` | List available trackers |
| `redmine://users/me` | Resource | _(auth only)_ | Current authenticated user profile |

Planned: `create_issue`, `update_issue`, prompts (`summarize_ticket`, `draft_bug_report`).

## Required Redmine Scopes

Enable these scopes on your Redmine OAuth application for full functionality:

| Redmine Scope | Identifier | Used By |
|---|---|---|
| View Issues | `view_issues` | `get_issue_details`, `search_issues` |
| View Projects | `view_project` | `redmine://projects/active`, `redmine://trackers` |
| Search Project | `search_project` | `search_issues` |

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
