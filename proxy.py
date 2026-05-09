"""
LoopForge proxy — forwards A2A requests to the deployed agent.

Compatible with modern Starlette/FastAPI/httpx versions.
Tested with:
- starlette >= 0.36
- httpx >= 0.27
- uvicorn >= 0.29
"""

import os
import asyncio
from contextlib import asynccontextmanager

import httpx
import uvicorn

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

AGENT_URL = (
    os.getenv("AGENT_URL")
    or os.getenv("RENDER_URL")
    or "https://sarangmenon555-loopforge.hf.space"
).rstrip("/")

PROXY_PORT = int(os.getenv("PROXY_PORT", "9009"))

# Reuse one shared async client (important for newer httpx versions)
http_client: httpx.AsyncClient | None = None


# -----------------------------------------------------------------------------
# WARMUP
# -----------------------------------------------------------------------------

async def warmup():
    """
    Wait for the remote agent to become available.
    """
    print(f"[proxy] Warming up {AGENT_URL} ...")

    global http_client

    for attempt in range(20):
        try:
            resp = await http_client.get(
                f"{AGENT_URL}/.well-known/agent-card.json"
            )

            if resp.status_code == 200:
                print(f"[proxy] Agent awake after {attempt + 1} attempt(s)")
                return

            print(
                f"[proxy] Attempt {attempt + 1}/20 "
                f"returned status {resp.status_code}"
            )

        except Exception as e:
            print(f"[proxy] Warmup {attempt + 1}/20 failed: {e}")

        await asyncio.sleep(5)

    print("[proxy] Warmup finished")


# -----------------------------------------------------------------------------
# KEEP ALIVE
# -----------------------------------------------------------------------------

async def keep_alive():
    """
    Periodically ping the deployed agent so it doesn't sleep.
    """
    await asyncio.sleep(30)

    global http_client

    while True:
        try:
            await http_client.get(
                f"{AGENT_URL}/.well-known/agent-card.json"
            )
            print("[proxy] Keep-alive ping sent")

        except Exception as e:
            print(f"[proxy] Keep-alive failed: {e}")

        await asyncio.sleep(240)


# -----------------------------------------------------------------------------
# LIFESPAN
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: Starlette):
    global http_client

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=30.0, read=300.0, write=300.0, pool=300.0),
        follow_redirects=True,
    )

    # FIX: Run warmup in the background so it doesn't block the server start
    warmup_task = asyncio.create_task(warmup()) 
    keepalive_task = asyncio.create_task(keep_alive())

    try:
        yield
    finally:
        warmup_task.cancel()
        keepalive_task.cancel()
        await http_client.aclose()

        try:
            await keepalive_task
        except asyncio.CancelledError:
            pass

        await http_client.aclose()


# -----------------------------------------------------------------------------
# PROXY HANDLER
# -----------------------------------------------------------------------------

HOP_BY_HOP_HEADERS = {
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


async def proxy_handler(request: Request):
    """
    Forward all incoming requests to the remote agent.
    """

    global http_client

    path = request.url.path

    target_url = f"{AGENT_URL}{path}"

    if request.url.query:
        target_url += f"?{request.url.query}"

    try:
        body = await request.body()

        # Filter unsupported hop-by-hop headers
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in HOP_BY_HOP_HEADERS
        }

        resp = await http_client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )

        # Remove problematic response headers
        response_headers = {
            k: v
            for k, v in resp.headers.items()
            if k.lower() not in HOP_BY_HOP_HEADERS
        }

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=response_headers,
            media_type=resp.headers.get("content-type"),
        )

    except httpx.RequestError as e:
        return Response(
            content=f"Proxy request error: {str(e)}",
            status_code=502,
        )

    except Exception as e:
        return Response(
            content=f"Unexpected proxy error: {str(e)}",
            status_code=500,
        )


# -----------------------------------------------------------------------------
# ROUTES
# -----------------------------------------------------------------------------

METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]

app = Starlette(
    debug=False,
    lifespan=lifespan,
    routes=[
        Route("/", proxy_handler, methods=METHODS),
        Route("/{path:path}", proxy_handler, methods=METHODS),
    ],
)

# -----------------------------------------------------------------------------
# ENTRYPOINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[proxy] Starting proxy on port {PROXY_PORT}")
    print(f"[proxy] Forwarding to: {AGENT_URL}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PROXY_PORT,
        proxy_headers=True,
    )