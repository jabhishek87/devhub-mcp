from fastmcp import FastMCP
from mcp_servers.middleware import load_subserver
from mcp_servers.gerrit import mcp as gerrit_mcp

# Single unified master process
hub_mcp = FastMCP("Master-MCP-server")

# Load sub-servers via middleware (no namespace prefix — tools keep original names)
load_subserver(hub_mcp, gerrit_mcp)

# To add more sub-servers later:
# from mcp_servers.jira import mcp as jira_mcp
# load_subserver(hub_mcp, jira_mcp, namespace="jira")

if __name__ == "__main__":
    hub_mcp.run(transport="stdio")
