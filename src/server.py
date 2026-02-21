"""FastMCP server entry point for the Redmine MCP server."""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from auth import RedmineProvider
from client import RedmineClient
from tools import register_tools

load_dotenv()

# Required configuration
REDMINE_URL = os.environ["REDMINE_URL"]
REDMINE_CLIENT_ID = os.environ["REDMINE_CLIENT_ID"]
REDMINE_CLIENT_SECRET = os.environ["REDMINE_CLIENT_SECRET"]

# Optional configuration
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))
MCP_BASE_URL = os.environ.get("MCP_BASE_URL", f"http://localhost:{MCP_PORT}")
REDMINE_SCOPES = os.environ.get("REDMINE_SCOPES", "").split() or None

# Auth provider
auth = RedmineProvider(
    redmine_url=REDMINE_URL,
    client_id=REDMINE_CLIENT_ID,
    client_secret=REDMINE_CLIENT_SECRET,
    base_url=MCP_BASE_URL,
    scopes=REDMINE_SCOPES,
)

# FastMCP server
mcp = FastMCP(
    name="Redmine MCP",
    instructions="MCP server for interacting with Redmine project management.",
    auth=auth,
)

# Redmine REST client
redmine = RedmineClient(base_url=REDMINE_URL)

# Register MCP surface
register_tools(mcp, redmine)


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
