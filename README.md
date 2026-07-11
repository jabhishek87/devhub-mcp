# DevHub MCP Gateway

Unified MCP gateway on k3s. All developer tools exposed as a single MCP endpoint.

## Architecture

```
main.py                    — Master gateway (single MCP process)
mcp_servers/
  middleware.py            — Aggregates local sub-server tools into hub
  proxy.py                 — Proxies remote MCP servers into hub
  gerrit.py                — OpenDev/Gerrit (direct API)
  jenkins.py               — Jenkins CI (direct API)
  jira.py                  — Jira (direct API)
  confluence.py            — Confluence (direct API)
```

### Tool Sources

| Source | Tools | Method |
|--------|-------|--------|
| Gerrit/Gitea | 21 | Direct API calls |
| Jenkins | 17 | Direct API calls |
| Jira | 19 | Direct API calls |
| Confluence | 11 | Direct API calls |
| Excalidraw | 5 | Proxied from remote MCP server |
| healthz | 1 | Built-in |
| **Total** | **74** | |

## Secrets

Create `secrets_rc` (gitignored) with all tokens:

```bash
export GERRIT_USER="your-user"
export GERRIT_HTTP_PASSWORD="your-pass"
export JENKINS_URL="http://jenkins.example.com/"
export JENKINS_USER="your-user"
export JENKINS_API_TOKEN="your-token"
export JIRA_URL="https://jira.example.com"
export JIRA_TOKEN="your-pat"
export CONFLUENCE_URL="https://confluence.example.com"
export CONFLUENCE_TOKEN="your-pat"
```

## Deployment (k3s)

### Build and Deploy

```bash
# Build image
docker build -t devhub-mcp:latest .

# Import into k3s
docker save devhub-mcp:latest | sudo k3s ctr images import -

# Create namespace and apply manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Wait for rollout
kubectl -n devhub rollout status deployment/devhub-gateway
```

### Populate Secrets

After applying the template, patch with real values:

```bash
source secrets_rc
kubectl -n devhub patch secret devhub-secrets --type merge -p "{\"stringData\":{
  \"GERRIT_USER\":\"$GERRIT_USER\",
  \"GERRIT_HTTP_PASSWORD\":\"$GERRIT_HTTP_PASSWORD\",
  \"JENKINS_URL\":\"$JENKINS_URL\",
  \"JENKINS_USER\":\"$JENKINS_USER\",
  \"JENKINS_API_TOKEN\":\"$JENKINS_API_TOKEN\",
  \"JIRA_URL\":\"$JIRA_URL\",
  \"JIRA_TOKEN\":\"$JIRA_TOKEN\",
  \"CONFLUENCE_URL\":\"$CONFLUENCE_URL\",
  \"CONFLUENCE_TOKEN\":\"$CONFLUENCE_TOKEN\"
}}"
```

### Redeploy After Code Changes

```bash
docker build -t devhub-mcp:latest .
docker save devhub-mcp:latest | sudo k3s ctr images import -
kubectl -n devhub rollout restart deployment/devhub-gateway
```

### Service Access

NodePort exposes the gateway on port 30080:

```
http://yow-ajaiswal-lx2.corp.ad.wrs.com:30080/mcp
```

### Verify

```bash
kubectl -n devhub get pods -l app=devhub-gateway
kubectl -n devhub logs deployment/devhub-gateway
```

## MCP Client Config

### Kiro (`~/.kiro/settings/mcp.json`)

```json
{
  "mcpServers": {
    "gateway": {
      "url": "http://yow-ajaiswal-lx2.corp.ad.wrs.com:30080/mcp"
    }
  }
}
```

## Adding a New Sub-Server

**Local (direct API):**
1. Create `mcp_servers/myservice.py` with `mcp = FastMCP("myservice")` and `@mcp.tool()` functions
2. In `main.py`: `load_subserver(hub_mcp, myservice_mcp)`

**Remote (proxy from existing MCP server):**
1. In `main.py`, add URL+token to `REMOTE_SERVERS` dict
2. Tools are discovered and proxied automatically

## Standalone Mode

Each local sub-server runs independently for testing:

```bash
source secrets_rc
python mcp_servers/gerrit.py
python mcp_servers/jenkins.py
python mcp_servers/jira.py
python mcp_servers/confluence.py
```

## Troubleshooting

- **SSL errors**: Internal WRS endpoints use corporate CA. The container uses `verify=False` for these.
- **Stale session after redeploy**: Restart Kiro session to get a fresh MCP session ID.
- **Tool timeout**: Check pod logs — `kubectl -n devhub logs deployment/devhub-gateway`
