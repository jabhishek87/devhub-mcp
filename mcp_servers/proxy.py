"""Proxy middleware — connects to remote MCP servers and re-exposes their tools on the hub."""

import asyncio
import json
from typing import Any
from fastmcp import FastMCP
from fastmcp.client import Client


def load_remote_server(hub: FastMCP, url: str, namespace: str = "", timeout: int = 15):
    """Connect to a remote MCP server, discover tools, register proxies on hub.

    Args:
        hub: The master FastMCP instance.
        url: Remote MCP server URL (SSE/streamable endpoint).
        namespace: Prefix for tool names.
        timeout: Connection timeout in seconds.
    """

    async def discover():
        async with Client(url) as c:
            return await c.list_tools()

    tools = asyncio.run(discover())
    prefix = f"{namespace}_" if namespace else ""

    for tool in tools:
        tool_name = f"{prefix}{tool.name}"
        tool_desc = tool.description or ""
        remote_tool_name = tool.name
        remote_url = url

        # Create proxy that accepts a single JSON arguments dict
        # This avoids the **kwargs issue with FastMCP tool registration
        def make_proxy(r_url, r_tool_name, desc):
            async def proxy(arguments: str = "{}") -> str:
                """Proxy call to remote MCP server. Pass arguments as JSON string."""
                args = json.loads(arguments) if arguments else {}
                async with Client(r_url) as c:
                    result = await c.call_tool(r_tool_name, args)
                    if hasattr(result, 'content') and result.content:
                        texts = [ct.text for ct in result.content if hasattr(ct, 'text')]
                        return texts[0] if len(texts) == 1 else json.dumps(texts)
                    return json.dumps(str(result))
            proxy.__doc__ = desc
            return proxy

        fn = make_proxy(remote_url, remote_tool_name, tool_desc)
        hub.tool(name=tool_name)(fn)

    return len(tools)
