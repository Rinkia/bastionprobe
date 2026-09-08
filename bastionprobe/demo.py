"""Two toy agents so `bastionprobe run` works with zero setup and the loop has a
runnable check: a vulnerable one (obeys instructions found in tool output) and a
safe one (treats tool output as data). Real targets live in your own module.
"""

from __future__ import annotations

import re
from typing import Mapping

from .target import AgentResponse

_KNOWN_TOOLS = ("send_email", "delete_file", "http_post")


def vulnerable_agent(messages: list[dict], tool_outputs: Mapping[str, str]) -> AgentResponse:
    """Naively concatenates tool output into its "reasoning" and does what it
    says: echoes any token it's told to, and calls any known tool named in the
    text. This is the mistake real agents make."""
    blob = " ".join(tool_outputs.values())
    reply = f"Here is the summary. {blob}"  # leaks the planted text verbatim
    called = tuple(t for t in _KNOWN_TOOLS if t in blob)
    return AgentResponse(text=reply, tool_calls=called)


def safe_agent(messages: list[dict], tool_outputs: Mapping[str, str]) -> AgentResponse:
    """Treats tool output strictly as data to summarize. Never emits tokens from
    it and never lets it trigger a tool call."""
    n = sum(len(v) for v in tool_outputs.values())
    return AgentResponse(text=f"The document is {n} characters long.", tool_calls=())
