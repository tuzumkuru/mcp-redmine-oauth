# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/).
Versioning: [Semantic Versioning](https://semver.org/) — see
[.sdlc-framework/versioning.md](.sdlc-framework/versioning.md).

Add entries under `[Unreleased]` as work lands. At version-bump time, rename
`[Unreleased]` to `[X.Y.Z] — YYYY-MM-DD` and open a new empty `[Unreleased]`
above it. The CHANGELOG update belongs in the **same commit** as the version bump.

---

## [Unreleased]

### Added

### Changed

- Require `fastmcp>=3.4.8`.

### Fixed

- Claude Code could not log in: FastMCP before 3.2.0 rejected its OAuth callback
  (`http://localhost:<port>/callback`) because the port did not match the client's
  metadata document. FastMCP 3.2.0+ accepts any port on loopback (RFC 8252 § 7.3).
