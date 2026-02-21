# Redmine FastMCP Server

MCP server that bridges AI agents to a [Redmine](https://www.redmine.org/) instance via OAuth 2.0. Built with [FastMCP 3](https://github.com/jlowin/fastmcp).

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
- A running Redmine 6.1+ instance with **REST API enabled** and **OAuth enabled**
- An OAuth application registered in Redmine (see below)

## Redmine Setup

### 1. Enable the REST API

**Administration → Settings → API → Enable REST web service** (check and save).

### 2. Register an OAuth Application

**Administration → Applications → New Application**

| Field | Value |
|---|---|
| Redirect URI | `http://localhost:8000/auth/callback` |
| Confidential client | Yes |
| Scopes | Select the scopes your tools need (e.g. View Issues, View Projects) |

Copy the generated **Client ID**, **Client Secret**, and note the **scope identifiers**.

## Setup

```bash
cp .env.example .env
```

Fill in your values:

```
REDMINE_URL=http://your-redmine-host
REDMINE_CLIENT_ID=your-client-id
REDMINE_CLIENT_SECRET=your-client-secret
REDMINE_SCOPES=view_issues view_project
```

`REDMINE_SCOPES` must match the scope identifiers from your Redmine OAuth application (space-separated).

## Running

### Locally

```bash
pip install -e .
python src/server.py
```

### Docker Compose

Starts the MCP server and [MCP Inspector](https://github.com/modelcontextprotocol/inspector) together:

```bash
docker compose up
```

| Service | URL |
|---|---|
| MCP Server | `http://localhost:8000/mcp` |
| MCP Inspector UI | `http://localhost:6274` |

In the Inspector UI, set the transport to **Streamable HTTP** and enter `http://mcp-server:8000/mcp` (the Docker service name, not `localhost`).

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDMINE_URL` | Yes | — | Base URL of your Redmine instance |
| `REDMINE_CLIENT_ID` | Yes | — | OAuth app Client ID |
| `REDMINE_CLIENT_SECRET` | Yes | — | OAuth app Client Secret |
| `REDMINE_SCOPES` | No | — | Space-separated OAuth scopes to request from Redmine |
| `MCP_HOST` | No | `0.0.0.0` | Bind host |
| `MCP_PORT` | No | `8000` | Bind port |
| `MCP_BASE_URL` | No | `http://localhost:MCP_PORT` | Public-facing URL used for OAuth redirects |

## Available Tools

| Tool | Description |
|---|---|
| `get_issue_details` | Fetch a Redmine issue by ID, including description, custom fields, and full comment/journal history |

Planned: `search_issues`, `create_issue`, `update_issue`, resources (`projects`, `trackers`, `users/me`), and prompts (`summarize_ticket`, `draft_bug_report`).

## Architecture

See [docs/architecture.md](docs/architecture.md) for the detailed OAuth flow, token storage, and module design.
