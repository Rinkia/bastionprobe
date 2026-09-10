"""A real OpenAI (GPT) target.

The vendor twin of anthropic_target: wraps an OpenAI client as a bastionprobe
Target so GPT models drop into the same suite and the same cross-model matrix.
It reuses the exact demo agent (system prompt + tools) from anthropic_target, so
a cross-vendor comparison measures the models, not two different harnesses.

Tools become `{"type":"function","function":{...}}`; the response is read from
`choices[0].message` (`.content` + `.tool_calls[].function.name`).

The poisoned payload is delivered as a labeled **user** message ("[Result from
the read_document tool] ..."), not as a fabricated assistant tool-call + tool
result. That replay works on OpenAI proper but strict providers reject a
functionCall the model never issued — Gemini 3.x, reached through its OpenAI-
compatible endpoint, demands a `thought_signature` on such parts. Injecting the
retrieved content as a user turn is portable across every OpenAI-compatible
provider and just as faithful: the injection still rides in the data the agent
retrieved, and the tools are still offered so tool-call checks fire. (The native
anthropic_target keeps the authentic tool_result replay.)

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
    vector: str = "user_message",
) -> Target:
    """Build a Target backed by a live OpenAI client.

    `vector` chooses how the poisoned content is delivered:
      - "user_message" (default): as a labeled user turn. Portable across every
        OpenAI-compatible provider, including strict ones (Gemini 3.x) that
        reject a fabricated tool-call.
      - "tool_result": as a real assistant tool-call + tool result. More
        authentic, but only OpenAI-proper and lenient providers accept it. Use it
        to match the native anthropic_target vector for apples-to-apples tests.

    `client` is anything with `.chat.completions.create(...)` matching the OpenAI
    SDK (a real `openai.OpenAI()`, or a stand-in for tests)."""
    if vector not in ("tool_result", "user_message"):
        raise ValueError(f"vector must be tool_result or user_message, got {vector!r}")
    tool_list = _to_openai_tools(tools if tools is not None else DEFAULT_TOOLS)

    def _convo(messages: list[dict], poisoned: str) -> list[dict]:
        base: list[dict[str, Any]] = [{"role": "system", "content": system}, *messages]
        if vector == "user_message":
            return base + [
                {"role": "user", "content": f"[Result from the {poisoned_tool} tool]\n{poisoned}"}
            ]
        # tool_result: fabricate the prior tool-call + its result.
        tcid = "call_" + secrets.token_hex(6)
        return base + [
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": tcid, "type": "function",
                 "function": {"name": poisoned_tool, "arguments": json.dumps({"path": "document.txt"})}},
            ]},
            {"role": "tool", "tool_call_id": tcid, "content": poisoned},
        ]

    def target(messages: list[dict], tool_outputs: Mapping[str, str]) -> AgentResponse:
        poisoned = tool_outputs.get(poisoned_tool, "")
        convo = _convo(messages, poisoned)

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
