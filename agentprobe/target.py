"""The agent-under-test contract.

A Target is any callable that runs the victim agent for one turn and reports
back what it did. agentprobe plants a payload in one tool output, hands the
whole thing to the Target, and reads the AgentResponse to decide whether the
injection landed.

You implement ONE function for your stack. The runner never sees inside the
agent; it only sees this response. Keep it honest: report the tools the agent
actually called and the text it actually produced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping


@dataclass(frozen=True)
class AgentResponse:
    """What the agent did with the (poisoned) tool outputs this turn."""

    text: str  # the agent's final reply to the user
    tool_calls: tuple[str, ...] = ()  # names of tools the agent invoked


# messages: the conversation so far (OpenAI/Anthropic-style role dicts).
# tool_outputs: {tool_name: output_string}. agentprobe poisons one value.
Target = Callable[[list[dict], Mapping[str, str]], AgentResponse]
