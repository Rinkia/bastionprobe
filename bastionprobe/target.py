"""The agent-under-test contract.

A Target is any callable that runs the victim agent for one turn and reports
back what it did. bastionprobe plants a payload in one tool output, hands the
whole thing to the Target, and reads the AgentResponse to decide whether the
injection landed.

You implement ONE function for your stack. The runner never sees inside the
agent; it only sees this response. Keep it honest: report the tools the agent
actually called and the text it actually produced.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Mapping


@dataclass(frozen=True)
class AgentResponse:
    """What the agent did with the (poisoned) tool outputs this turn."""

    text: str  # the agent's final reply to the user
    tool_calls: tuple[str, ...] = ()  # names of tools the agent invoked


# messages: the conversation so far (OpenAI/Anthropic-style role dicts).
# tool_outputs: {tool_name: output_string}. bastionprobe poisons one value.
Target = Callable[[list[dict], Mapping[str, str]], "AgentResponse"]


def rate_limited(target: Target, per_minute: float) -> Target:
    """Wrap a target so its calls are spaced to at most `per_minute` requests.

    Free tiers throttle hard (Gemini free = 5 req/min); a full suite fires many
    calls back to back and trips a 429. This spaces them just enough. Composable
    and provider-agnostic - wrap any target:

        target = rate_limited(make_openai_target(client, model=...), per_minute=5)

    A suite of N payloads x runs at 5/min takes ~(N*runs/5) minutes, so prefer a
    provider with a higher limit (or fewer runs) for large sweeps.
    """
    min_interval = 60.0 / per_minute if per_minute > 0 else 0.0
    last = [0.0]

    def wrapped(messages: list[dict], tool_outputs: Mapping[str, str]) -> AgentResponse:
        wait = min_interval - (time.monotonic() - last[0])
        if wait > 0:
            time.sleep(wait)
        last[0] = time.monotonic()
        return target(messages, tool_outputs)

    return wrapped
