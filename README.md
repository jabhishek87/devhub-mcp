# devhub-mcp

MCP (Model Context Protocol) server for OpenDev Gitea and Gerrit APIs. Exposes repository browsing, code review, and change management as tools for LLM agents.

## Tools

### Gitea (read-only)
| Tool | Description |
|------|-------------|
| `search_repos` | Search OpenDev repositories |
| `get_repo` | Get repository details |
| `list_repo_branches` | List branches |
| `get_file_contents` | Get file from repo |
| `list_repo_commits` | List commits |
| `list_orgs` | List organizations |
| `list_org_repos` | List org repositories |

### Gerrit (read)
| Tool | Description |
|------|-------------|
| `gerrit_search_changes` | Search changes by query |
| `gerrit_get_change` | Get change details |
| `gerrit_list_change_files` | List modified files |
| `gerrit_get_file_diff` | Get file diff |
| `gerrit_list_projects` | List projects |
| `gerrit_get_project` | Get project details |

### Gerrit (write — requires auth)
| Tool | Description |
|------|-------------|
| `gerrit_review` | Post review with labels |
| `gerrit_add_reviewer` | Add reviewer |
| `gerrit_remove_reviewer` | Remove reviewer |
| `gerrit_abandon_change` | Abandon change |
| `gerrit_restore_change` | Restore abandoned change |
| `gerrit_submit_change` | Submit (merge) change |
| `gerrit_set_topic` | Set topic |
| `gerrit_set_hashtags` | Add/remove hashtags |

## Architecture

```
main.py                    — Master hub (single MCP process)
mcp_servers/
  middleware.py            — Aggregates sub-server tools into hub
  gerrit.py                — OpenDev/Gerrit sub-server (runs standalone too)
```

Adding a new sub-server:
```python
# mcp_servers/jira.py — define tools with @mcp.tool()
# main.py:
from mcp_servers.jira import mcp as jira_mcp
load_subserver(hub_mcp, jira_mcp, namespace="jira")
```

## Setup

### Local

```bash
python3.12 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
python main.py
```

### Docker

```bash
docker build -t mcp-server .
docker run --rm -e GERRIT_USER=myuser -e GERRIT_HTTP_PASSWORD=mypass mcp-server
```

### Docker Compose

```bash
docker compose up
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GERRIT_USER` | For write ops | Gerrit HTTP username |
| `GERRIT_HTTP_PASSWORD` | For write ops | Gerrit HTTP password |

## MCP Client Configuration

### Kiro CLI (`~/.kiro/settings/mcp.json`)

```json
{
  "mcpServers": {
    "opendev": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "-e", "GERRIT_USER", "-e", "GERRIT_HTTP_PASSWORD", "mcp-server"],
      "env": {
        "GERRIT_USER": "your-user",
        "GERRIT_HTTP_PASSWORD": "your-pass"
      }
    }
  }
}
```

### Standalone (gerrit.py only)

```bash
cd mcp_servers && python gerrit.py
```

## Transport

Default: `stdio` (for agent integration). The server reads JSON-RPC from stdin and writes to stdout.
