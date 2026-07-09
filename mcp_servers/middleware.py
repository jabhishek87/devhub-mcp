"""Middleware to aggregate tools from sub-server FastMCP instances
into a master hub server.

Each sub-server (e.g. gerrit.py) keeps its own FastMCP instance with
@mcp.tool() decorators and can run standalone. This middleware imports
those instances and re-registers their tools onto the hub with optional
namespace prefixing.
"""

import asyncio
from fastmcp import FastMCP


def load_subserver(hub: FastMCP, subserver: FastMCP, namespace: str = ""):
    """Register all tools from a sub-server onto the hub.

    Args:
        hub: The master FastMCP instance.
        subserver: A sub-server FastMCP instance (e.g. gerrit.mcp).
        namespace: Optional prefix for tool names (e.g. "gerrit" ->
                   "gerrit_search_repos"). Empty string means no prefix.
    """
    prefix = f"{namespace}_" if namespace else ""
    tools = asyncio.run(subserver.list_tools())

    for tool in tools:
        tool_name = f"{prefix}{tool.name}" if prefix else tool.name
        hub.tool(name=tool_name)(tool.fn)
