"""Template: wire your own agent to bastionprobe.

Copy this, make `agent()` actually run your agent for one turn against the given
tool_outputs, and fire:

    bastionprobe run --target examples.my_agent:agent

Rules:
  - tool_outputs is {tool_name: output}. Feed each value to your agent as the
    result of that tool, exactly as your agent would receive it in production.
  - Return the agent's real reply text and the real names of any tools it called
    this turn. Don't sanitize - bastionprobe is measuring what your agent does.
"""

from __future__ import annotations

from typing import Mapping

from bastionprobe import AgentResponse


def agent(messages: list[dict], tool_outputs: Mapping[str, str]) -> AgentResponse:
    # 1. inject tool_outputs into your agent's context as tool results
    # 2. run one turn
    # 3. collect reply text + tool calls it made
    reply_text = "..."          # <- your agent's actual reply
    tools_it_called = ()        # <- e.g. ("send_email",)
    return AgentResponse(text=reply_text, tool_calls=tools_it_called)
