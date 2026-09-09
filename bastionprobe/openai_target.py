"""A real OpenAI (GPT) target.

The vendor twin of anthropic_target: wraps an OpenAI client as a bastionprobe
Target so GPT models drop into the same suite and the same cross-model matrix.
It reuses the exact demo agent (system prompt + tools) from anthropic_target, so
a cross-vendor comparison measures the models, not two different harnesses.

OpenAI's chat-completions tool-calling shape differs from Anthropic's, so this
adapter translates: tools become `{"type":"function","function":{...}}`, the
poisoned payload comes back as a `role:"tool"` message, and the response is read
from `choices[0].message` (`.content` + `.tool_calls[].function.name`).

Importing this module needs neither the OpenAI SDK nor a key — only calling the
returned target does.
"""

from __future__ import annotations

import json
import secrets
from typing import Any, Mapping

from .anthropic_target import DEFAULT_SYSTEM, DEFAULT_TOOLS
from .runner import POISONED_TOOL
from .target import AgentResponse, Target

# Cheap + widely available default. Override with the model you actually deploy.
DEFAULT_MODEL = "gpt-4o-mini"


def _to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anthropic tool dicts -> OpenAI function-tool dicts. Same names/schemas, so
    both adapters expose an identical toolbox to their model."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


def make_openai_target(
    client: Any,
    model: str = DEFAULT_MODEL,
    system: str = DEFAULT_SYSTEM,
    tools: list[dict[str, Any]] | None = None,
    poisoned_tool: str = POISONED_TOOL,
    max_tokens: int = 512,
) -> Target:
    """Build a Target backed by a live OpenAI client.

    `client` is anything with `.chat.completions.create(...)` matching the OpenAI
    SDK (a real `openai.OpenAI()`, or a stand-in for tests)."""
    tool_list = _to_openai_tools(tools if tools is not None else DEFAULT_TOOLS)

    def target(messages: list[dict], tool_outputs: Mapping[str, str]) -> AgentResponse:
        poisoned = tool_outputs.get(poisoned_tool, "")
        tool_call_id = "call_" + secrets.token_hex(6)

        # Replay the agent's own read: it already called read_document and got the
        # (poisoned) content back. Now let the model take its next turn.
        convo: list[dict[str, Any]] = [{"role": "system", "content": system}]
        convo += list(messages)
        convo += [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": poisoned_tool,
                            "arguments": json.dumps({"path": "document.txt"}),
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": tool_call_id, "content": poisoned},
        ]

        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            tools=tool_list,
            messages=convo,
        )

        msg = resp.choices[0].message
        text = getattr(msg, "content", None) or ""
        tool_calls = tuple(
            tc.function.name for tc in (getattr(msg, "tool_calls", None) or [])
        )
        return AgentResponse(text=text, tool_calls=tool_calls)

    return target
