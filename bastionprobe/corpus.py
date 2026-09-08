"""Load attack payloads for bastionprobe.

Shared corpus contract with agentbastion: rows are JSONL objects that carry a
`category` drawn from the same taxonomy as agentbastion's benchmark/corpus.jsonl
(direct_injection, exfiltration, indirect_injection, jailbreak_persona, ...).
Defense reads those rows as "block this string"; offense reads them as "fire
this string". Same taxonomy, opposite direction.

bastionprobe's own payloads (payloads.jsonl) extend that schema with the fields an
active attack needs: a stable `id`, the delivery `channel` (where the payload is
planted), a `check` telling the runner how to score success, and an optional
`{canary}` slot the runner fills with a unique token per run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_PAYLOADS_FILE = Path(__file__).with_name("payloads.jsonl")


@dataclass(frozen=True)
class Payload:
    """One attack. Immutable. `text` may contain a `{canary}` placeholder."""

    id: str
    text: str
    category: str
    channel: str = "tool_output"
    check: str = "canary"  # "canary" | "tool"
    forbidden_tool: Optional[str] = None
    severity: int = 3

    def render(self, canary: str) -> str:
        """Fill the canary slot. No-op if the payload has no placeholder."""
        return self.text.replace("{canary}", canary)


def load_payloads(path: Path = _PAYLOADS_FILE) -> list[Payload]:
    rows: list[Payload] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("check") == "tool" and not d.get("forbidden_tool"):
            raise ValueError(f"payload {d.get('id')!r}: check=tool needs forbidden_tool")
        rows.append(
            Payload(
                id=d["id"],
                text=d["text"],
                category=d.get("category", "indirect_injection"),
                channel=d.get("channel", "tool_output"),
                check=d.get("check", "canary"),
                forbidden_tool=d.get("forbidden_tool"),
                severity=int(d.get("severity", 3)),
            )
        )
    return rows
