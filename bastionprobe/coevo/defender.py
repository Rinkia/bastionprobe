"""A as a bastionprobe Target (the blue side).

Wrap a defender's block decision + an inner agent into a Target, so the whole
existing pipeline (`run_suite`) measures the loop: fire B's attacks at this
target and the land rate = attacks that got PAST A *and* landed on the agent —
exactly "effective against A".

Defender-agnostic: A is a `block_fn(text) -> bool` over the poisoned tool output
(same shape as the frozen benchmark). agentbastion plugs in as
`lambda t: fw.is_blocked(fw.scan(t))`.
"""

from __future__ import annotations

from typing import Mapping

from ..demo import vulnerable_agent
from ..runner import POISONED_TOOL
from ..target import AgentResponse, Target
from .benchmark import BlockFn


def make_guarded_target(block_fn: BlockFn, inner: Target = vulnerable_agent,
                        poisoned_tool: str = POISONED_TOOL) -> Target:
    """A guards the tool result (indirect injection): if A blocks the poisoned
    output, the inner agent never sees it (safe); otherwise the inner agent runs
    on the poisoned content and may obey."""

    def target(messages: list[dict], tool_outputs: Mapping[str, str]) -> AgentResponse:
        poisoned = tool_outputs.get(poisoned_tool, "")
        if block_fn(poisoned):
            return AgentResponse(text="[blocked by A]", tool_calls=())
        return inner(messages, tool_outputs)

    return target
