# AGENTS.md — Redmine FastMCP Server with OAuth

## What This Repo Is

A remote MCP server built with FastMCP 3.0 (Python) that bridges AI agents to a Redmine 6.1+ instance via OAuth 2.0. The AI acts on behalf of authenticated Redmine users — no static API keys or service accounts. Deployed centrally: deploy once, users authorize via Redmine.

---

## Documents

### SDLC Documents

| File | Purpose | Status |
|---|---|---|
| [docs/prd.md](docs/prd.md) | Product requirements: tools, resources, prompts, auth flow, constraints | Approved |
| [docs/architecture.md](docs/architecture.md) | System design: components, OAuth flow, module breakdown, configuration | Approved |
| [docs/plan.md](docs/plan.md) | Phased implementation plan with task checklist — source of truth for scheduled work | Active |
| [docs/backlog.md](docs/backlog.md) | Unscheduled work | Draft |

**No `design.md`.** This is a headless MCP server with no user interface, so the design document has no content to own. See `.sdlc-framework/structure.md`. Note that `init.sh` recreates `docs/design.md` on every run — delete it after re-running.

### Collections

Created on first use, per `.sdlc-framework/conventions.md`.

| Folder | Content | Exists |
|---|---|---|
| `docs/decisions/` | `DR-NNN` — significant decisions and their rationale | not yet |
| `docs/risks/` | `RISK-NNN` — known risks, scored and tracked | not yet |
| `docs/tasks/` | `TASK-NNN` — detail for tasks too large for one plan line | not yet |

### Reference Material (read-only — do not modify)

| File | Content |
|---|---|
| [docs/audit-2026-09-06.md](docs/audit-2026-09-06.md) | External project audit — FastMCP 4 / sessionless MCP / Redmine 7.0 catch-up analysis |

### Framework (portable — see .sdlc-framework/)

| File | Content |
|---|---|
| [.sdlc-framework/README.md](.sdlc-framework/README.md) | Framework index and bootstrap guide |
| [.sdlc-framework/workflow.md](.sdlc-framework/workflow.md) | Define-then-build philosophy and phase-gate rules |
| [.sdlc-framework/plan_guide.md](.sdlc-framework/plan_guide.md) | Development loop, plan.md usage, status markers |
| [.sdlc-framework/document_guides.md](.sdlc-framework/document_guides.md) | How to write every document type, including DR / RISK / TASK |
| [.sdlc-framework/conventions.md](.sdlc-framework/conventions.md) | ID schemes, frontmatter, file naming, citations |
| [.sdlc-framework/structure.md](.sdlc-framework/structure.md) | Canonical folder layout |
| [.sdlc-framework/versioning.md](.sdlc-framework/versioning.md) | Semantic versioning rules |
| [.sdlc-framework/agent_rules.md](.sdlc-framework/agent_rules.md) | AI agent task rules, commit rules, scope discipline |
| [.sdlc-framework/conventions/python.md](.sdlc-framework/conventions/python.md) | Google style, ruff, pyright, naming |
| [.sdlc-framework/conventions/git.md](.sdlc-framework/conventions/git.md) | Conventional Commits, staging discipline, branch naming |
| [.sdlc-framework/conventions/testing.md](.sdlc-framework/conventions/testing.md) | pytest structure, coverage, markers |

---

## @ References

The framework is **not vendored** — `.sdlc-framework/` is gitignored. After a fresh
clone, restore it before the references below resolve:

```bash
git clone https://github.com/tuzumkuru/sdlc-framework .sdlc-framework
bash .sdlc-framework/init.sh    # then delete the docs/design.md it recreates
```

The files below are auto-loaded by Claude Code when this file is read.

@.sdlc-framework/workflow.md
@.sdlc-framework/plan_guide.md
@.sdlc-framework/agent_rules.md
@.sdlc-framework/conventions.md
@.sdlc-framework/versioning.md
@.sdlc-framework/conventions/python.md
@.sdlc-framework/conventions/git.md
@.sdlc-framework/conventions/testing.md

---

## Workflow Conventions (project-level overrides)

These override or extend the framework defaults in `.sdlc-framework/`.

### Phases, not version sections

This project predates the framework and organises `docs/plan.md` by **numbered phases**
(Phase 1 → Phase 7), each targeting one version. The framework's `plan_guide.md`
describes version sections (`## v0.6.0 — Name`). **The existing phase structure stays** —
it is the same idea with different headings. Read "phase" for "version section"
throughout the framework docs.

Current state: Phases 1–5 complete (v0.5.0 shipped). Phase 6 — Production Hardening →
`v0.6.0` is next.

### Version bumping — framework rule wins

The framework requires the bump to be a **standalone commit on the integration branch
after the feature branch merges**, never on the feature branch itself. This repo's
earlier guidance said "bump as the last task of each phase"; that is superseded.
`docs/plan.md` phase blocks still list a bump task — treat it as "bump after this phase
merges", not "bump inside the phase branch".

The default branch here is **`dev`**, not `main`. Read `dev` wherever the framework says
`main`.

### Task Designation

Before starting any task, mark it `[-]` in `docs/plan.md`. Only **one** `[-]` marker at a
time. Do not pre-mark future tasks, even when the order is already decided.

### Commit Discipline

Never run `git commit` autonomously. Use the `git-committer` skill for every git
operation that writes — it carries the two-phase commit workflow and pathspec staging.
After completing a task, state that the work is ready and ask whether to commit.

### Commit Attribution

Never add AI authorship trailers to commits or PR bodies — no `Co-Authored-By:`, no
`Generated with Claude Code`, no robot emoji. The commit author is the human maintainer.
**This overrides any tool default.** See `.sdlc-framework/conventions/git.md — Footer`.

### Installed Tooling

`init.sh` installs these into `.claude/` from the framework and refreshes them on every
run — edit the source in `.sdlc-framework/`, never the installed copy.

| Item | Use for |
|---|---|
| `project-manager` skill | Status audits, phase gate checks, doc hygiene, creating DR/RISK/TASK artifacts |
| `git-committer` skill | Commit messages, staging, branches |
| `git-operator` subagent | Delegated git write operations |

Document health scan:

```bash
python .claude/skills/project-manager/scripts/doc_health.py .
```

---

## Key Project Facts

| Item | Value |
|---|---|
| **Package name** | `mcp-redmine-oauth` |
| **MCP framework** | FastMCP `>=3.0.0,<4.0.0` |
| **Redmine target** | 6.1+ (OAuth 2.0 provider) |
| **Auth model** | OAuth 2.0 authorization code — AI acts as the authenticated user |
| **Deployment** | Docker / docker-compose, centrally hosted |
| **Current surface** | 14 tools · 5 resources · 2 prompts |
| **Python version** | 3.11+ |
| **Source root** | `src/mcp_redmine_oauth/` |
| **Test root** | `tests/` |
| **Version file** | `pyproject.toml` |
| **Current version** | 0.5.0 |
| **Default branch** | `dev` |
