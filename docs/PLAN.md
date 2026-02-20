# Development Plan — Redmine FastMCP Server

## Task Status Convention

| Mark | Meaning |
|---|---|
| `[ ]` | Not started |
| `[-]` | In progress |
| `[x]` | Done |
| `[!]` | Blocked |
| `[~]` | Skipped / out of scope |

---

## MVP — Core Auth + One Tool

**Goal:** A working FastMCP server where a real MCP client can authenticate via Redmine OAuth and call one tool successfully.

**Success Criteria:**
- Claude Desktop connects to the FastMCP server
- User is redirected to Redmine, logs in, and approves access
- `get_issue_details` returns real data for a given issue ID
- Auth flow works end-to-end with in-memory token store

### Project Setup
- [ ] Initialize `pyproject.toml` with dependencies: `fastmcp`, `httpx`, `python-dotenv`
- [ ] Create `src/` directory with module files
- [ ] Create `.env.example` with all required variables

### FastMCP Server
- [ ] `server.py`: Create FastMCP app instance with Streamable HTTP transport
- [ ] `server.py`: Mount `OAuthProxy` and register tools, resources, prompts

### OAuth Integration
- [ ] `auth.py`: Configure `OAuthProxy` pointing to Redmine's authorize and token endpoints
- [ ] `auth.py`: Wire in `REDMINE_CLIENT_ID`, `REDMINE_CLIENT_SECRET`, and redirect URI
- [ ] `auth.py`: Set up in-memory token store

### Redmine HTTP Client
- [ ] `client.py`: Async HTTP client using `httpx` with base URL from `REDMINE_URL`
- [ ] `client.py`: Accept Bearer token per call; set `Authorization` header automatically
- [ ] `client.py`: Raise typed errors for 401, 403, 404, 5xx responses

### First Tool
- [ ] `tools.py`: Implement `get_issue_details(issue_id)` — fetches issue with `?include=journals`
- [ ] `tools.py`: Retrieve Redmine token from session via `get_access_token()` and pass to client

---

## V1 — Full PRD Feature Set

**Goal:** All tools, resources, and prompts from the PRD are working. Error handling and context limits are in place.

**Dependencies:** MVP complete.

**Success Criteria:**
- All 4 tools, 3 resources, and 2 prompts work in Claude Desktop
- Redmine 403 errors surface as clear MCP error messages
- Large issue journal histories are truncated without crashing

### Remaining Tools
- [ ] `tools.py`: `search_issues(query, project_id?, status_id?)`
- [ ] `tools.py`: `create_issue(project_id, tracker_id, subject, description, priority_id?)`
- [ ] `tools.py`: `update_issue(issue_id, notes?, status_id?, assignee_id?)`

### Resources
- [ ] `resources.py`: `redmine://projects/active` — active projects accessible to the user
- [ ] `resources.py`: `redmine://trackers` — available trackers with IDs
- [ ] `resources.py`: `redmine://users/me` — authenticated user profile

### Prompts
- [ ] `prompts.py`: `summarize_ticket(issue_id)`
- [ ] `prompts.py`: `draft_bug_report(project_id, rough_notes)`

### Error Handling & Constraints
- [ ] Map Redmine 403 → user-facing MCP error explaining missing scope
- [ ] Truncate journal history in `get_issue_details` when entries exceed a configurable limit
- [ ] Handle Redmine API pagination for `search_issues` results

### Tests
- [ ] Unit tests for all tools with mocked `client.py`
- [ ] Unit tests for all resources with mocked `client.py`

### Documentation
- [ ] `README.md`: setup, environment variables, running the server, connecting from Claude Desktop
- [ ] `.env.example`: finalized with all variables and inline comments

---

## V2 — Production Readiness

**Goal:** Server is stable, observable, and deployable via Docker with sessions that survive restarts.

**Dependencies:** V1 complete.

**Success Criteria:**
- Restarting the server does not log out connected users
- Multiple users can connect simultaneously with fully isolated sessions
- Docker image builds and runs with only env var configuration

### Persistent Token Storage
- [ ] Implement SQLite backend for `OAuthProxy` token store
- [ ] Make backend selectable via `TOKEN_STORE_URL` env var (default: SQLite, optional: Redis)
- [ ] Test: token survives server restart

### Docker
- [ ] Write `Dockerfile` (multi-stage, non-root user)
- [ ] Write `docker-compose.yml` with env var passthrough
- [ ] Test: image builds and server is reachable from MCP client

### Observability
- [ ] Add structured logging (request in/out, OAuth events, Redmine API errors)
- [ ] Expose `/health` endpoint returning server status

### Integration Tests
- [ ] End-to-end OAuth flow test against a real (or test) Redmine instance
- [ ] Concurrent multi-user session test: two clients, isolated Redmine tokens
