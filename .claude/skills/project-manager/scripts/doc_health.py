#!/usr/bin/env python3
"""Deterministic document-health scan for repos using the SDLC framework.

Checks the ID-addressable collections (decisions, risks, tasks) and the SDLC
documents for the defects a human reviewer reliably misses: ID gaps, duplicate
IDs, filename/ID mismatch, missing or blank frontmatter fields, dangling
cross-references, collection-README drift, and leftover template placeholders.

Usage:
    python doc_health.py [repo-root]

Exit code is 0 when nothing critical was found, 1 otherwise, so it can gate CI.
Stdlib only — no install step, no PyYAML.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Collection name -> (ID prefix, required frontmatter fields)
COLLECTIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "decisions": ("DR", ("id", "title", "status", "decision", "created", "updated")),
    "risks": (
        "RISK",
        ("id", "title", "category", "likelihood", "impact", "score", "status",
         "created", "updated"),
    ),
    "tasks": ("TASK", ("id", "title", "version", "status", "created", "updated")),
}

# Frontmatter fields whose values reference other artifact IDs.
REF_FIELDS = ("mitigated_by", "depends_on", "supersedes", "affects")

SDLC_DOCS = ("prd.md", "architecture.md", "design.md", "plan.md", "backlog.md")

# (pattern, label, match-inside-HTML-comments)
PLACEHOLDERS = (
    (re.compile(r"<!--\s*fill in\s*-->", re.I), "<!-- fill in --> placeholder", True),
    (re.compile(r"^\s*(?:-\s*)?TBD\b", re.I | re.M), "TBD marker", False),
    (re.compile(r"Decision needed:", re.I), "unresolved 'Decision needed:'", False),
)

ID_RE = re.compile(r"\b((?:DR|RISK|TASK)-\d{3})\b")

FENCE_RE = re.compile(r"```.*?```", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def strip_fences(text: str) -> str:
    """Drop fenced code blocks — schema examples are not data."""
    return FENCE_RE.sub("", text)


def strip_comments(text: str) -> str:
    """Drop HTML comments — template instructions are not content."""
    return COMMENT_RE.sub("", text)


@dataclass
class Report:
    critical: list[str] = field(default_factory=list)
    warning: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.critical or self.warning or self.info)


@dataclass
class Item:
    path: Path
    ident: str
    number: int
    fields: dict[str, str]


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return the YAML frontmatter as flat key -> value strings.

    Deliberately minimal: the framework's schemas are flat scalar maps, so a
    real YAML parser would only add a dependency. Returns None when the file
    has no frontmatter block at all.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load_collection(folder: Path, prefix: str) -> tuple[list[Item], list[str]]:
    """Load every <PREFIX>-NNN-*.md in folder. Returns (items, malformed-names)."""
    items: list[Item] = []
    malformed: list[str] = []
    pattern = re.compile(rf"^{prefix}-(\d+)-[a-z0-9-]+\.md$")

    for path in sorted(folder.glob(f"{prefix}-*.md")):
        match = pattern.match(path.name)
        if not match:
            malformed.append(path.name)
            continue
        digits = match.group(1)
        if len(digits) != 3:
            malformed.append(f"{path.name} (ID must be zero-padded to 3 digits)")
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8")) or {}
        items.append(
            Item(path=path, ident=f"{prefix}-{digits}", number=int(digits), fields=fm)
        )
    return items, malformed


def check_collection(
    name: str, folder: Path, prefix: str, required: tuple[str, ...], report: Report
) -> list[Item]:
    items, malformed = load_collection(folder, prefix)

    for bad in malformed:
        report.critical.append(
            f"{name}/{bad} — filename does not match <PREFIX>-NNN-<title-slug>.md"
        )

    seen: dict[int, Path] = {}
    for item in items:
        rel = f"{name}/{item.path.name}"

        if item.number in seen:
            report.critical.append(
                f"{item.ident} — duplicate ID, also {seen[item.number].name}"
            )
        seen[item.number] = item.path

        if not item.fields:
            report.critical.append(f"{rel} — no YAML frontmatter block")
            continue

        declared = item.fields.get("id", "")
        if declared and declared != item.ident:
            report.critical.append(
                f"{rel} — frontmatter id '{declared}' does not match filename"
                f" '{item.ident}'"
            )

        for key in required:
            if key not in item.fields:
                report.critical.append(f"{item.ident} — frontmatter missing '{key}'")
            elif not item.fields[key]:
                report.warning.append(
                    f"{item.ident} — '{key}' is blank (use '—' for empty optional"
                    " fields)"
                )

        for key in ("created", "updated"):
            value = item.fields.get(key, "")
            if value and value != "—" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                report.warning.append(f"{item.ident} — '{key}' is not YYYY-MM-DD")

    # ID sequence gaps
    numbers = sorted(seen)
    if numbers:
        missing = [n for n in range(1, numbers[-1] + 1) if n not in seen]
        if missing:
            gaps = ", ".join(f"{prefix}-{n:03d}" for n in missing)
            report.warning.append(f"{name}/ — gap in ID sequence: {gaps}")

    return items


def check_references(all_items: dict[str, Item], report: Report) -> None:
    for ident, item in sorted(all_items.items()):
        for key in REF_FIELDS:
            raw = item.fields.get(key, "")
            if not raw or raw == "—":
                continue
            for ref in ID_RE.findall(raw):
                if ref not in all_items:
                    report.critical.append(
                        f"{ident} — '{key}' references {ref}, which does not exist"
                    )


def check_readme_drift(
    name: str, folder: Path, items: list[Item], report: Report
) -> None:
    readme = folder / "README.md"
    if not readme.exists():
        if items:
            report.warning.append(f"{name}/ — has items but no README.md index")
        return
    # Schema blocks in the index are examples, not table rows.
    text = strip_fences(readme.read_text(encoding="utf-8"))
    listed = set(ID_RE.findall(text))
    actual = {i.ident for i in items}

    for ident in sorted(actual - listed):
        report.warning.append(f"{name}/README.md — summary table missing {ident}")
    for ident in sorted(listed - actual):
        report.warning.append(
            f"{name}/README.md — summary table lists {ident}, which has no file"
        )


def check_documents(docs: Path, report: Report) -> None:
    for filename in SDLC_DOCS:
        path = docs / filename
        if not path.exists():
            # design.md and backlog.md are legitimately optional.
            if filename not in ("design.md", "backlog.md"):
                report.warning.append(f"docs/{filename} — not found")
            continue
        raw = path.read_text(encoding="utf-8")
        for pattern, label, in_comments in PLACEHOLDERS:
            # A marker inside an HTML comment is template guidance, not an
            # unresolved item — except <!-- fill in -->, which IS a comment.
            text = raw if in_comments else strip_comments(raw)
            hits = len(pattern.findall(text))
            if hits:
                report.critical.append(f"docs/{filename} — {hits}x {label}")


def check_plan(docs: Path, report: Report) -> None:
    plan = docs / "plan.md"
    if not plan.exists():
        return
    text = plan.read_text(encoding="utf-8")
    # Only count real checklist lines, not the legend or template blocks.
    active = re.findall(r"^\s*-\s*\[-\]\s+\S.*$", text, re.M)
    if len(active) > 1:
        report.critical.append(
            f"docs/plan.md — {len(active)} tasks marked [-]; exactly one is allowed"
        )

    for marker, label in (("!", "blocked"), ("~", "skipped")):
        for line in re.findall(rf"^\s*-\s*\[\{marker}\]\s+(.*)$", text, re.M):
            if "—" not in line and "--" not in line and ":" not in line:
                report.warning.append(
                    f"docs/plan.md — [{marker}] task has no inline {label} reason:"
                    f" {line.strip()[:60]}"
                )


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    docs = root / "docs"

    if not (root / ".sdlc-framework").is_dir():
        print(f"error: no .sdlc-framework/ in {root}", file=sys.stderr)
        return 2
    if not docs.is_dir():
        print(f"error: no docs/ in {root}", file=sys.stderr)
        return 2

    report = Report()
    all_items: dict[str, Item] = {}

    for name, (prefix, required) in COLLECTIONS.items():
        folder = docs / name
        if not folder.is_dir():
            continue  # collections are created on first use
        items = check_collection(name, folder, prefix, required, report)
        check_readme_drift(name, folder, items, report)
        for item in items:
            all_items.setdefault(item.ident, item)

    check_references(all_items, report)
    check_documents(docs, report)
    check_plan(docs, report)

    print(f"Doc Health — {root}")
    print(f"Scanned {len(all_items)} collection items\n")

    if not report:
        print("No issues found.")
        return 0

    for label, entries in (
        ("Critical", report.critical),
        ("Warnings", report.warning),
        ("Info", report.info),
    ):
        if entries:
            print(f"{label} ({len(entries)})")
            for entry in entries:
                print(f"  - {entry}")
            print()

    return 1 if report.critical else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
