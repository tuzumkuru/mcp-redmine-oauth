"""FastMCP server entry point for the Redmine MCP server."""

from __future__ import annotations

import asyncio
import os
from importlib.metadata import version

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from mcp_redmine_oauth.auth import RedmineProvider
from mcp_redmine_oauth.client import RedmineClient
from mcp_redmine_oauth.prompts import register_prompts
from mcp_redmine_oauth.resources import register_resources
from mcp_redmine_oauth.scopes import get_effective_scopes, set_allowed_scopes
from mcp_redmine_oauth.storage import create_token_store
from mcp_redmine_oauth.tools import register_tools

load_dotenv()

# Required configuration
REDMINE_URL = os.environ["REDMINE_URL"]
REDMINE_CLIENT_ID = os.environ["REDMINE_CLIENT_ID"]
REDMINE_CLIENT_SECRET = os.environ["REDMINE_CLIENT_SECRET"]

# Optional configuration
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))
MCP_BASE_URL = os.environ.get("MCP_BASE_URL", f"http://localhost:{MCP_PORT}")
TOKEN_STORE_URL = os.environ.get("TOKEN_STORE_URL")

# FastMCP server (auth added after tool registration so scopes can be auto-collected)
mcp = FastMCP(
    name="Redmine FastMCP Server with OAuth",
    version=version("mcp-redmine-oauth"),
    instructions="MCP server for interacting with Redmine project management.",
)


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> Response:
    return JSONResponse({"status": "ok", "service": "mcp-redmine-oauth"})


# Redmine REST client
redmine = RedmineClient(base_url=REDMINE_URL)

# Register MCP surface — @requires_scopes decorators populate the scope registry as a side effect
register_tools(mcp, redmine)
register_resources(mcp, redmine)
register_prompts(mcp, redmine)

# Optional: filter requested scopes to match what the Redmine OAuth app supports
REDMINE_SCOPES = os.environ.get("REDMINE_SCOPES")
if REDMINE_SCOPES:
    set_allowed_scopes(REDMINE_SCOPES.split())

token_store = create_token_store(TOKEN_STORE_URL)

# Auth provider — scopes auto-collected from @requires_scopes, filtered by REDMINE_SCOPES if set
auth = RedmineProvider(
    redmine_url=REDMINE_URL,
    client_id=REDMINE_CLIENT_ID,
    client_secret=REDMINE_CLIENT_SECRET,
    base_url=MCP_BASE_URL,
    scopes=get_effective_scopes(),
    client_storage=token_store,
    scope_store=token_store,
)
mcp.auth = auth


def main() -> None:
    asyncio.run(
        mcp.run_http_async(
            host=MCP_HOST,
            port=MCP_PORT,
            transport="streamable-http",
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["*"],
                    allow_headers=["*"],
                    expose_headers=["Mcp-Session-Id"],
                ),
            ],
        )
    )


if __name__ == "__main__":
    main()
