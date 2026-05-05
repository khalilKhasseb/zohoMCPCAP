"""
MCP server entry point for Zoho Campaigns.

Runs via stdio — Claude Desktop manages the process lifecycle.
"""

import asyncio
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .api import ZohoCampaignsAPI
from .tools import register_tools


def main() -> None:
    server = Server("zoho-campaigns")

    try:
        api = ZohoCampaignsAPI()
    except Exception as e:
        print(f"Failed to initialize Zoho Campaigns API: {e}", file=sys.stderr)
        print("Have you run setup.sh yet? It only takes a minute.", file=sys.stderr)
        sys.exit(1)

    register_tools(server, api)

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
