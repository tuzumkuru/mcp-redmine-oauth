# Product Requirements Document

## Redmine FastMCP Server

**Version:** 1.0
**Stack:** FastMCP 3.0 (Python), Redmine 6.1+

---

## 1. Overview

A remote MCP server that exposes Redmine's REST API to AI agents via OAuth 2.0. The server uses Redmine 6.1's native OAuth 2.0 provider so the AI acts entirely on behalf of the authenticated user — no static API keys or service accounts required.

---

## 2. Architecture

**Components:**
- **Redmine (v6.1+):** Resource server and Identity Provider (IdP)
- **FastMCP Server:** Python app bridging MCP protocol and Redmine REST API
- **MCP Client:** AI interface (e.g., Claude Desktop)

**Authentication Flow:**
1. FastMCP server is registered in Redmine (Administration → Applications) as a confidential client, generating a Client ID and Client Secret. The redirect URI points back to the FastMCP server.
2. MCP Client connects to FastMCP and is redirected to Redmine's login/consent page.
3. After user approval, Redmine sends the authorization code to the FastMCP server's redirect URI.
4. FastMCP performs the back-channel code exchange using the Client ID and Secret, receiving an Access Token and Refresh Token.
5. FastMCP stores the Redmine tokens encrypted in a server-side token store. It issues its own short-lived JWT to the MCP client.
6. The MCP client only ever sees the FastMCP JWT — the Redmine token never leaves the server.
7. For every subsequent MCP request, the client sends the FastMCP JWT. The server validates it, looks up the corresponding Redmine token, and uses it for Redmine REST API calls. Token refresh is handled transparently by the server.

**Deployment:** Single Redmine instance, URL configured via environment variable. Multi-user: each client session has its own FastMCP JWT and corresponding stored Redmine token. Initial deployment as a Python process; Docker support to follow.

---

## 3. Functional Requirements

### Tools

| Tool | Inputs | Action |
|---|---|---|
| `search_issues` | `query` (str), `project_id` (int, opt), `status_id` (int/str, opt) | Search issues matching criteria |
| `get_issue_details` | `issue_id` (int) | Fetch full issue with description, custom fields, and journal history |
| `create_issue` | `project_id` (int), `tracker_id` (int), `subject` (str), `description` (str), `priority_id` (int, opt) | Create a new issue as the authenticated user |
| `update_issue` | `issue_id` (int), `notes` (str, opt), `status_id` (int, opt), `assignee_id` (int, opt) | Update issue state or add a comment |

### Resources

| URI | Returns |
|---|---|
| `redmine://projects/active` | Active projects the user can access, with IDs |
| `redmine://trackers` | Available trackers (Bug, Feature, etc.) with IDs |
| `redmine://users/me` | Authenticated user's profile |

### Prompts

| Prompt | Arguments | Instruction |
|---|---|---|
| `summarize_ticket` | `issue_id` | Fetch issue details and journal history. Summarize the discussion, identify blockers, and suggest next action. |
| `draft_bug_report` | `project_id`, `rough_notes` | Transform rough notes into a professional bug report with steps to reproduce, expected and actual behavior. Submit via `create_issue`. |

---

## 4. Non-Functional Requirements

- **Pagination:** Truncate or paginate large journal histories to avoid exceeding LLM context limits.
- **Error handling:** Surface Redmine 403 errors as clear scope-related messages to the LLM.

---

## 5. Redmine Setup Prerequisites

1. Redmine 6.1.0 or higher.
2. REST API enabled: Administration → Settings → API.
3. OAuth application registered: Administration → Applications.
4. Redirect URI set to the FastMCP server's callback endpoint.
