# Development Plan — Redmine FastMCP Server with OAuth

## Task Status Convention

| Mark | Meaning |
|---|---|
| `[ ]` | Not started |
| `[-]` | In progress |
| `[x]` | Done |
| `[!]` | Blocked |
| `[~]` | Skipped / out of scope |

---

## Phase 1: MVP — Core Auth + One Tool → `v0.1.0`

**Goal:** A working FastMCP server where a real MCP client can authenticate via Redmine OAuth and call one tool successfully.

**Success Criteria:**
- MCP client connects to the FastMCP server
- User is redirected to Redmine, logs in, and approves access
- `get_issue_details` returns real data for a given issue ID
- Auth flow works end-to-end with in-memory token store

### Project Setup
- [x] Initialize `pyproject.toml` with dependencies: `fastmcp`, `httpx`, `python-dotenv`
- [x] Create `src/` directory with module files
- [x] Create `.env.example` with all required variables

### FastMCP Server
- [x] `server.py`: Create FastMCP app instance with Streamable HTTP transport
- [x] `server.py`: Mount `OAuthProxy` and register tools, resources, prompts

### OAuth Integration
- [x] `auth.py`: Configure `OAuthProxy` pointing to Redmine's authorize and token endpoints
- [x] `auth.py`: Wire in `REDMINE_CLIENT_ID`, `REDMINE_CLIENT_SECRET`, and redirect URI
- [x] `auth.py`: Set up in-memory token store (OAuthProxy default)

### Redmine HTTP Client
- [x] `client.py`: Async HTTP client using `httpx` with base URL from `REDMINE_URL`
- [x] `client.py`: Accept Bearer token per call; set `Authorization` header automatically
- [x] `client.py`: Raise typed errors for 401, 403, 404, 5xx responses

### First Tool
- [x] `tools.py`: Implement `get_issue_details(issue_id)` — fetches issue with `?include=journals`
- [x] `tools.py`: Retrieve Redmine token from session via `get_access_token()` and pass to client

### Auth UX
- [x] Disable FastMCP authorization consent screen — Redmine login/consent is the real gate; the extra FastMCP screen is redundant friction for a centrally-deployed server

### Version
- [x] `pyproject.toml`: version `0.1.0` (initial)

---

## Phase 2: Containerization → `v0.2.0`

**Goal:** The MCP server runs in a Docker container with only env var configuration.

**Dependencies:** Phase 1 complete.

**Success Criteria:**
- Docker image builds from the repo
- Server is reachable from an MCP client when running in a container

### Docker
- [x] Write `Dockerfile` for the MCP server (multi-stage, non-root user)
- [x] Write `docker-compose.yml` for the MCP server only (no inspector, no Redmine — those are external)
- [x] Test: image builds and server is reachable from an MCP client

### Version
- [~] `pyproject.toml`: bump to `0.2.0` — skipped, caught up in Phase 3 bump

---

## Phase 3: Basic Tools — Read Operations → `v0.3.0`

**Goal:** All read-only tools and resources are working.

**Dependencies:** Phase 2 complete.

**Success Criteria:**
- `search_issues` returns results in Claude Desktop
- All 3 resources return correct data
- Large journal histories are truncated without crashing
- Paginated search results are handled correctly

### Tools
- [x] `tools.py`: `search_issues(query, project_id?, open_issues_only?)` — uses `/search.json` for full-text search
- [x] Truncate journal history in `get_issue_details` when entries exceed `MAX_JOURNAL_ENTRIES` (25)
- [x] Handle Redmine API pagination for `search_issues` results (offset/limit with metadata)

### Resources
- [x] `resources.py`: `redmine://projects/active` — active projects accessible to the user
- [x] `resources.py`: `redmine://trackers` — available trackers with IDs
- [x] `resources.py`: `redmine://users/me` — authenticated user profile

### Scope Architecture
- [x] `scopes.py`: `@requires_scopes(*scopes)` decorator — declares required scopes at decoration time (auto-populates registry) and enforces auth + scope at call time
- [x] `scopes.py`: `get_registered_scopes()` replaces manual `ALL_SCOPES` list — server always requests exactly what the tools need
- [x] `scopes.py`: `set_allowed_scopes()` / `get_effective_scopes()` — optional `REDMINE_SCOPES` env var filters requested scopes to what the Redmine OAuth app supports (intersection of declared and allowed)
- [x] All tools and resources declare scopes via `@requires_scopes` — no inline `check_scope()` calls in function bodies
- [x] `server.py`: register tools/resources first, auto-collect scopes via `get_effective_scopes()`, create `RedmineProvider`, then set `mcp.auth`; reads optional `REDMINE_SCOPES` env var as allowlist filter
- [x] `auth.py`: `_extract_upstream_claims` captures granted scopes from Redmine token exchange; `verify_token` sets real `AccessToken.scopes`

### Tests
- [x] Unit tests for `search_issues` with mocked `client.py`
- [x] Unit tests for all resources with mocked `client.py`
- [x] Unit tests for `requires_scopes` decorator (registry, auth guard, scope guard, passthrough)
- [x] Unit tests for `_extract_upstream_claims` scope capture in `auth.py`

### Version
- [x] `pyproject.toml`: bump to `0.3.0`

---

## Phase 4: Extended Read Operations → `v0.4.0`

**Goal:** Comprehensive read-only access to Redmine data — filtered issue queries, project details, relations, versions, and reference data.

