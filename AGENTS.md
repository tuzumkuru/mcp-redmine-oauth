# AGENTS.md — Redmine FastMCP Server with OAuth

Guidance for AI agents (Claude Code, Codex, Copilot, ...) working in this repository.

## What This Repo Is

A remote MCP server, built with FastMCP 3 (Python), that connects AI agents to a Redmine 6.1+ instance through Redmine's own OAuth 2.0 provider. Each user logs in with their Redmine account and the agent acts as that user. No shared API keys or service accounts. Deployed centrally: one server, every user authorizes through Redmine.

## Key Facts

| Item | Value |
|---|---|
| Package | `mcp-redmine-oauth` |
| MCP framework | FastMCP `>=3.4.8,<4.0.0` |
| Redmine | 6.1+ (OAuth 2.0 provider) |
| Auth | OAuth 2.0 authorization code; the agent acts as the logged-in user |
| Deployment | Docker / docker compose |
| Surface | 14 tools, 5 resources, 2 prompts |
| Python | 3.11+ |
| Source / tests | `src/mcp_redmine_oauth/` / `tests/` |
| Version | `pyproject.toml`; see `CHANGELOG.md` |
| Default branch | `main` |

## Documents

| File | What it holds |
|---|---|
| [docs/plan.md](docs/plan.md) | Phases, tasks and backlog. The source of truth for scheduled work |
| [docs/decisions.md](docs/decisions.md) | Decision records (DR-NNN) |
| [docs/risks.md](docs/risks.md) | Risk register (RISK-NNN) |
| [docs/reports/](docs/reports/) | Reviews and investigations |
| [docs/prd.md](docs/prd.md) | Product requirements |
| [docs/architecture.md](docs/architecture.md) | Components, OAuth flow, modules, scopes, configuration |
| [CHANGELOG.md](CHANGELOG.md) | Released changes (Keep a Changelog) |

## How We Work

- **Plan first.** Work comes from `docs/plan.md`. Mark the task you work on `[-]`; one at a time. Mark it `[x]` when done, `[!]` with a reason when blocked, `[~]` with a reason when skipped. New ideas go to the backlog, agreed with the maintainer first.
- **Decisions are written down.** A change that departs from `docs/architecture.md` or a decision record gets a DR first, then the code.
- **Tests run before every commit:** `pytest`. CI runs them on every pull request (see the plan for the CI work).
- **Ask before acting** on anything public (pushes, pull requests, comments, releases) or on a deployed server.
- **Never invent.** Redmine API behaviour, scopes and FastMCP APIs are checked in their source or docs, or marked TBD.

## Git

- **Conventional Commits:** `type(scope): summary`, imperative, lower case after the colon, no trailing period, 72 characters at most. Body only when the why is not obvious.
- **Branches:** `feature/…`, `fix/…`, `docs/…`, `chore/…`, merged into `main` through a pull request.
- **Version bump:** a standalone `chore: bump version to X.Y.Z` commit on `main` after the work merges, with the `[Unreleased]` CHANGELOG section renamed in the same commit, then an annotated tag `vX.Y.Z`.
- **Every commit is previewed** (`git status`, `git diff --cached`, message) and made only after the maintainer confirms. Stage and commit by explicit path.
- **Author:** `Tolga Uzun <tolgauzun@gmail.com>` (set in the clone's git config).
- **No AI attribution** in commits or pull requests: no `Co-Authored-By:`, no "Generated with", no robot emoji. This overrides any tool default.
- Never force-push `main`, never rewrite pushed history, never push without being asked.
