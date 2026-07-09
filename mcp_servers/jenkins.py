import os
import json
from fastmcp import FastMCP
import httpx

mcp = FastMCP("jenkins")

JENKINS_URL = os.environ.get("JENKINS_URL", "").rstrip("/")
JENKINS_USER = os.environ.get("JENKINS_USER", "")
JENKINS_TOKEN = os.environ.get("JENKINS_API_TOKEN", "")


def _auth() -> httpx.BasicAuth | None:
    return httpx.BasicAuth(JENKINS_USER, JENKINS_TOKEN) if JENKINS_USER and JENKINS_TOKEN else None


async def _get(path: str, params: dict | None = None) -> dict | list | str:
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{JENKINS_URL}{path}", params=params, auth=_auth(), timeout=30)
        r.raise_for_status()
        return r.json()


async def _post(path: str, data: dict | None = None, params: dict | None = None) -> dict | str:
    auth = _auth()
    if not auth:
        return {"error": "JENKINS_USER and JENKINS_API_TOKEN env vars required"}
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{JENKINS_URL}{path}", data=data, params=params, auth=auth, timeout=30)
        r.raise_for_status()
        return r.json() if r.text.strip() and r.headers.get("content-type", "").startswith("application/json") else {"status": r.status_code}


async def _get_text(path: str) -> str:
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{JENKINS_URL}{path}", auth=_auth(), timeout=60)
        r.raise_for_status()
        return r.text


# --- Job tools ---

@mcp.tool()
async def list_jobs(folder: str = "") -> list:
    """List Jenkins jobs. Optionally specify a folder path (e.g. 'my-folder/subfolder')."""
    base = f"/job/{'/job/'.join(folder.split('/'))}" if folder else ""
    data = await _get(f"{base}/api/json", {"tree": "jobs[name,url,color,lastBuild[number,result,timestamp]]"})
    return data.get("jobs", [])


@mcp.tool()
async def get_job(job_path: str) -> dict:
    """Get details of a Jenkins job. job_path: slash-separated (e.g. 'folder/job-name')."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    return await _get(f"{path}/api/json")


@mcp.tool()
async def get_job_config(job_path: str) -> str:
    """Get the XML config of a Jenkins job."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    return await _get_text(f"{path}/config.xml")


@mcp.tool()
async def list_builds(job_path: str, limit: int = 10) -> list:
    """List recent builds for a Jenkins job."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    data = await _get(f"{path}/api/json", {"tree": f"builds[number,result,timestamp,duration,displayName]{{0,{limit}}}"})
    return data.get("builds", [])


@mcp.tool()
async def get_build(job_path: str, build_number: int) -> dict:
    """Get details of a specific build."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    return await _get(f"{path}/{build_number}/api/json")


@mcp.tool()
async def get_build_log(job_path: str, build_number: int, tail: int = 0) -> str:
    """Get console output of a build. Use tail=N to get last N bytes only."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    if tail > 0:
        text = await _get_text(f"{path}/{build_number}/logText/progressiveText?start=0")
        return text[-tail:] if len(text) > tail else text
    return await _get_text(f"{path}/{build_number}/consoleText")


@mcp.tool()
async def get_build_test_report(job_path: str, build_number: int) -> dict:
    """Get test results for a build (if available)."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    return await _get(f"{path}/{build_number}/testReport/api/json")


# --- Trigger / control ---

@mcp.tool()
async def trigger_build(job_path: str, parameters: dict | None = None) -> dict:
    """Trigger a Jenkins build. Pass parameters dict for parameterized jobs."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    if parameters:
        return await _post(f"{path}/buildWithParameters", params=parameters)
    return await _post(f"{path}/build")


@mcp.tool()
async def stop_build(job_path: str, build_number: int) -> dict:
    """Stop a running build."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    return await _post(f"{path}/{build_number}/stop")


@mcp.tool()
async def enable_job(job_path: str) -> dict:
    """Enable a disabled Jenkins job."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    return await _post(f"{path}/enable")


@mcp.tool()
async def disable_job(job_path: str) -> dict:
    """Disable a Jenkins job."""
    path = f"/job/{'/job/'.join(job_path.split('/'))}"
    return await _post(f"{path}/disable")


# --- Queue / nodes ---

@mcp.tool()
async def get_queue() -> list:
    """Get the current Jenkins build queue."""
    data = await _get("/queue/api/json")
    return data.get("items", [])


@mcp.tool()
async def list_nodes() -> list:
    """List Jenkins nodes/agents."""
    data = await _get("/computer/api/json", {"tree": "computer[displayName,offline,temporarilyOffline,idle,numExecutors]"})
    return data.get("computer", [])


@mcp.tool()
async def get_node(node_name: str) -> dict:
    """Get details of a Jenkins node."""
    name = "(built-in)" if node_name.lower() in ("master", "built-in") else node_name
    return await _get(f"/computer/{name}/api/json")


# --- Views / system ---

@mcp.tool()
async def list_views() -> list:
    """List Jenkins views."""
    data = await _get("/api/json", {"tree": "views[name,url]"})
    return data.get("views", [])


@mcp.tool()
async def get_view(view_name: str) -> dict:
    """Get details and jobs in a Jenkins view."""
    return await _get(f"/view/{view_name}/api/json")


@mcp.tool()
async def whoami() -> dict:
    """Get current authenticated Jenkins user info."""
    return await _get("/me/api/json")


if __name__ == "__main__":
    mcp.run(transport="stdio")
