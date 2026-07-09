import os
import json
from urllib.parse import quote
from fastmcp import FastMCP
import httpx

mcp = FastMCP("opendev")
GITEA = "https://opendev.org/api/v1"
GERRIT = "https://review.opendev.org"
GERRIT_USER = os.environ.get("GERRIT_USER", "")
GERRIT_PASS = os.environ.get("GERRIT_HTTP_PASSWORD", "")


async def _gitea(path: str, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{GITEA}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()


def _gerrit_auth() -> httpx.BasicAuth | None:
    return httpx.BasicAuth(GERRIT_USER, GERRIT_PASS) if GERRIT_USER and GERRIT_PASS else None


def _parse_gerrit(text: str):
    if text.startswith(")]}'"):
        text = text[5:]
    return json.loads(text)


async def _gerrit_get(path: str, params: dict | None = None):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{GERRIT}{path}", params=params, auth=_gerrit_auth(), timeout=30)
        r.raise_for_status()
        return _parse_gerrit(r.text)


async def _gerrit_post(path: str, data: dict | None = None):
    auth = _gerrit_auth()
    if not auth:
        return {"error": "GERRIT_USER and GERRIT_HTTP_PASSWORD env vars required for write operations"}
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{GERRIT}/a{path}", json=data, auth=auth, timeout=30)
        r.raise_for_status()
        return _parse_gerrit(r.text) if r.text.strip() else {"status": "ok"}


async def _gerrit_put(path: str, data: dict | None = None):
    auth = _gerrit_auth()
    if not auth:
        return {"error": "GERRIT_USER and GERRIT_HTTP_PASSWORD env vars required for write operations"}
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{GERRIT}/a{path}", json=data, auth=auth, timeout=30)
        r.raise_for_status()
        return _parse_gerrit(r.text) if r.text.strip() else {"status": "ok"}


async def _gerrit_delete(path: str):
    auth = _gerrit_auth()
    if not auth:
        return {"error": "GERRIT_USER and GERRIT_HTTP_PASSWORD env vars required for write operations"}
    async with httpx.AsyncClient() as c:
        r = await c.delete(f"{GERRIT}/a{path}", auth=auth, timeout=30)
        r.raise_for_status()
        return {"status": "ok"}


# --- Gitea tools (read-only) ---

@mcp.tool()
async def search_repos(query: str, limit: int = 10) -> dict:
    """Search OpenDev repositories."""
    return await _gitea("/repos/search", {"q": query, "limit": limit})


@mcp.tool()
async def get_repo(owner: str, repo: str) -> dict:
    """Get details of an OpenDev repository."""
    return await _gitea(f"/repos/{owner}/{repo}")


@mcp.tool()
async def list_repo_branches(owner: str, repo: str) -> list:
    """List branches of an OpenDev repository."""
    return await _gitea(f"/repos/{owner}/{repo}/branches")


@mcp.tool()
async def get_file_contents(owner: str, repo: str, filepath: str, ref: str = "") -> dict:
    """Get file contents from an OpenDev repository."""
    params = {"ref": ref} if ref else None
    return await _gitea(f"/repos/{owner}/{repo}/contents/{filepath}", params)


@mcp.tool()
async def list_repo_commits(owner: str, repo: str, sha: str = "", limit: int = 10) -> list:
    """List commits in an OpenDev repository."""
    params = {"limit": limit}
    if sha:
        params["sha"] = sha
    return await _gitea(f"/repos/{owner}/{repo}/commits", params)


@mcp.tool()
async def list_orgs(limit: int = 20) -> dict:
    """List organizations on OpenDev."""
    return await _gitea("/orgs", {"limit": limit})


@mcp.tool()
async def list_org_repos(org: str, limit: int = 20) -> list:
    """List repositories for an OpenDev organization."""
    return await _gitea(f"/orgs/{org}/repos", {"limit": limit})


# --- Gerrit read tools ---

@mcp.tool()
async def gerrit_search_changes(query: str, limit: int = 10) -> list:
    """Search Gerrit changes. Example queries: 'status:open project:openstack/nova', 'owner:self status:merged'."""
    return await _gerrit_get("/changes/", {"q": query, "n": limit})


@mcp.tool()
async def gerrit_get_change(change_id: str) -> dict:
    """Get details of a Gerrit change."""
    return await _gerrit_get(f"/changes/{change_id}/detail")


@mcp.tool()
async def gerrit_list_change_files(change_id: str, revision: str = "current") -> dict:
    """List files modified in a Gerrit change revision."""
    return await _gerrit_get(f"/changes/{change_id}/revisions/{revision}/files")


@mcp.tool()
async def gerrit_get_file_diff(change_id: str, filepath: str, revision: str = "current") -> dict:
    """Get the diff of a specific file in a Gerrit change."""
    return await _gerrit_get(f"/changes/{change_id}/revisions/{revision}/files/{quote(filepath, safe='')}/diff")


@mcp.tool()
async def gerrit_list_projects(prefix: str = "", limit: int = 20) -> dict:
    """List Gerrit projects. Optionally filter by prefix (e.g. 'openstack/')."""
    params = {"n": limit}
    if prefix:
        params["p"] = prefix
    return await _gerrit_get("/projects/", params)


@mcp.tool()
async def gerrit_get_project(project: str) -> dict:
    """Get details of a Gerrit project."""
    return await _gerrit_get(f"/projects/{quote(project, safe='')}")


# --- Gerrit write tools (require auth) ---

@mcp.tool()
async def gerrit_review(change_id: str, message: str, labels: dict | None = None, revision: str = "current") -> dict:
    """Post a review on a Gerrit change. labels example: {'Code-Review': +1}."""
    data = {"message": message}
    if labels:
        data["labels"] = labels
    return await _gerrit_post(f"/changes/{change_id}/revisions/{revision}/review", data)


@mcp.tool()
async def gerrit_add_reviewer(change_id: str, reviewer: str) -> dict:
    """Add a reviewer to a Gerrit change. reviewer can be a username or email."""
    return await _gerrit_post(f"/changes/{change_id}/reviewers", {"reviewer": reviewer})


@mcp.tool()
async def gerrit_remove_reviewer(change_id: str, reviewer: str) -> dict:
    """Remove a reviewer from a Gerrit change."""
    return await _gerrit_delete(f"/changes/{change_id}/reviewers/{reviewer}")


@mcp.tool()
async def gerrit_abandon_change(change_id: str, message: str = "") -> dict:
    """Abandon a Gerrit change."""
    return await _gerrit_post(f"/changes/{change_id}/abandon", {"message": message} if message else {})


@mcp.tool()
async def gerrit_restore_change(change_id: str, message: str = "") -> dict:
    """Restore an abandoned Gerrit change."""
    return await _gerrit_post(f"/changes/{change_id}/restore", {"message": message} if message else {})


@mcp.tool()
async def gerrit_submit_change(change_id: str) -> dict:
    """Submit (merge) an approved Gerrit change."""
    return await _gerrit_post(f"/changes/{change_id}/submit")


@mcp.tool()
async def gerrit_set_topic(change_id: str, topic: str) -> dict:
    """Set the topic on a Gerrit change."""
    return await _gerrit_put(f"/changes/{change_id}/topic", {"topic": topic})


@mcp.tool()
async def gerrit_set_hashtags(change_id: str, add: list[str] | None = None, remove: list[str] | None = None) -> dict:
    """Add/remove hashtags on a Gerrit change."""
    data = {}
    if add:
        data["add"] = add
    if remove:
        data["remove"] = remove
    return await _gerrit_post(f"/changes/{change_id}/hashtags", data)


if __name__ == "__main__":
    mcp.run(transport="stdio")
