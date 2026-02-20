# Architecture — Redmine FastMCP Server

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
│  Tools / Resources /     │──── REST API calls ─────────────────▶ Redmine API
│  Prompts                 │     Authorization: Bearer <redmine-token>
└──────────────────────────┘
```

---

## Authentication Flow

FastMCP 3.0's `OAuthProxy` is used. It bridges Redmine's OAuth 2.0 endpoints to the MCP client, handling the confidential client exchange server-side.

1. MCP client connects to FastMCP and discovers OAuth metadata via `/.well-known/oauth-authorization-server`.
2. Client redirects the user to Redmine's authorization endpoint.
3. After user consent, Redmine sends the authorization code to FastMCP's `/oauth/callback`.
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

| Module | Responsibility |
|---|---|
| `server.py` | FastMCP app entry point; mounts `OAuthProxy`, registers tools/resources/prompts |
| `auth.py` | `OAuthProxy` configuration; Redmine OAuth endpoints; token store setup |
| `client.py` | Thin async HTTP client wrapping Redmine REST API; receives Bearer token per call |
| `tools.py` | MCP tools: `search_issues`, `get_issue_details`, `create_issue`, `update_issue` |
| `resources.py` | MCP resources: `projects/active`, `trackers`, `users/me` |
| `prompts.py` | MCP prompts: `summarize_ticket`, `draft_bug_report` |

Tools and resources retrieve the current session's Redmine token via FastMCP's `get_access_token()` dependency and pass it to `client.py`.

---

## Token Storage

`OAuthProxy` requires a backend to store encrypted Redmine tokens.

| Phase | Backend |
|---|---|
| Development | In-memory (default, lost on restart) |
| Production | SQLite or Redis (configured via env var) |

---

## Configuration

| Variable | Description |
|---|---|
| `REDMINE_URL` | Base URL of the Redmine instance |
| `REDMINE_CLIENT_ID` | OAuth application Client ID from Redmine |
| `REDMINE_CLIENT_SECRET` | OAuth application Client Secret from Redmine |
| `MCP_HOST` | FastMCP bind host (default: `0.0.0.0`) |
| `MCP_PORT` | FastMCP bind port (default: `8000`) |
| `JWT_SIGNING_KEY` | Secret for signing FastMCP-issued JWTs |
| `TOKEN_STORE_URL` | Storage backend URL (optional; defaults to in-memory) |

---

## Redmine OAuth App Registration

In Redmine: **Administration → Applications → New Application**

- **Redirect URI:** `http://<MCP_HOST>:<MCP_PORT>/oauth/callback`
- **Confidential client:** yes (requires Client Secret)
- **Scopes:** as supported by your Redmine instance
