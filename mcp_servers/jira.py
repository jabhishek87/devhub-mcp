import os
import json
from fastmcp import FastMCP
import httpx

mcp = FastMCP("jira")

JIRA_URL = os.environ.get("JIRA_URL", "https://jira.wrs.com")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")


def _auth_headers() -> dict:
    if JIRA_TOKEN:
        return {"Authorization": f"Bearer {JIRA_TOKEN}"}
    return {}


async def _get(path: str, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.get(
            f"{JIRA_URL}/rest/api/2{path}",
            params=params,
            headers=_auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


async def _post(path: str, data: dict | None = None) -> dict:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.post(
            f"{JIRA_URL}/rest/api/2{path}",
            json=data,
            headers=_auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json() if r.text.strip() else {"status": "ok"}


async def _put(path: str, data: dict | None = None) -> dict:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.put(
            f"{JIRA_URL}/rest/api/2{path}",
            json=data,
            headers=_auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json() if r.text.strip() else {"status": "ok"}


# --- Server info / users ---


@mcp.tool()
async def jira_get_server_info() -> dict:
    """Get jira server version, time and title"""
    return await _get("/serverInfo")


@mcp.tool()
async def jira_get_current_user() -> dict:
    """Get current jira user"""
    return await _get("/myself")


@mcp.tool()
async def jira_get_user(username: str) -> dict:
    """Get user profile by username.
    Returns displayName, emailAddress, active, deleted, timeZone.
    Useful to check if a user exists or is terminated (displayName prefixed with "Term")."""
    return await _get("/user", {"username": username})


@mcp.tool()
async def jira_search_users(query: str, limit: int = 50) -> list:
    """Search users by username, display name, or email."""
    return await _get("/user/search", {"username": query, "maxResults": limit})


# --- Projects ---


@mcp.tool()
async def jira_search_projects(query: str = "", limit: int = 50) -> list:
    """Search projects by name or key (case-insensitive).
    If query is empty, returns all projects (up to limit)."""
    projects = await _get("/project")
    if query:
        q = query.lower()
        projects = [
            p for p in projects
            if q in p.get("name", "").lower() or q in p.get("key", "").lower()
        ]
    return projects[:limit]


@mcp.tool()
async def jira_list_recent_projects() -> list:
    """List recent projects"""
    return await _get("/project", {"recent": 10})


@mcp.tool()
async def jira_list_components(project: str) -> list:
    """Get project components"""
    return await _get(f"/project/{project}/components")


@mcp.tool()
async def jira_list_issue_types_for_project(project: str) -> list:
    """list available issue types in a jira project"""
    data = await _get(f"/project/{project}")
    return data.get("issueTypes", [])


@mcp.tool()
async def jira_issue_fields_of_type_in_project(project: str, issue_type_id: str, required_only: bool = False) -> dict:
    """get available issue fields for an issue type in a jira project"""
    meta = await _get("/issue/createmeta", {
        "projectKeys": project,
        "issuetypeIds": issue_type_id,
        "expand": "projects.issuetypes.fields",
    })
    projects = meta.get("projects", [])
    if not projects:
        return {"error": f"Project {project} not found"}
    issue_types = projects[0].get("issuetypes", [])
    if not issue_types:
        return {"error": f"Issue type {issue_type_id} not found"}
    fields = issue_types[0].get("fields", {})
    if required_only:
        fields = {k: v for k, v in fields.items() if v.get("required")}
    return fields


@mcp.tool()
async def jira_fields(include_custom_fields: bool = True) -> list:
    """Get jira server fields"""
    fields = await _get("/field")
    if not include_custom_fields:
        fields = [f for f in fields if not f.get("custom")]
    return fields


# --- Issues ---


@mcp.tool()
async def jira_issue_get(issue_id: str, fields: str = "") -> dict:
    """Get issue detail"""
    params = {}
    if fields:
        params["fields"] = fields
    return await _get(f"/issue/{issue_id}", params or None)


@mcp.tool()
async def jira_search_issues(jql: str, fields: str = "summary,status,assignee,priority,issuetype", maxResults: int = 50) -> dict:
    """Search jira issues using JQL"""
    return await _post("/search", {
        "jql": jql,
        "fields": [f.strip() for f in fields.split(",")],
        "maxResults": maxResults,
    })


@mcp.tool()
async def jira_issue_create(fields: dict) -> dict:
    """you need to figure out the fields names using type metadata"""
    return await _post("/issue", {"fields": fields})


@mcp.tool()
async def jira_issue_update(issue_id: str, fields: dict) -> dict:
    """Update a jira issue"""
    return await _put(f"/issue/{issue_id}", {"fields": fields})


@mcp.tool()
async def jira_issue_add_comment(issue_id: str, body: str) -> dict:
    """Add wiki-style formatted comment to Jira issue
    Format: Jira Wiki text formatting only, Markdown not supported !"""
    return await _post(f"/issue/{issue_id}/comment", {"body": body})


@mcp.tool()
async def jira_issue_add_attachment(issue_id: str, content: str, filename: str) -> dict:
    """Add an attachment to a jira issue with specified filename"""
    headers = _auth_headers()
    headers["X-Atlassian-Token"] = "no-check"
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.post(
            f"{JIRA_URL}/rest/api/2/issue/{issue_id}/attachments",
            headers=headers,
            files={"file": (filename, content.encode(), "application/octet-stream")},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def jira_issue_get_attachment(attachment_id: str) -> dict:
    """Get attachment content, attachment_id can be found in issue detail `attachment` field.
    If filesize exceeds 20kb, only url is returned."""
    meta = await _get(f"/attachment/{attachment_id}")
    size = meta.get("size", 0)
    if size > 20480:
        return {"filename": meta.get("filename"), "size": size, "url": meta.get("content"), "note": "File too large, only URL returned"}
    # Fetch content
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.get(meta.get("content", ""), headers=_auth_headers(), timeout=30)
        r.raise_for_status()
        return {"filename": meta.get("filename"), "size": size, "content": r.text[:20480]}


@mcp.tool()
async def jira_issue_get_available_transitions(issue_id: str) -> list:
    """Get available transitions for an issue."""
    data = await _get(f"/issue/{issue_id}/transitions")
    return data.get("transitions", [])


@mcp.tool()
async def jira_issue_transition(issue_id: str, transition: str) -> dict:
    """Transition an issue to a new status."""
    return await _post(f"/issue/{issue_id}/transitions", {"transition": {"id": transition}})


if __name__ == "__main__":
    mcp.run(transport="stdio")
