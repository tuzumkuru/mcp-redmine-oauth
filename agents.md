# Agent Guide — Redmine FastMCP Server

## What This Repo Is

A remote MCP server built with FastMCP 3.0 (Python) that bridges AI agents to a Redmine 6.1+ instance via OAuth 2.0. The AI acts on behalf of authenticated Redmine users — no static API keys or service accounts.

## Documents

| File | Purpose |
|---|---|
| [docs/prd.md](docs/prd.md) | Product requirements: tools, resources, prompts, auth flow, constraints |
| [docs/architecture.md](docs/architecture.md) | System design: components, OAuth flow, module breakdown, configuration |
| [docs/PLAN.md](docs/PLAN.md) | Phased implementation plan (MVP → V1 → V2) with task checklist |

---

## Workflow

This project uses a **define-then-build** workflow. No code is written without a matching document that justifies it.

### Phase Order

```
PRD  →  Architecture  →  Plan  →  MVP  →  V1  →  V2
 (what)     (how)        (when)   ← implementation phases →
```

Each document phase must be complete and agreed upon before the next begins. Each implementation phase must meet its success criteria before the next starts.

### Source of Truth

[docs/PLAN.md](docs/PLAN.md) is the single source of truth for current state. It tracks every task across all phases using status markers:

| Mark | Meaning |
|---|---|
| `[ ]` | Not started |
| `[-]` | In progress |
| `[x]` | Done |
| `[!]` | Blocked |
| `[~]` | Skipped |

### Development Loop

1. Open `PLAN.md` — identify the current phase and the next open task.
2. Consult the relevant doc (`prd.md` for features, `architecture.md` for structure).
3. Mark the task `[-]`, implement it, mark it `[x]`.
4. If a decision changes the design, update the relevant document before continuing.
5. When all tasks in a phase are `[x]`, verify success criteria, then move to the next phase.

### Rules

- Work one task at a time. Do not batch or skip ahead.
- Scope is fixed per phase. New ideas go into a later phase or back into the PRD.
- If blocked, mark `[!]` and document why in `PLAN.md` next to the task.