**Dependencies:** Phase 3 complete.

**Success Criteria:**
- `list_issues` with filters returns correct results (assignee, status, tracker, project)
- `assigned_to_id=me` shortcut works for "my issues" queries
- Issue relations and project versions are accessible
- All reference data resources return valid data
- Unit tests for all new tools and resources

### Tools
- [ ] `tools.py`: `list_issues(project_id?, assigned_to_id?, status_id?, tracker_id?, sort?, offset?, limit?)` — filtered issue listing via `/issues.json`; support `assigned_to_id="me"` shortcut
- [ ] `tools.py`: `get_issue_relations(issue_id)` — blocking/blocked-by/related links via `/issues/{id}/relations.json`
- [ ] `tools.py`: `get_project_details(project_id)` — single project with categories, modules, custom fields via `/projects/{id}.json?include=trackers,issue_categories,enabled_modules`
- [ ] `tools.py`: `get_project_versions(project_id)` — milestones/releases via `/projects/{id}/versions.json`
- [ ] `tools.py`: `list_time_entries(project_id?, user_id?, from_date?, to_date?, offset?, limit?)` — time entries via `/time_entries.json`

### Resources
- [ ] `resources.py`: `redmine://issue-statuses` — all status values (New, In Progress, Closed…) via `/issue_statuses.json`
- [ ] `resources.py`: `redmine://enumerations/priorities` — priority levels (Low, Normal, High…) via `/enumerations/issue_priorities.json`

### Scopes
- [ ] `scopes.py`: add `VIEW_TIME_ENTRIES = "view_time_entries"` constant

### Tests
- [ ] Unit tests for `list_issues` with mocked filters and pagination
- [ ] Unit tests for `get_issue_relations`, `get_project_details`, `get_project_versions`
- [ ] Unit tests for `list_time_entries` with mocked date range filters
- [ ] Unit tests for new resources (`issue-statuses`, `enumerations/priorities`)

### Documentation
- [ ] Update `README.md` tools/resources table and required scopes
- [ ] Update `docs/architecture.md` scope mapping table

### Version
- [ ] `pyproject.toml`: bump to `0.4.0`

---

## Phase 5: Write Operations + Prompts → `v0.5.0`

**Goal:** Write tools and AI prompts are working end-to-end.

**Dependencies:** Phase 4 complete.

**Success Criteria:**
- `create_issue` and `update_issue` work in Claude Desktop
- Both prompts execute correctly
- Redmine 403 errors surface as clear scope-related messages

### Tools
- [ ] `tools.py`: `create_issue(project_id, tracker_id, subject, description, priority_id?)`
- [ ] `tools.py`: `update_issue(issue_id, notes?, status_id?, assignee_id?)`
- [ ] Map Redmine 403 → user-facing MCP error explaining missing scope

### Prompts
- [ ] `prompts.py`: `summarize_ticket(issue_id)`
- [ ] `prompts.py`: `draft_bug_report(project_id, rough_notes)`

### Tests
- [ ] Unit tests for `create_issue` and `update_issue` with mocked `client.py`

### Version
- [ ] `pyproject.toml`: bump to `0.6.0`

---

## Phase 6: Production Hardening → `v0.6.0`

**Goal:** Server is stable, observable, and sessions survive restarts.

**Dependencies:** Phase 5 complete.

**Success Criteria:**
- Restarting the server does not log out connected users
- Multiple users can connect simultaneously with fully isolated sessions

### Persistent Token Storage
- [ ] Implement SQLite backend for `OAuthProxy` token store (also persists `scope_store` in `auth.py`)
- [ ] Make backend selectable via `TOKEN_STORE_URL` env var (default: SQLite, optional: Redis)
- [ ] Test: token survives server restart

### Dynamic Tool Disabling by Scope
- [ ] Extend `requires_scopes` wrapper to accept injected `Context` (FastMCP dependency injection)
- [ ] On first authenticated call per session: iterate scope registry, call `disable_components(context, ...)` for tools with unmet scopes
- [ ] Client receives `ToolListChangedNotification` — tools disappear from list if scope not granted

### Observability
- [ ] Add structured logging (request in/out, OAuth events, Redmine API errors)
- [ ] Expose `/health` endpoint returning server status

### Integration Tests
- [ ] End-to-end OAuth flow test against a real (or test) Redmine instance
- [ ] Concurrent multi-user session test: two clients, isolated Redmine tokens

### Version
- [ ] `pyproject.toml`: bump to `0.6.0`

---

## Phase 7: Release → `v1.0.0`

**Goal:** Project is documented, versioned, and ready for public use.

**Dependencies:** Phase 6 complete.

**Success Criteria:**
- README covers all setup steps end-to-end
- Version is `1.0.0` and tagged in git

### Documentation
- [ ] `README.md`: finalize setup, environment variables, running, Docker, and connecting from Claude Desktop
- [ ] `.env.example`: finalized with all variables and inline comments

### Release
- [ ] Bump version to `1.0.0` in `pyproject.toml`
- [ ] Tag `v1.0.0` in git

---

## Backlog

Ideas and requests not yet assigned to a phase. Review during phase planning.

- Push repo to GitHub and migrate backlog items to Issues
- Per-client Redmine consent: Redmine auto-approves after first grant because all MCP clients share the same `REDMINE_CLIENT_ID`. Consider whether per-client consent is desirable (would require separate Redmine app registrations or a `force_reauthorize` param per client).
