# Decisions

One row per decision, plus a section with **Context**, **Options**, **Decision** and **Consequences**. Status: `open`, `decided` or `superseded`.

| ID | Title | Status | Decision |
|----|-------|--------|----------|
| DR-001 | FastMCP version line | decided | `fastmcp>=3.4.8,<4`; 4.x in the backlog |
| DR-002 | What to do with PR #2 | decided | Closed unmerged; Phase 8 redoes the work |
| DR-003 | How writes reach Redmine | decided | Link tools that open a prefilled Redmine form; write tools stay, shown only when the token holds the write scopes |
| DR-004 | How changes are tested | decided | Every change is tested in CI, including against a real Redmine (6.1 and 7.0), before release |

---

## DR-001 — FastMCP version line

**Context.** Claude Code could not log in: FastMCP before 3.2.0 rejected its loopback callback on a random port ([report](reports/2026-10-05-review.md) § *Claude Code login failure*). FastMCP 4.0 (2026-08-31) moves to the sessionless MCP protocol and has breaking changes. 3.x still gets security fixes; 3.4.8 shipped on 2026-10-04. 3.4.3 turned on a Host/Origin check by default that 3.4.4 reverted.

**Options**

| Option | For | Against |
|--------|-----|---------|
| `>=3.4.8,<4` | Fixes the login; all 90 tests pass on 3.4.8; no code change | Stays on the older protocol |
| Move to 4.x now | Newest protocol, scope step-up | Young (11 patch releases in 5 weeks); breaking changes |

**Decision.** `fastmcp>=3.4.8,<4`, released as v0.5.1 on 2026-10-06. Moving to 4.x is in the backlog.

**Consequences.** The server speaks MCP up to protocol 2025-11-25. Per-tool scope challenges and sessionless MCP wait for the 4.x move.

## DR-002 — What to do with PR #2

**Context.** PR #2 (opened by an AI agent on 2026-03-09) attempted the hardening phase. The 2026-10-05 review found refresh tokens stored unencrypted in SQLite, a Redis option that crashes on start, a permission error in Docker, 7 failing existing tests, and an end-to-end test that is `assert True`. Its `/health` route and FastMCP's `disable_components` approach work.

**Options**

| Option | For | Against |
|--------|-----|---------|
| Fix and merge it | Some work reused | Most of it has to change; it also bumps the version on the branch |
| Close it and redo the hardening phase | Clean design on FastMCP's own storage | Writes the reusable parts again |

**Decision.** Closed unmerged on 2026-10-06, with a comment on the PR.

**Consequences.** Nothing from PR #2 is reused as code. The `/health` route and scope-based tool hiding are Phase 8 tasks.

## DR-003 — How writes reach Redmine

**Context.** Agents should propose changes and a person should accept them, not agents writing on their own. Redmine 6.1's new-issue and edit-issue pages fill the form from `issue[...]` values in the link and save nothing until the user submits (`app/controllers/issues_controller.rb`, `new` and `edit`). The wiki edit page does not take text from the link. Redmine has no endpoint that tells a client which scopes its OAuth app holds, and asking for a scope the app lacks fails the login (`config/initializers/30-redmine.rb`).

**Options**

| Option | For | Against |
|--------|-----|---------|
| Write tools only | Simple | The agent writes without a person in the loop |
| Approval page on the server | Server-enforced approval | Pending-change store, page, expiry and audit log to build |
| Proposal notes or issues in Redmine | Approval inside Redmine | Needs webhooks (Redmine 7.0) or polling; Redmine cannot tell the user's click from the agent's |
| Link tools that open a prefilled Redmine form | No write by the agent; Redmine saves it as the user, with its own permissions and workflow | Not for wiki text or attachments; long text may hit the URL length limit |

**Decision.**
- Add link tools that return a prefilled Redmine form link. They need read scopes only.
- Keep the write tools. Each needs its write scope and is shown only when the user's token holds it, so the scopes on the Redmine OAuth app decide whether direct writes are possible.
- No approval page.

**Consequences.**
- A deployment that grants only read scopes lets agents propose changes through links and nothing more.
- Phase 8 makes tool visibility follow the granted scopes; Phase 9 adds the link tools.
- Wiki changes go through the write tools where the scope allows it, or are shown as text to paste.

## DR-004 — How changes are tested

**Context.** The Claude Code login failure only showed against a real client and a real Redmine; unit tests with mocks passed. The server targets Redmine 6.1 and 7.0, and Redmine plugins and versions change the API's behaviour.

**Options**

| Option | For | Against |
|--------|-----|---------|
| Unit tests with mocks only | Fast | Misses OAuth, scope and API behaviour of a real Redmine |
| Manual testing against a live Redmine | Real behaviour | Not repeatable; risks real data |
| CI with unit tests plus integration tests against Redmine in Docker | Real behaviour on every change; version matrix; fake data only | Setup work; slower CI |

**Decision.** Every change is tested in CI before release: lint, type check and unit tests, plus integration tests against Redmine 6.1 and 7.0 running in Docker with seeded data and an OAuth app. Decided by the maintainer on 2026-10-06.

**Consequences.** Phase 7 adds the test Redmine (compose file and seed script) and the CI workflows. New tools get an integration test.
