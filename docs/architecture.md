# Architecture — Redmine FastMCP Server with OAuth

## Components

```
MCP Client (e.g. Claude Desktop)
        │
        │  MCP over Streamable HTTP
        │  Authorization: Bearer <fastmcp-jwt>
        ▼
┌──────────────────────────┐
│     FastMCP 3.0 Server   │
│                          │
│  OAuthProxy              │──── back-channel token exchange ────▶ Redmine OAuth
│  Token Store (encrypted) │◀─── access token + refresh token ────
│                          │
│  Tools                   │──── REST API calls ─────────────────▶ Redmine API
│                          │     Authorization: Bearer <redmine-token>
└──────────────────────────┘
```

---

## Authentication Flow

FastMCP 3.0's `OAuthProxy` is used. It bridges Redmine's OAuth 2.0 endpoints to the MCP client, handling the confidential client exchange server-side.

1. MCP client connects to FastMCP and discovers OAuth metadata via `/.well-known/oauth-authorization-server`.
2. Client redirects the user to Redmine's authorization endpoint (with auto-collected scopes, filtered by `REDMINE_SCOPES` if set).
3. After user consent, Redmine sends the authorization code to FastMCP's `/auth/callback`.
4. FastMCP performs the back-channel code exchange using `REDMINE_CLIENT_ID` + `REDMINE_CLIENT_SECRET`.
5. FastMCP stores the Redmine access token + refresh token encrypted in the token store.
6. FastMCP issues its own short-lived JWT to the MCP client.
7. **The MCP client only ever sees the FastMCP JWT — the Redmine token never leaves the server.**

For subsequent requests:
- Client sends `Authorization: Bearer <fastmcp-jwt>` with every MCP request.
- FastMCP validates the JWT, looks up the corresponding Redmine token, and injects it into Redmine API calls.
- Token refresh is handled transparently by FastMCP before each Redmine call.

**Multi-user:** Each MCP client session has its own FastMCP JWT and its own stored Redmine token. The server is multi-tenant by design.

---

## Request Flow (Tool Call)

```
Client                  FastMCP                 Redmine
  │                        │                       │
  │── MCP tool call ───────▶│                       │
  │   Bearer: <jwt>         │                       │
  │                         │ validate JWT          │
  │                         │ look up Redmine token │
  │                         │─── GET /issues ──────▶│
  │                         │    Bearer: <redmine>  │
  │                         │◀── 200 JSON ──────────│
  │◀── MCP result ──────────│                       │
```

---

## Module Design

All modules live under the `mcp_redmine_oauth` package (`src/mcp_redmine_oauth/`).

| Module | Responsibility |
|---|---|
| `server.py` | FastMCP app entry point; registers tools/resources, collects scopes, creates auth, starts server |
| `auth.py` | `RedmineProvider` (OAuthProxy subclass) + `RedmineTokenVerifier`; scope capture from token exchange |
| `scopes.py` | `@requires_scopes` decorator, scope registry, allowlist filter, `check_scope` helper |
| `client.py` | Thin async HTTP client wrapping Redmine REST API; receives Bearer token per call |
| `tools.py` | MCP tools: `get_issue_details`, `search_issues` (planned: `create_issue`, `update_issue`) |
| `resources.py` | MCP resources: `projects/active`, `trackers`, `users/me` |
| `prompts.py` | (planned) MCP prompts: `summarize_ticket`, `draft_bug_report` |

The package exposes a console entry point `mcp-redmine-oauth` (defined in `pyproject.toml`) that calls `server:main`.

Tools and resources retrieve the current session's Redmine token via FastMCP's `get_access_token()` dependency and pass it to `client.py`.

---

## Token Storage

`OAuthProxy` requires a backend to store encrypted Redmine tokens.

| Phase | Backend |
|---|---|
| Development | In-memory (default, lost on restart) |
| Production | SQLite or Redis (configured via env var) |

---

## Scope Architecture

Scopes are declared directly on each tool/resource using the `@requires_scopes` decorator:

```python
@mcp.tool()
@requires_scopes(VIEW_ISSUES, SEARCH_PROJECT)
async def search_issues(query: str) -> str: ...
```

**Scope lifecycle:**

1. **Declaration** — `@requires_scopes(...)` on each tool/resource registers scopes to a global `_registry` at decoration time.
2. **Collection** — `server.py` calls `register_tools()` / `register_resources()` first (populating `_registry`), then collects scopes via `get_effective_scopes()`.
3. **Filtering** — If `REDMINE_SCOPES` env var is set, only the intersection of declared and allowed scopes is requested. This prevents OAuth errors when the Redmine app doesn't support all declared scopes.
4. **Authorization** — Collected scopes are passed to `RedmineProvider` and sent to Redmine in the OAuth authorization URL.
5. **Capture** — `_extract_upstream_claims` captures granted scopes from Redmine's token exchange response into `scope_store`.
6. **Enforcement** — At call time, the `@requires_scopes` wrapper checks the token's granted scopes and returns a descriptive error if any are missing.

**Current scope mapping:**

| Tool / Resource | Required Scopes |
|---|---|
| `get_issue_details` | `view_issues` |
| `search_issues` | `view_issues`, `search_project` |
| `active_projects` | `view_project` |
| `trackers` | `view_project` |
| `current_user` | _(auth only)_ |

---

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDMINE_URL` | Yes | — | Base URL of the Redmine instance |
| `REDMINE_CLIENT_ID` | Yes | — | OAuth application Client ID from Redmine |
| `REDMINE_CLIENT_SECRET` | Yes | — | OAuth application Client Secret from Redmine |
| `REDMINE_SCOPES` | No | _(all declared)_ | Allowlist filter: space-separated scopes your Redmine app supports. Only the intersection of this and tool-declared scopes is requested. Omit to request all. |
| `MCP_HOST` | No | `0.0.0.0` | FastMCP bind host |
| `MCP_PORT` | No | `8000` | FastMCP bind port |
| `MCP_BASE_URL` | No | `http://localhost:MCP_PORT` | Public-facing URL for OAuth redirects |

---

## Redmine OAuth App Registration

In Redmine: **Administration → Applications → New Application**

- **Redirect URI:** `http://<MCP_HOST>:<MCP_PORT>/auth/callback`
- **Confidential client:** yes (requires Client Secret)
- **Scopes:** select the scopes your tools need (e.g. View Issues, View Projects, Search Project)
