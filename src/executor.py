"""
A2A Executor: bridges the a2a-sdk v2 request handling to our Agent class.
"""

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import TaskState

from agent import Agent


class Executor(AgentExecutor):
    """Wraps Agent so it conforms to the AgentExecutor interface."""

    def __init__(self) -> None:
        self._agent = Agent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        await updater.submit()
        try:
            await self._agent.run(context, updater)
        except Exception as exc:
            msg = updater.new_agent_message(parts=_text_parts(f"Agent error: {exc}"))
            await updater.failed(message=msg)
            raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.cancel()


def _text_parts(text: str):
    """Helper to build a list[Part] with a single text part."""
    from a2a.types import Part
    p = Part()
    p.text = text
    return [p]