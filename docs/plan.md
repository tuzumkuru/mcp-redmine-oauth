# Development Plan — Redmine FastMCP Server with OAuth

Progress: `[ ]` not started · `[-]` in progress · `[x]` done · `[!]` blocked · `[~]` skipped

Work is split into **work packages** (`WP-NN`). A work package's ID is given when it is created and never changes or gets reused; it says nothing about order. **Priority is the position in this file**: *Now* is being worked on, *Next* is agreed and in order, *Later* is wanted but not ordered. Reprioritising means moving a block. A work package that changes the server ends with a release; the version number is set at release time. Refer to a work package by ID and name, e.g. "WP-08 (Hardening)". Decisions are in [decisions.md](decisions.md), risks in [risks.md](risks.md).

---

## Done

| WP | Name | Released | What shipped |
|---|---|---|---|
| WP-01 | MVP: core auth and one tool | v0.1.0 | FastMCP server with Streamable HTTP, `OAuthProxy` to Redmine, async Redmine client, `get_issue_details` |
| WP-02 | Containerization | in v0.3.0 | Multi-stage Dockerfile with a non-root user, docker compose |
| WP-03 | Read operations | v0.3.0 | `search_issues`, 3 resources, journal truncation, pagination, the `@requires_scopes` scope registry |
| WP-04 | Extended read operations | v0.4.0 | `list_issues`, relations, project details and versions, time entries, 2 more resources |
| WP-05 | Write operations and prompts | v0.5.0 | Issue, project and wiki write tools; `summarize_ticket` and `draft_bug_report` prompts |
| WP-06 | Claude Code login fix | v0.5.1 | Require `fastmcp>=3.4.8`: FastMCP before 3.2.0 rejected Claude Code's loopback callback on a random port (DR-001, [report](reports/2026-10-05-review.md)) |

---

# Now

## WP-13: Draft tools

**Release:** next minor version.

**Goal:** Agents propose changes as links to a Redmine form filled with the proposed values; the user reviews and submits, and Redmine saves it as the user (DR-003). Moved to the front by the maintainer on 2026-10-13.

### Tasks
- [ ] `draft_new_issue`: link to `/projects/<project>/issues/new` with `issue[...]` values (tracker, subject, description, priority, assignee, category, version, parent, dates, custom fields)
- [ ] `draft_issue_update`: link to `/issues/<id>/edit` with the changed `issue[...]` values and `issue[notes]`
- [ ] Links use Redmine's public URL; read scopes only
- [ ] Tool descriptions tell the agent to show the link to the user and that nothing is saved until the user submits
- [ ] Link length: the descriptions give the URL length limit and ask for short text. When a link would exceed it, the tool returns a warning with the text that did not fit, for the user to paste, instead of a link that fails
- [ ] Check whether Redmine's project form also takes values from the link; if so, add `draft_new_project` and `draft_project_update`
- [ ] Unit tests for every link tool; check the links by hand against a real Redmine form
- [ ] Minimal CI: GitHub Actions runs the unit tests on every push and pull request (DR-004; lint, type checks and integration tests follow in WP-07)
- [ ] README tools table; CHANGELOG; version bump
- [ ] WP-13 close

**Exit criteria:**
- Each draft tool's link opens the Redmine form with the proposed values filled in, and nothing is saved until the user submits

---

# Next

## WP-07: Repo baseline

**Goal:** The repo is self-contained, and every change is tested in CI against a real Redmine (DR-004). No change in behaviour.

### Tasks
- [x] Move the development documents into this repo; drop the old framework (`.sdlc-framework` references, `.claude/` tooling); standalone `AGENTS.md`
- [ ] `pyproject.toml`: build system, dev dependency group (pytest, pytest-asyncio, ruff, pyright), pytest settings
- [ ] Add `.gitattributes`
- [ ] Add ruff and pyright settings; fix what they report
- [ ] Test Redmine in Docker: compose file and seed script (projects, users, roles, issues, wiki pages, an OAuth app), for local runs and CI
- [ ] GitHub Actions: lint, type check and unit tests on Python 3.11 to 3.13; integration tests against Redmine 6.1 and 7.0 from the test Redmine
- [ ] Dependabot for pip, Docker and GitHub Actions
- [ ] Docker: `HEALTHCHECK`; stop `.dockerignore` excluding `README.md`
- [ ] Check settings at startup and fail with a clear message (today a missing variable raises a bare `KeyError`)
- [ ] WP-07 close

**Exit criteria:**
- CI runs on every push and pull request, and passes on `main`
- Integration tests run against Redmine 6.1 and 7.0
- No file loads or links the old `.sdlc-framework`

---

## WP-08: Hardening

**Release:** a minor version.

**Goal:** Users stay logged in across restarts, each sees only the tools their Redmine grant allows, and the server is safe to run for a whole company.

### Tasks
- [ ] Keep the granted scopes in FastMCP's token (`upstream_claims`); remove `_scope_store` (RISK-001)
- [ ] Persistent, encrypted login storage: fixed `JWT_SIGNING_KEY`, storage on a Docker volume (or Redis), documented in `.env.example` (RISK-002)
- [ ] Hide tools the user's scopes do not allow, with FastMCP's per-tool scope check (DR-003, RISK-004)
- [ ] Read-only mode: write scopes are left out of the login request and write tools are refused
- [ ] Check `REDMINE_SCOPES` at startup and stop with a message listing the scopes the server accepts
- [ ] When Redmine refuses the login with `invalid_scope`, show which scopes to tick on the Redmine OAuth app
- [ ] Decide the consent screen setting (`remember` or off) and record it as a DR (RISK-003)
- [ ] `/health` route
- [ ] Logging of requests, OAuth events and Redmine errors, with no tokens or response bodies
- [ ] Tool errors: set the MCP error flag; handle 401, other 4xx, 5xx and network errors
- [ ] Escape IDs and page titles in Redmine URLs; reuse one HTTP client
- [ ] Tests: two users stay separate; login survives a restart; scopes survive a token refresh
- [ ] Update README and architecture notes; CHANGELOG; version bump
- [ ] WP-08 close

