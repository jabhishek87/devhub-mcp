"""Container health and tool registration tests."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import hub_mcp

EXPECTED_LOCAL_TOOLS = [
    # gerrit/gitea
    "search_repos", "get_repo", "list_repo_branches", "get_file_contents",
    "list_repo_commits", "list_orgs", "list_org_repos",
    "gerrit_search_changes", "gerrit_get_change", "gerrit_list_change_files",
    "gerrit_get_file_diff", "gerrit_list_projects", "gerrit_get_project",
    "gerrit_review", "gerrit_add_reviewer", "gerrit_remove_reviewer",
    "gerrit_abandon_change", "gerrit_restore_change", "gerrit_submit_change",
    "gerrit_set_topic", "gerrit_set_hashtags",
    # jenkins
    "jenkins_list_jobs", "jenkins_get_job", "jenkins_get_job_config",
    "jenkins_list_builds", "jenkins_get_build", "jenkins_get_build_log",
    "jenkins_get_build_test_report", "jenkins_trigger_build",
    "jenkins_stop_build", "jenkins_enable_job", "jenkins_disable_job",
    "jenkins_get_queue", "jenkins_list_nodes", "jenkins_get_node",
    "jenkins_list_views", "jenkins_get_view", "jenkins_whoami",
    # health
    "healthz",
]

# Remote proxied tools (discovered at startup — names come from remote servers)
EXPECTED_REMOTE_PREFIXES = ["confluence_", "jira_"]
EXPECTED_EXCALIDRAW_TOOLS = ["read_me", "create_view", "export_to_excalidraw", "save_checkpoint", "read_checkpoint"]


async def run_tests():
    errors = []

    tools = await hub_mcp.list_tools()
    names = [t.name for t in tools]

    # Check local tools present
    missing_local = [t for t in EXPECTED_LOCAL_TOOLS if t not in names]
    if missing_local:
        errors.append(f"Missing local tools: {missing_local}")

    # Check remote proxied tools present
    for prefix in EXPECTED_REMOTE_PREFIXES:
        proxied = [n for n in names if n.startswith(prefix)]
        if not proxied:
            errors.append(f"No proxied tools with prefix '{prefix}' — remote server may be unreachable")

    # Excalidraw tools (no prefix)
    missing_excalidraw = [t for t in EXPECTED_EXCALIDRAW_TOOLS if t not in names]
    if missing_excalidraw:
        errors.append(f"Missing excalidraw tools: {missing_excalidraw} — remote server may be unreachable")

    # Healthz
    result = await hub_mcp.call_tool("healthz", {})
    data = json.loads(result.content[0].text)
    if data.get("status") != "ok":
        errors.append(f"Healthz bad status: {data}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        remote_count = len(names) - len(EXPECTED_LOCAL_TOOLS)
        print(f"OK: {len(names)} tools ({len(EXPECTED_LOCAL_TOOLS)} local + {remote_count} proxied), healthz passed")


if __name__ == "__main__":
    asyncio.run(run_tests())
