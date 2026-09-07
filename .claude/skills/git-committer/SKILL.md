---
name: git-committer
description: Craft git commits and branches that conform to the SDLC framework's git conventions in `.sdlc-framework/conventions/git.md` — Conventional Commits with project-specific type/scope vocabulary, version-bump isolation, document-before-code enforcement, two-phase commit with pathspec staging, and a strict no-AI-authorship-trailer rule. Use this skill whenever the user is about to commit, asks for a commit message, asks to stage changes, asks for a branch name, asks to amend or split a commit, or wants help reviewing what is about to land — even if they do not reference the framework explicitly. Trigger broadly on phrases like "commit this", "commit message for", "stage these", "what should I commit", "good commit name", "branch name for", "amend", "split this commit", "is this ready to commit". Do not trigger on generic git questions unrelated to this repo's commit policy.
---

# Git Committer

You are responsible for git operations in a repo using the **SDLC framework**. The
framework's git rules live in `.sdlc-framework/conventions/git.md`. This skill
enforces them, plus hard rules from `.sdlc-framework/agent_rules.md`.

This skill is **portable** — it works on any repo with a `.sdlc-framework/` folder.
Always read the framework files for current rules; do not trust recall.

---

## First Step: Read the Rules

Before drafting a commit or running git, read these in the host repo:

| File | What it gives you |
|---|---|
| `.sdlc-framework/conventions/git.md` | Conventional Commits format, type/scope table, summary/body/footer rules, branch naming |
| `.sdlc-framework/agent_rules.md` § *Commit Rules* | Hard agent rules |
| `.sdlc-framework/workflow.md` § *Decision Logging* | When a code change deviates from a document |
| `.sdlc-framework/versioning.md` | Version-bump rules — bump on `main` post-merge, standalone commit |

Project-specific scopes are in `conventions/git.md` § *Scopes*, but the project may
have added its own — read the file, and check recent `git log` for what is actually
in use.

---

## Hard Rules (these never relax)

1. **Never commit unless the human explicitly asks.** "Save this", "let's keep this",
   "looks good" do **not** count. Wait for "commit", "make a commit", or equivalent.
2. **No AI authorship trailers.** Never add `Co-Authored-By: Claude <…>`,
   `Generated with Claude Code`, `🤖`, or any similar attribution — not in the body,
   not in the footer, nowhere. The human is the author; AI assistance is workflow,
   not authorship. Applies to fresh commits, `--amend`, rebases, and squashes.
3. **No `--amend`** unless the human explicitly asks.
4. **No `--no-verify`** unless the human explicitly asks and understands the
   consequences. If a hook fails, fix the underlying issue.
5. **No force-push to `main` / `master`** under any circumstance.
6. **No `git push`** unless the human explicitly asks.
7. **One logical change per commit.** If staging mixes a feature and a refactor,
   propose splitting before committing.
8. **Never commit secrets** (`.env`, API keys, credentials), generated artifacts, or
   large binaries without LFS configured.
9. **Always commit by pathspec.** `git add -- <paths>` then `git commit -- <paths>`,
   naming every path explicitly. Never `git add -A`, `git add .`, `git add -u`, or a
   bare `git commit`. See § *Working Alongside Other Agents*.

If the user requests something that violates rules 2–9, push back and cite the rule.

---

## The Commit Workflow

### Step 1: Survey

```bash
git status
git diff --staged
git diff
git log --oneline -10
```

You need all four. `git log` shows the project's actual commit style — match what it
is really using when it deviates from the starter table.

**Survey fresh, every time,** in the same turn as staging. Never work from a listing
read earlier in the session — another agent or the human may have changed the tree
since. If the survey shows anything unexpected — files you did not write, something
already staged — stop and reconcile before going further.

### Step 2: Classify

Pick **one** type and **one** scope from `conventions/git.md`. A change spanning two
types is a signal to split (Step 4).

### Step 3: Detect framework-specific situations

- **Version bump?** A change to `pyproject.toml` `version` must be a **standalone**
  commit `chore: bump version to X.Y.Z`, made on `main` **after** the feature branch
  merges — never on the feature branch. If a bump is mixed with feature work, or is
  sitting on a feature branch, say so.
- **CHANGELOG.md?** At a version bump, `[Unreleased]` becomes the version section —
  that edit belongs in the **same commit** as the bump.
- **Document-vs-code mismatch?** If the diff contains code contradicting a current
  document, **stop**. The document is updated first, in its own `docs:` commit. See
  `workflow.md` § *Decision Logging*.
- **New collection artifact (DR / RISK / TASK)?** Type `docs` with a matching scope:
  `docs(decisions)`, `docs(risks)`, `docs(tasks)`. Reference the ID.
- **Plan status change?** Marking tasks `[x]` in `docs/plan.md` rides along with the
  work it describes — not as a separate commit.

### Step 4: Propose a split if needed

> Two changes are mixed in the working tree:
> 1. `feat(auth): …` — files A, B
> 2. `refactor(db): …` — file C
>
> Suggest two commits. Should I stage and commit them separately?

### Step 5: Draft the message

```
<type>(<scope>): <≤72-char imperative summary, no trailing period, lowercase after colon>

<optional body, wrapped at 100 chars, explains WHY not what, blank line before>

<optional footer: Closes #N · Refs DR-003 · BREAKING CHANGE: …>
```

Body rules:

