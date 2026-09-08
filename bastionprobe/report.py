"""Report attack results: a .jsonl of every result + a stdout summary table."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from .runner import AttackResult


def write_jsonl(results: list[AttackResult], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def summary(results: list[AttackResult]) -> str:
    total = len(results)
    landed = sum(1 for r in results if r.landed)
    multi = any(r.runs > 1 for r in results)
    header = (
        f"bastionprobe: {total} attacks fired  |  "
        f"{landed} landed (VULNERABLE)  |  {total - landed} blocked"
    )
    if multi:
        header += f"  |  {results[0].runs} runs/payload"
    lines = ["", header, "-" * 68]
    for r in results:
        mark = "FAIL" if r.landed else "pass"
        # With multiple runs, the land rate is the real signal (models are noisy).
        rate = f"  {r.landed_count}/{r.runs}" if r.runs > 1 else ""
        lines.append(f"  [{mark}{rate}] {r.payload_id:20} {r.category:24} {r.signal}")
    lines.append("-" * 68)
    if landed:
        lines.append(
            f"  {landed}/{total} payloads got through. Each is a hole a runtime "
            "guard (e.g. agentbastion) should close."
        )
    else:
        lines.append("  All payloads blocked. Agent ignored planted tool-output instructions.")
    lines.append("")
    return "\n".join(lines)


def render(results: list[AttackResult], out: Optional[Path] = None) -> str:
    if out is not None:
        write_jsonl(results, out)
    return summary(results)
