"""
A2A conformance tests for LoopForge.

Run with:
    uv run pytest --agent-url http://localhost:9009 -v
"""

import pytest
import httpx

# New SDK uses /.well-known/agent-card.json (not agent.json)
AGENT_CARD_PATH = "/.well-known/agent-card.json"


@pytest.fixture
def agent_url(request):
    return request.config.getoption("--agent-url")


@pytest.mark.asyncio
async def test_agent_card_reachable(agent_url):
    """Agent card endpoint must return 200."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{agent_url}{AGENT_CARD_PATH}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_agent_card_fields(agent_url):
    """Agent card must include required fields."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{agent_url}{AGENT_CARD_PATH}")
    card = resp.json()
    assert "name" in card
    assert "description" in card
    assert "skills" in card
    assert len(card["skills"]) > 0


@pytest.mark.asyncio
async def test_agent_card_name(agent_url):
    """Agent card name must be LoopForge."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{agent_url}{AGENT_CARD_PATH}")
    card = resp.json()
    assert card["name"] == "LoopForge"