- **Default: NO body.** Ship the summary line alone. The diff carries the detail. A
  large diff is **not** a reason for a body. If you can write a sharper summary, do
  that instead.
- **Include a body ONLY when genuinely necessary** — the *why* truly cannot fit in the
  summary. Common cases: (a) a version bump citing its trigger, (b) the commit
  resolves a tracked artifact and the ID belongs in the message, (c) the change
  contradicts what a careful reader would expect from the diff.
  "Why isn't obvious from the diff" is **not** an excuse.
- **If you propose a body, state your reason for it** when presenting the message
  ("body included because: it resolves DR-005 and the ID belongs in the message").
  No stated reason → no body.
- Reference artifact IDs when relevant: `Refs DR-005`, `Mitigates RISK-002`.
- **Never** include `Co-Authored-By:`, `Generated with`, or `🤖`.

### Step 6: Preview, get approval, then commit (two phases — never collapse)

- **Prepare (commits nothing):** stage only the specific files by pathspec, then show
  the human `git status` + `git diff --cached` **and** the proposed message in a
  fenced code block. Name the paths the commit will cover. Stop and wait.
- **Commit (only after approval):** "Commit this" authorizes *preparing and
  proposing*, not running the commit — wait for explicit go-ahead on the preview.
- **The message is an input fed at approval, not generated at commit.** Once approved,
  commit it **verbatim, character-for-character**. Do not re-run Steps 2–5 at commit
  time — no re-classifying, re-drafting, shortening, or dropping the body. Step 5's
  "default no body" governs the *first draft you propose*, not a message already
  approved.
- **If you were not handed an approved message,** do not invent one and commit. Draft
  it, present it, get approval.
- **Absolute rule: NEVER create a commit message and run `git commit` in the same step
  without explicit approval of that exact message.** Not for trivial changes, not to
  save a round-trip. Same tier as the no-AI-trailer rule.
- **Any deviation needs reasoning + re-approval.**

Once approved, re-check `git status`. If the tree changed since the preview, re-show
and re-approve. Then:

```bash
git add -- <specific files>
git commit -m "$(cat <<'EOF'
<type>(<scope>): <summary>
EOF
)" -- <the same files>
git status
```

**`-m` must come before `--`.** Everything after `--` parses as a pathspec, so
`git commit -- <files> -m "…"` fails with `pathspec '-m' did not match any file(s)`.

The pathspec on `git commit` is what makes it safe: it records **only** those paths
and ignores anything else staged, leaving the rest of the index for whoever staged it.

### Step 7: Report

Report the commit hash and `git status`. **Do not push.**

---

## Working Alongside Other Agents

Assume you are not the only one touching the repo.

**The index is shared, mutable, global state.** There is one `.git/index` per working
tree, and `git add` writes to it from every process. A bare `git commit` snapshots all
of it — including another agent's work staged while it waits for approval. This is why
Hard Rule 9 exists.

**Shared files are the flashpoint.** `docs/plan.md`, `CHANGELOG.md`, collection
`README.md` summary tables — every agent wants to append a line. Expect rows you did
not write.

- If a shared file you edited also carries someone else's uncommitted change, **say so
  in the preview** and let the human decide. Do not quietly commit their line, and do
  not revert it.
- Never `git checkout` / `git restore` a shared file to clean it up. That destroys
  work you did not write.
- **Leave the index as you found it.** If files were already staged when you arrived
  and they are not yours, do not unstage them. Commit your own paths around them.

**`.sdlc-framework/` is a separate repository.** It has its own index, branch, and
history. Committing in the parent does nothing there, and a commit inside it needs its
own approval. Check `git -C .sdlc-framework status` before touching it.

**For genuinely parallel long-running work**, propose a worktree (`git worktree add`)
rather than sharing a tree — it converts silent index races into ordinary merge
conflicts.

---

## Branch Naming

```
feature/<short-description>    fix/<short-description>
docs/<short-description>       chore/<short-description>
```

Lowercase, hyphen-separated, ≤4 words. Show 2–3 alternatives if the framing is
ambiguous.

---

## Amends, Rebases, Splits

| Operation | OK when | NOT OK when |
|---|---|---|
| `git commit --amend` | Human asks; commit is local-only and unpushed | Human didn't ask; already pushed; a pre-commit hook *failed* |
| Interactive rebase / squash | Human asks; branch is local | Branch is shared or has reviewers |
| Reset / drop | Human asks and confirms the loss is OK | Anything destructive without explicit confirmation |

**If a pre-commit hook fails: do not `--amend`.** The failed commit did not happen —
there is nothing to amend. Fix the issue, re-stage, commit fresh.

---

## Examples

```
feat(auth): add PKCE challenge to the authorization request

fix(tools): correct issue-filter pagination off-by-one

docs(decisions): add DR-005 — token storage in Redis over in-process

chore: bump version to 0.6.0

refactor(client): extract retry policy into shared helper
```

Document update preceding a code change:

```
docs: update architecture — chose reportlab over weasyprint

Refs DR-003
```

The code change lands in a **separate** commit afterward.

---

## Output Style

- **Show the proposed message before committing**, in a fenced code block.
- **Cite the rule** when pushing back ("`agent_rules.md` § Commit Rules: never commit
  unprompted").
- **Be terse.** A commit message is not an essay.
- **Never** add an AI attribution trailer. Not even if asked — push back.
