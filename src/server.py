"""FastMCP server entry point for the Redmine MCP server."""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from fastmcp import FastMCP

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

# Build the base URL for OAuth redirect
BASE_URL = f"http://{MCP_HOST}:{MCP_PORT}"

# Auth provider
auth = RedmineProvider(
    redmine_url=REDMINE_URL,
    client_id=REDMINE_CLIENT_ID,
    client_secret=REDMINE_CLIENT_SECRET,
    base_url=BASE_URL,
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
        )
    )


if __name__ == "__main__":
    main()
