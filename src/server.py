import argparse
import logging
import os
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

# Import your agent executor
from src.loopforge import LoopForgeExecutor  # Adjust this import path

def main():
    parser = argparse.ArgumentParser(description="Run the LoopForge A2A agent.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=9009, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="URL to advertise in the agent card")
    parser.add_argument(
        "--google-api-key",
        type=str,
        default=os.environ.get("GOOGLE_API_KEY"),
        help="Google API key for Gemini",
    )
    
    args = parser.parse_args()

    skill = AgentSkill(
        id="loopforge-solver",
        name="LoopForge Solver",
        description="Receives a coding problem and solves it using Gemini 2.0 Flash.",
        tags=["coding", "gemini", "agent"],
        examples=["Fix this bug in the code", "Implement this feature"],
    )

    agent_card = AgentCard(
        name="LoopForge",
        description="A2A coding agent powered by Gemini 2.0 Flash.",
        url=args.card_url or f"http://{args.host}:{args.port}/",
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=LoopForgeExecutor(
            google_api_key=args.google_api_key,
        ),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    logging.info(f"Starting LoopForge agent on {args.host}:{args.port}")
    uvicorn.run(server.build(), host=args.host, port=args.port)

if __name__ == "__main__":
    main()