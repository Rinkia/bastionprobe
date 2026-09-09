"""Aggregate land rates by tactic (or any payload dimension).

As the payload set grows, the useful question stops being "did payload X land"
and becomes "which framing tactic lands". This groups results and reports the
pooled land rate per group, so you can see - across many payloads and runs -
that, say, `data-field` beats `operational-note`, or `egress-*` stays near zero.
Pure aggregation over AttackResult; no model calls.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .runner import AttackResult


@dataclass(frozen=True)
class GroupRate:
    key: str
    payloads: int  # distinct payloads in this group
    runs: int  # total runs fired across them
    landed: int  # total runs that landed
    any_landed: int  # payloads that landed at least once

    @property
    def rate(self) -> float:
        return self.landed / self.runs if self.runs else 0.0


def group_rates(results: list[AttackResult], by: str = "tactic") -> list[GroupRate]:
    """Pool results by an AttackResult attribute (default `tactic`). Groups are
    returned most-vulnerable first. Empty group keys fall back to '(none)'."""
    buckets: dict[str, list[AttackResult]] = defaultdict(list)
    for r in results:
        buckets[getattr(r, by, "") or "(none)"].append(r)

    out = [
        GroupRate(
            key=key,
            payloads=len(rs),
            runs=sum(r.runs for r in rs),
            landed=sum(r.landed_count for r in rs),
            any_landed=sum(1 for r in rs if r.landed),
        )
        for key, rs in buckets.items()
    ]
    return sorted(out, key=lambda g: g.rate, reverse=True)


def format_groups(groups: list[GroupRate], by: str = "tactic") -> str:
    if not groups:
        return ""
    lines = [f"land rate by {by}:", "-" * 68]
    for g in groups:
        pct = f"{g.rate * 100:3.0f}%"
        lines.append(
            f"  {pct}  {g.landed:>3}/{g.runs:<3} runs  "
            f"{g.any_landed}/{g.payloads} payloads   {g.key}"
        )
    return "\n".join(lines)
