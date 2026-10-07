# Risks

One row per risk, plus a section where a risk needs detail. Scoring: likelihood and impact `H`/`M`/`L`; score `critical`, `high`, `medium` or `low` (H×H critical, H×M or M×H high, M×M, H×L or L×H medium, otherwise low). Status: `open`, `mitigated`, `monitoring` or `resolved`.

| ID | Title | Likelihood | Impact | Score | Mitigation | Status |
|----|-------|------------|--------|-------|------------|--------|
| RISK-001 | Server treats a user as having every scope after a token refresh | H | M | high | Phase 8: keep scopes in the FastMCP token | open |
| RISK-002 | Recreating the container logs every user out | H | M | high | Phase 8: fixed signing key, storage on a volume | open |
| RISK-003 | Consent screen is off, so the confused-deputy protection is off | M | H | high | Phase 8: decide the consent setting | open |
| RISK-004 | Per-session tool hiding will not work on the sessionless MCP protocol | M | M | medium | Phase 8: use per-tool scope checks, not session state | open |
| RISK-005 | Clients whose metadata lists a fixed loopback port (e.g. GitHub Copilot CLI) cannot log in | M | L | low | Watch; `enable_cimd=False` if needed | monitoring |

## RISK-001 — Scope over-grant after refresh

`RedmineProvider._extract_upstream_claims` stores the granted scopes in an in-memory dict keyed by the Redmine access token. FastMCP 3.2+ refreshes the Redmine token silently, without calling that method, so the new token has no entry. `RedmineTokenVerifier` then falls back to all registered scopes. Redmine still enforces the user's real permissions, so the effect is that the server's own scope check stops working. The dict is also lost on restart and never pruned.

## RISK-002 — Logins lost on container recreate

With no `client_storage`, FastMCP keeps encrypted login state under `~/.fastmcp` inside the container. The compose file has no volume and there is no fixed `JWT_SIGNING_KEY`, so a recreated container forgets every client and token.
