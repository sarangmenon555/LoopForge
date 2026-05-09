# LoopForge — AgentBeats Sprint 3

A Gemini 2.0 Flash powered A2A-compatible purple agent for the
[AgentX–AgentBeats](https://rdi.berkeley.edu/agentx-agentbeats.html)
competition, **Phase 2 Sprint 3 — Coding Agent track**.

## Benchmarks targeted

| Benchmark | Track |
|-----------|-------|
| SWE-bench Pro | Coding Agent |
| Terminal Bench 2.0 | Coding Agent |
| NetArena | Coding Agent |

## Architecture

```
Green Agent (benchmark)
        │  A2A assessment_request
        ▼
  server.py  ──▶  executor.py  ──▶  agent.py
                                        │
                              ┌─────────┴──────────┐
                              │   Gemini 2.0 Flash  │
                              │   (function calling)│
                              └─────────┬──────────┘
                          ┌────────────┴────────────┐
                     run_python  run_shell  write_file  read_file
```

The agent uses an iterative **plan → act → observe → reflect** loop:
1. Reads the task from the green agent
2. Asks Gemini to plan and call tools
3. Executes tools locally (Python sandbox, shell, file I/O)
4. Feeds results back to Gemini
5. Repeats up to 6 iterations until a final answer is produced

## Abstract 

This purple agent uses **Gemini 2.0 Flash** with native function calling to
solve coding tasks through an iterative tool-use loop. The agent receives a
task description via the A2A protocol, then autonomously plans, writes, and
executes code using four tools: `run_python`, `run_shell`, `write_file`, and
`read_file`. It iterates up to 6 times, observing execution results and
self-correcting until it arrives at a verified solution. The architecture is
intentionally general — no benchmark-specific prompts or lookup tables — so
the same agent works across SWE-bench Pro, Terminal Bench 2.0, and NetArena.