import os
from fastmcp import FastMCP
from mcp_servers.middleware import load_subserver
from mcp_servers.proxy import load_remote_server
from mcp_servers.gerrit import mcp as gerrit_mcp
from mcp_servers.jenkins import mcp as jenkins_mcp

# Single unified master process
hub_mcp = FastMCP("Master-MCP-server")

# Local sub-servers (direct API calls)
load_subserver(hub_mcp, gerrit_mcp)
load_subserver(hub_mcp, jenkins_mcp, namespace="jenkins")

# Remote MCP servers (proxied through gateway)
REMOTE_SERVERS = {
    "confluence": os.environ.get("CONFLUENCE_MCP_URL", "https://confluence.wndrvr.cloud/mcp"),
    "jira": os.environ.get("JIRA_MCP_URL", "https://jira.wndrvr.cloud/mcp"),
    "excalidraw": os.environ.get("EXCALIDRAW_MCP_URL", "https://mcp.excalidraw.com"),
}

for name, url in REMOTE_SERVERS.items():
    try:
        count = load_remote_server(hub_mcp, url)
        print(f"[gateway] Proxied {name}: {count} tools")
    except Exception as e:
        print(f"[gateway] WARNING: Failed to connect to {name} ({url}): {e}")


@hub_mcp.tool()
async def healthz() -> dict:
    """Health check. Returns server status and loaded tool count."""
    tools = await hub_mcp.list_tools()
    return {
        "status": "ok",
        "server": "Master-MCP-server",
        "tools_loaded": len(tools),
    }


if __name__ == "__main__":
    hub_mcp.run(transport="stdio")
