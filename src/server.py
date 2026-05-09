"""
A2A server entry point for LoopForge - Updated for A2A SDK 1.0+
"""

import argparse
import os
import json
from typing import Optional

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Agent Card Definition
AGENT_CARD = {
    "id": "loopforge",
    "name": "LoopForge",
    "description": "LoopForge is a self-correcting, tool-using coding agent powered by Gemini 2.0 Flash. It iteratively plans, writes, runs, and fixes code until the task is solved.",
    "version": "1.0.0",
    "default_input_modes": ["text"],
    "default_output_modes": ["text"],
    "capabilities": {
        "streaming": True
    },
    "skills": [
        {
            "id": "coding-agent",
            "name": "Coding Agent",
            "description": "Solves software engineering tasks: bug fixes (SWE-bench Pro), shell tasks (Terminal Bench 2.0), networking (NetArena). Uses Gemini Flash with run_python, run_shell, write_file, read_file.",
            "tags": ["coding", "swe", "terminal", "networking", "python", "bash"],
            "examples": [
                "Fix the failing unit test in this Python file.",
                "Write a shell script that monitors CPU usage every 5 seconds.",
                "Implement a TCP server that echoes messages back to the client."
            ]
        }
    ]
}


async def agent_card_handler(request):
    """Serve agent card at /.well-known/agent-card.json"""
    return JSONResponse(AGENT_CARD)


async def rpc_handler(request):
    """Handle JSON-RPC 2.0 requests"""
    try:
        if request.method == "POST":
            body = await request.json()
        else:
            return JSONResponse({"error": "Method not allowed"}, status_code=405)
    except Exception as e:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            status_code=400
        )
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    # Simple RPC methods for testing
    if method == "agent_info":
        result = {
            "name": "LoopForge",
            "version": "1.0.0",
            "status": "ready"
        }
    elif method == "test":
        result = {"status": "ok", "message": "Agent is running"}
    else:
        result = {
            "status": "ok",
            "method": method,
            "params": params,
            "note": "Method not implemented - returning echo response"
        }
    
    response = {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    }
    
    return JSONResponse(response)


def build_app() -> Starlette:
    """Build the Starlette application"""
    routes = [
        Route("/.well-known/agent-card.json", agent_card_handler, methods=["GET"]),
        Route("/rpc", rpc_handler, methods=["POST"]),
        Route("/", rpc_handler, methods=["POST"]),  # Fallback
    ]
    
    return Starlette(routes=routes)


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="LoopForge — AgentBeats Coding Agent")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=9009, help="Server port")
    args = parser.parse_args()

    app = build_app()
    
    print(f"Starting LoopForge agent on {args.host}:{args.port}")
    print(f"Agent card: http://{args.host}:{args.port}/.well-known/agent-card.json")
    print(f"RPC endpoint: http://{args.host}:{args.port}/rpc")
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()