"""
LoopForge — Gemini-powered Purple Agent for AgentBeats Sprint 3.
Uses the new google-genai SDK with iterative tool-use loop.
"""

import os
import subprocess
import tempfile
import textwrap

import google.genai as genai
import google.genai.types as genai_types

from a2a.server.agent_execution.context import RequestContext
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import Part, TaskState

# ── Setup ─────────────────────────────────────────────────────────────────────

MAX_ITERATIONS = 6
MAX_OUTPUT_CHARS = 8_000
MODEL = "gemini-2.0-flash"


def _text_part(text: str) -> Part:
    p = Part()
    p.text = text
    return p


# ── Tools ─────────────────────────────────────────────────────────────────────

def run_python(code: str) -> str:
    """Execute Python code and return stdout/stderr."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        fname = f.name
    try:
        r = subprocess.run(["python3", fname], capture_output=True, text=True, timeout=30)
        return ((r.stdout + r.stderr).strip() or "(no output)")[:MAX_OUTPUT_CHARS]
    except subprocess.TimeoutExpired:
        return "ERROR: timed out after 30s"
    except Exception as e:
        return f"ERROR: {e}"


def run_shell(command: str) -> str:
    """Execute a shell command and return output."""
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return ((r.stdout + r.stderr).strip() or "(no output)")[:MAX_OUTPUT_CHARS]
    except subprocess.TimeoutExpired:
        return "ERROR: timed out after 30s"
    except Exception as e:
        return f"ERROR: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        with open(path, "w") as f:
            f.write(content)
        return f"Written: {path}"
    except Exception as e:
        return f"ERROR: {e}"


def read_file(path: str) -> str:
    """Read and return file content."""
    try:
        with open(path) as f:
            return f.read()[:MAX_OUTPUT_CHARS]
    except Exception as e:
        return f"ERROR: {e}"


TOOL_FN_MAP = {
    "run_python": run_python,
    "run_shell": run_shell,
    "write_file": write_file,
    "read_file": read_file,
}

# Declare tools for Gemini using the new SDK
TOOLS = [
    genai_types.Tool(
        function_declarations=[
            genai_types.FunctionDeclaration(
                name="run_python",
                description="Execute Python code and return stdout/stderr.",
                parameters=genai_types.Schema(
                    type="OBJECT",
                    properties={"code": genai_types.Schema(type="STRING", description="Python code to run")},
                    required=["code"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="run_shell",
                description="Execute a shell/terminal command and return output.",
                parameters=genai_types.Schema(
                    type="OBJECT",
                    properties={"command": genai_types.Schema(type="STRING", description="Shell command")},
                    required=["command"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="write_file",
                description="Write text content to a file on disk.",
                parameters=genai_types.Schema(
                    type="OBJECT",
                    properties={
                        "path": genai_types.Schema(type="STRING", description="File path"),
                        "content": genai_types.Schema(type="STRING", description="Content to write"),
                    },
                    required=["path", "content"],
                ),
            ),
            genai_types.FunctionDeclaration(
                name="read_file",
                description="Read the content of a file from disk.",
                parameters=genai_types.Schema(
                    type="OBJECT",
                    properties={"path": genai_types.Schema(type="STRING", description="File path")},
                    required=["path"],
                ),
            ),
        ]
    )
]

SYSTEM_PROMPT = textwrap.dedent("""\
    You are LoopForge, an expert software engineering agent competing in AgentBeats Sprint 3.
    You solve coding tasks (bug fixes, shell tasks, networking) iteratively.

    Strategy:
    1. Read the task carefully and plan your approach.
    2. Use tools (run_python, run_shell, write_file, read_file) to implement and verify.
    3. Iterate: run → observe → fix → re-run until correct.
    4. End with a clear FINAL ANSWER summarising what you did and the solution.

    Rules:
    - Never hardcode answers; reason from first principles.
    - Always verify your solution by running tests or checking output.
    - Aim to solve each task in ≤6 tool calls.
""")


class Agent:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    async def run(self, context: RequestContext, updater: TaskUpdater) -> None:
        # Extract task text
        task_text = ""
        if context.message:
            for part in context.message.parts:
                if part.HasField("text"):
                    task_text += part.text

        await updater.start_work(
            message=updater.new_agent_message([_text_part("🤔 Analysing the task…")])
        )

        config = genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=TOOLS,
            max_output_tokens=4096,
        )

        # Build conversation history
        history: list[genai_types.Content] = [
            genai_types.Content(role="user", parts=[genai_types.Part(text=task_text)])
        ]

        for iteration in range(MAX_ITERATIONS):
            response = self._client.models.generate_content(
                model=MODEL,
                contents=history,
                config=config,
            )

            # Add model response to history
            history.append(response.candidates[0].content)

            # Check for function calls
            fn_calls = [
                part.function_call
                for part in response.candidates[0].content.parts
                if part.function_call
            ]

            if not fn_calls:
                break

            # Execute tools
            tool_response_parts = []
            for fn_call in fn_calls:
                name = fn_call.name
                args = dict(fn_call.args)
                tool_fn = TOOL_FN_MAP.get(name)

                step = f"🔧 [{iteration+1}/{MAX_ITERATIONS}] `{name}`"
                await updater.update_status(
                    TaskState.TASK_STATE_WORKING,
                    message=updater.new_agent_message([_text_part(step)]),
                )

                result = tool_fn(**args) if tool_fn else f"ERROR: unknown tool '{name}'"

                tool_response_parts.append(
                    genai_types.Part(
                        function_response=genai_types.FunctionResponse(
                            name=name,
                            response={"result": result},
                        )
                    )
                )

            # Add tool results to history
            history.append(
                genai_types.Content(role="user", parts=tool_response_parts)
            )

        # Extract final text
        final_text = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                final_text += part.text

        if not final_text:
            final_text = "Task completed."

        await updater.add_artifact(
            parts=[_text_part(final_text)],
            name="solution",
        )
        await updater.complete(
            message=updater.new_agent_message([_text_part("✅ Done.")])
        )