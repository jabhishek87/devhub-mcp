import os
import json
from fastmcp import FastMCP
import httpx

mcp = FastMCP("confluence")

CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "https://confluence.wrs.com")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")


def _auth_headers() -> dict:
    if CONFLUENCE_TOKEN:
        return {"Authorization": f"Bearer {CONFLUENCE_TOKEN}"}
    return {}


async def _get(path: str, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.get(
            f"{CONFLUENCE_URL}/rest/api{path}",
            params=params,
            headers=_auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


async def _post(path: str, data: dict | None = None) -> dict:
    headers = _auth_headers()
    headers["Content-Type"] = "application/json"
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.post(
            f"{CONFLUENCE_URL}/rest/api{path}",
            json=data,
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        return r.json() if r.text.strip() else {"status": "ok"}


async def _put(path: str, data: dict | None = None) -> dict:
    headers = _auth_headers()
    headers["Content-Type"] = "application/json"
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.put(
            f"{CONFLUENCE_URL}/rest/api{path}",
            json=data,
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        return r.json() if r.text.strip() else {"status": "ok"}


async def _delete(path: str) -> dict:
    async with httpx.AsyncClient(verify=False) as c:
        r = await c.delete(
            f"{CONFLUENCE_URL}/rest/api{path}",
            headers=_auth_headers(),
            timeout=30,
        )
        r.raise_for_status()
        return {"status": "ok"}


# --- User / Spaces ---


@mcp.tool()
async def confluence_current_user() -> dict:
    """Get current user in confluence."""
    return await _get("/user/current")


@mcp.tool()
async def confluence_list_spaces(start: int = 0, limit: int = 25, expand: str = "", include_archived: bool = False) -> dict:
    """List all accessible spaces in confluence."""
    params = {"start": start, "limit": limit}
    if expand:
        params["expand"] = expand
    if not include_archived:
        params["status"] = "current"
    return await _get("/space", params)


# --- Pages ---


@mcp.tool()
async def confluence_get_page(page_id: str = "", url: str = "", space: str = "", title: str = "", expand: str = "body.storage,version") -> dict:
    """Get a page from Confluence. Accepts page_id, url, or space+title."""
    if page_id:
        return await _get(f"/content/{page_id}", {"expand": expand})
    if url:
        # Extract page ID from URL patterns
        # /pages/viewpage.action?pageId=12345 or /display/SPACE/Title
        if "pageId=" in url:
            pid = url.split("pageId=")[1].split("&")[0]
            return await _get(f"/content/{pid}", {"expand": expand})
        # Try /display/SPACE/Title pattern
        parts = url.rstrip("/").split("/display/")
        if len(parts) == 2:
            sp_title = parts[1].split("/", 1)
            if len(sp_title) == 2:
                space, title = sp_title[0], sp_title[1].replace("+", " ")
    if space and title:
        data = await _get("/content", {"spaceKey": space, "title": title, "expand": expand})
        results = data.get("results", [])
        if results:
            return results[0]
        return {"error": f"Page not found: space={space}, title={title}"}
    return {"error": "Provide page_id, url, or space+title"}


@mcp.tool()
async def confluence_get_page_children(page_id: str, start: int = 0, limit: int = 25, expand: str = "") -> dict:
    """Get child pages of a page. Returns id, title, and labels by default (lightweight). Use expand=body.storage for full content."""
    params = {"start": start, "limit": limit}
    if expand:
        params["expand"] = expand
    return await _get(f"/content/{page_id}/child/page", params)


@mcp.tool()
async def confluence_create_page(space: str, title: str, body: str, parent_id: str = "") -> dict:
    """Create a page in confluence."""
    data = {
        "type": "page",
        "title": title,
        "space": {"key": space},
        "body": {"storage": {"value": body, "representation": "storage"}},
    }
    if parent_id:
        data["ancestors"] = [{"id": parent_id}]
    return await _post("/content", data)


@mcp.tool()
async def confluence_update_page(page_id: str, title: str, body: str, parent_id: str = "") -> dict:
    """Update a page in confluence."""
    # Get current version
    current = await _get(f"/content/{page_id}", {"expand": "version"})
    version = current.get("version", {}).get("number", 0) + 1
    data = {
        "type": "page",
        "title": title,
        "version": {"number": version},
        "body": {"storage": {"value": body, "representation": "storage"}},
    }
    if parent_id:
        data["ancestors"] = [{"id": parent_id}]
    return await _put(f"/content/{page_id}", data)


@mcp.tool()
async def confluence_move_page(space_key: str, page_id: str, target_page_id: str) -> dict:
    """Move a page in confluence."""
    # Move by updating ancestors
    current = await _get(f"/content/{page_id}", {"expand": "version"})
    version = current.get("version", {}).get("number", 0) + 1
    data = {
        "type": "page",
        "title": current.get("title", ""),
        "version": {"number": version},
        "ancestors": [{"id": target_page_id}],
    }
    return await _put(f"/content/{page_id}", data)


# --- Labels ---


@mcp.tool()
async def confluence_set_page_label(page_id: str, label: str) -> dict:
    """Set a page label in confluence."""
    return await _post(f"/content/{page_id}/label", [{"prefix": "global", "name": label}])


@mcp.tool()
async def confluence_remove_page_label(page_id: str, label: str) -> dict:
    """Remove a page label in confluence."""
    return await _delete(f"/content/{page_id}/label/{label}")


# --- Search ---


@mcp.tool()
async def confluence_content_search(cql: str, start: int = 0, limit: int = 25, expand: str = "", excerpt: str = "") -> dict:
    """Use structured queries to search for content in Confluence."""
    params = {"cql": cql, "start": start, "limit": limit}
    if expand:
        params["expand"] = expand
    if excerpt:
        params["excerpt"] = excerpt
    return await _get("/content/search", params)


# --- Attachments ---


@mcp.tool()
async def confluence_get_attachments(page_id: str) -> dict:
    """Get attachments on a page."""
    return await _get(f"/content/{page_id}/child/attachment")


if __name__ == "__main__":
    mcp.run(transport="stdio")
