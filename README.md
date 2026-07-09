# DevHub MCP Server

Unified MCP gateway. All developer tools exposed as a single MCP stdio endpoint via Docker.

## Architecture

```
main.py                    — Master gateway (single MCP stdio process)
mcp_servers/
  middleware.py            — Aggregates local sub-server tools into hub
  proxy.py                 — Proxies remote MCP servers into hub
  gerrit.py                — OpenDev/Gerrit (direct API, runs standalone too)
  jenkins.py               — Jenkins CI (direct API, runs standalone too)
```

### Tool Sources

| Source | Tools | Method |
|--------|-------|--------|
| Gerrit/Gitea | 21 | Direct API calls |
| Jenkins | 17 | Direct API calls |
| Confluence | 11 | Proxied from remote MCP server |
| Jira | 19 | Proxied from remote MCP server |
| Excalidraw | 5 | Proxied from remote MCP server |
| healthz | 1 | Built-in |
| **Total** | **74** | |

## Secrets

All secrets stored in `~/.secrets` and sourced into shell:

```bash
# ~/.secrets
export GERRIT_USER="your-user"
export GERRIT_HTTP_PASSWORD="your-pass"
export JENKINS_URL="http://jenkins.example.com/"
export JENKINS_USER="your-user"
export JENKINS_API_TOKEN="your-token"
```

Source before use: `source ~/.secrets`

No secrets needed for Confluence, Jira, or Excalidraw — they're proxied from public MCP endpoints that handle their own auth.

## Quick Start

```bash
source ~/.secrets
make build
make test-docker
```

## Makefile

```bash
make build       # Build Docker image
make run         # Run gateway (stdio)
make up          # docker compose up -d
make down        # docker compose down
make test        # Tests locally
make test-docker # Tests in container
make healthz     # Health check
make lint        # Lint all files
make clean       # Remove image
make help        # Show targets
```

## MCP Client Config

### Kiro (`~/.kiro/settings/mcp.json`)

```json
{
  "mcpServers": {
    "gateway": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "-i", "gateway"],
      "env": {
        "GERRIT_USER": "${GERRIT_USER}",
        "GERRIT_HTTP_PASSWORD": "${GERRIT_HTTP_PASSWORD}",
        "JENKINS_URL": "${JENKINS_URL}",
        "JENKINS_USER": "${JENKINS_USER}",
        "JENKINS_API_TOKEN": "${JENKINS_API_TOKEN}"
      },
      "type": "stdio",
      "timeout": 120000
    }
  }
}
```

## Adding a New Sub-Server

**Local (direct API):**
1. Create `mcp_servers/myservice.py` with `mcp = FastMCP("myservice")` and `@mcp.tool()` functions
2. In `main.py`: `load_subserver(hub_mcp, myservice_mcp, namespace="myservice")`

**Remote (proxy from existing MCP server):**
1. In `main.py`, add URL to `REMOTE_SERVERS` dict
2. That's it — tools are discovered and proxied automatically

## Standalone Mode

Each local sub-server runs independently:
```bash
python mcp_servers/gerrit.py
python mcp_servers/jenkins.py
```