**Exit criteria:**
- Restarting or recreating the container does not log users out
- A user without a scope does not see the tools that need it

---

## WP-09: Safety and MCP quality

**Release:** a minor version.

**Goal:** Clients can tell reading tools from writing ones, admins can limit what the server exposes, and large or hostile Redmine content cannot flood or steer the model.

### Tasks
- [ ] Tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`) on every tool, with a test that fails when one is missing
- [ ] Tool allowlist, set by environment variable
- [ ] Response size limit and one pagination format for every list
- [ ] Mark text that comes from Redmine so the model treats it as data, not instructions
- [ ] Split `tools.py` (921 lines) by area: issues, projects, wiki, time
- [ ] Fix `rename_wiki_page`, which sends a field Redmine probably does not accept
- [ ] CHANGELOG; version bump
- [ ] WP-09 close

**Exit criteria:**
- Every tool carries annotations
- A read-only deployment exposes no tool that writes

---

## WP-10: Redmine coverage

**Release:** a minor version.

**Goal:** Cover the common Redmine work that similar servers already support.

### Tasks
- [ ] Create and update time entries; list time entry activities
- [ ] Attachments: download with a size limit (images returned so the model can see them) and upload
- [ ] Watchers; create and delete issue relations
- [ ] One tool that returns a project's trackers, statuses, members and custom fields
- [ ] CHANGELOG; version bump
- [ ] WP-10 close

**Exit criteria:**
- Each new tool has unit tests and an integration test

---

## WP-11: Security review

**Goal:** A full security check of the server, its dependencies, its container, a reference deployment and this repo, with every finding fixed or accepted in a DR. Written up as a report in `docs/reports/`; each finding gets a severity.

### Tasks
- [ ] Threat model: assets (Redmine tokens, user data, signing keys), actors (users, other MCP clients, outsiders, a hostile issue text), trust boundaries
- [ ] OAuth flow: redirect URI checks (CIMD, DCR, loopback), PKCE, consent and confused deputy, state and `iss`, token audience, lifetimes and refresh, revocation, logout
- [ ] Token storage: encryption at rest, signing and encryption keys, key rotation, what survives a restart
- [ ] Scope enforcement: each tool checks the scopes it needs, after refresh and restart; no over-grant (RISK-001)
- [ ] Input handling: path and query escaping in Redmine URLs, parameter validation, size limits, errors that leak internals
- [ ] Prompt injection: Redmine text marked as data; write tools cannot be driven by issue content alone
- [ ] Transport and HTTP: CORS (`allow_origins=["*"]` today), Host and Origin checks, TLS between the proxy and the container, rate limiting, request size
- [ ] Logging: no tokens, secrets or response bodies in logs; enough to trace a request
- [ ] Dependencies: `pip-audit`, pinned versions or a lock file, licences
- [ ] Static analysis: `bandit` and `semgrep` (or CodeQL) on the source
- [ ] Secrets: `gitleaks` over the full git history, `.env` handling, `.dockerignore`
- [ ] Container: non-root user, image scan (`trivy`), base image updates, filesystem permissions, healthcheck
- [ ] Reference deployment: `.env` file permissions, direct reachability of the container port, reverse proxy or tunnel settings, Docker socket exposure; written into the deployment guide
- [ ] GitHub repo: branch protection, Dependabot alerts, secret scanning, CodeQL, who has write access
- [ ] Fix or accept every finding; re-run the scans
- [ ] WP-11 close

**Exit criteria:**
- The report lists every check above with its result
- No open finding rated high or critical
- Scans run in CI on every pull request

---

# Later

## WP-12: Release 1.0

**Release:** v1.0.0.

**Goal:** Anyone can deploy the server from the README and a published image.

### Tasks
- [ ] Finish the README, `.env.example` and a deployment guide
- [ ] Add a LICENSE and SECURITY.md
- [ ] Publish the Docker image to GHCR from CI
- [ ] CHANGELOG; bump to 1.0.0; tag `v1.0.0`
- [ ] WP-12 close

**Exit criteria:**
- A fresh deployment from the README and the published image works with Claude Code

---

## Backlog

Unscheduled ideas. Promoted to a work package once scoped and agreed.

- Move to FastMCP 4.x and MCP protocol 2026-07-28 (sessionless), once 4.x settles
- Redmine 7 webhooks
- Consent per MCP client (today all clients share one Redmine app, so Redmine approves silently after the first grant)
- Support for Redmine plugins such as Agile and Checklists
- Publish to PyPI; list the server in the MCP registry
- List the projects the user can see (identifier and name)
- List the wiki pages of a project; a wiki start page that only shows `{{child_pages}}` gives no way to find the others
- Search wiki pages, not only issues
- Filter `list_issues` by category and by created or updated date
- List issue statuses, trackers and categories with their IDs, so filters can use them
- List and read attachments on issues and wiki pages
- Journal paging in `get_issue_details`: history is capped at 25 entries (`MAX_JOURNAL_ENTRIES`) with no way to read the rest. On 2026-10-13 an issue with 53 entries hid the last 28, which held the needed information. Add `journal_offset` / `journal_limit` (or a separate paged journal tool) and keep the cap as the default. The cap keeps the oldest 25 today, so the newest entries are the ones dropped
- Per-project permissions for an agent connection: a user connects an agent with narrower rights than their own, set per project (to be designed)
