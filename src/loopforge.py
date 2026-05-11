"""
LoopForge Agent Executor - Handles coding tasks via Gemini 2.0 Flash
"""

import logging
import os
from typing import Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


class LoopForgeExecutor:
    """
    LoopForge executor that uses Gemini 2.0 Flash to solve coding problems.
    Compatible with A2A SDK 0.3.10 DefaultRequestHandler.
    """

    def __init__(self, google_api_key: Optional[str] = None):
        """
        Initialize the LoopForge executor.
        
        Args:
            google_api_key: Google API key for Gemini. If not provided, 
                          uses GOOGLE_API_KEY environment variable.
        """
        self.google_api_key = google_api_key or os.environ.get("GOOGLE_API_KEY")
        
        if not self.google_api_key:
            logger.warning("No GOOGLE_API_KEY provided. Agent will not function properly.")
        else:
            genai.configure(api_key=self.google_api_key)
        
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("LoopForgeExecutor initialized with Gemini 2.0 Flash")

    async def execute(self, context, event_queue):
        """
        Execute a coding task using Gemini 2.0 Flash.
        
        Args:
            context: Request context from DefaultRequestHandler
            event_queue: Event queue for publishing responses
        """
        try:
            # Extract the user's message
            user_input = context.get_user_input()
            
            logger.info(f"Processing task: {user_input[:100]}...")
            
            # Create the prompt for Gemini
            prompt = f"""You are an expert coding agent. Solve the following coding problem:

{user_input}

Provide a clear, concise solution with explanations."""
            
            # Call Gemini 2.0 Flash
            response = self.model.generate_content(prompt)
            solution = response.text
            
            logger.info(f"Generated solution ({len(solution)} chars)")
            
            # Publish response message
            from a2a.utils import new_agent_text_message
            message = new_agent_text_message(solution, context.message.messageId)
            event_queue.enqueue_event(message)
            
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}", exc_info=True)
            error_msg = f"Error: {str(e)}"
            
            from a2a.utils import new_agent_text_message
            message = new_agent_text_message(error_msg, context.message.messageId)
            event_queue.enqueue_event(message)