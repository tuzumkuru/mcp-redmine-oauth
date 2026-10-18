# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/).
Versioning: [Semantic Versioning](https://semver.org/).

Add entries under `[Unreleased]` as work lands. At version-bump time, rename
`[Unreleased]` to `[X.Y.Z] — YYYY-MM-DD` and open a new empty `[Unreleased]`
above it. The CHANGELOG update belongs in the **same commit** as the version bump.

---

## [Unreleased]

### Added

### Changed

### Fixed

## [0.6.0] — 2026-10-18

### Added

- Draft tools `draft_new_issue`, `draft_issue_update` and `draft_new_project`: each returns a link to the Redmine form filled in with the proposed values. Nothing is saved until the user submits the form, and Redmine saves it as that user. Text that would make the link too long is returned separately for the user to paste.
- `REDMINE_PUBLIC_URL`: the Redmine URL used in draft links, when it differs from `REDMINE_URL`.
- CI: unit tests on Python 3.11 to 3.13 for every push and pull request.

## [0.5.1] — 2026-10-06

### Changed

- Require `fastmcp>=3.4.8`.

### Fixed

- Claude Code could not log in: FastMCP before 3.2.0 rejected its OAuth callback
  (`http://localhost:<port>/callback`) because the port did not match the client's
  metadata document. FastMCP 3.2.0+ accepts any port on loopback (RFC 8252 § 7.3).
