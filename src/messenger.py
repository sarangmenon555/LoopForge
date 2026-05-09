"""
A2A Messenger: helper for calling other A2A agents from within this agent.
"""

import httpx
from a2a.client import Client, ClientConfig
from a2a.types import Message, SendMessageRequest
from a2a.utils import new_user_text_message


class Messenger:
    """Sends messages to remote A2A agents."""

    async def talk_to_agent(self, message: Message, url: str) -> str:
        """Send a message to another A2A agent and return its text response."""
        async with httpx.AsyncClient() as http_client:
            config = ClientConfig(base_url=url, httpx_client=http_client)
            client = Client(config=config)
            request = SendMessageRequest(message=message)
            response = await client.send_message(request)
            parts = getattr(response.result, "parts", []) if response.result else []
            texts = [p.root.text for p in parts if hasattr(p.root, "text")]
            return "\n".join(texts)