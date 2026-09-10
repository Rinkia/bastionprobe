"""Behavioral map axes: index an attack by its STRATEGY FAMILY, not its outcome.

A cell is a combination of axis values. The director's job is to fill empty cells,
so the axes must be enumerable (empty cells exist before anything lands in them).

Per the plan, axes are DERIVED from existing AttackResult / Payload metadata — no
new payload schema:
  - framing   <- tactic            (data-field, operational-note, egress-*, ...)
  - surface   <- check             (canary -> content-echo, tool -> tool-call)
  - language  <- category prefix   (en / de / fr / es / it)
  - action    <- forbidden_tool    (egress / destructive / echo)
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

# Known axis values, from the current payload taxonomy. Unknown values fall into
# "other" rather than raising, so the map never breaks on a new payload.
FRAMINGS = ("data-field", "operational-note", "egress-legit", "egress-overt",
            "destructive", "sysprompt-leak", "other")
SURFACES = ("content-echo", "tool-call")
LANGUAGES = ("en", "de", "fr", "es", "it")
ACTIONS = ("echo", "egress", "destructive")

_EGRESS_TOOLS = {"send_email", "http_post"}
_DESTRUCTIVE_TOOLS = {"delete_file"}
_LANG_PREFIXES = ("de", "fr", "es", "it")


@dataclass(frozen=True)
class Cell:
    framing: str
    surface: str
    language: str
    action: str

    @property
    def key(self) -> str:
        return f"{self.framing}|{self.surface}|{self.language}|{self.action}"

    def distance(self, other: "Cell") -> int:
        """Number of axes that differ (0-4). The behavioral-map metric."""
        return sum(
            a != b
            for a, b in (
                (self.framing, other.framing),
                (self.surface, other.surface),
                (self.language, other.language),
                (self.action, other.action),
            )
        )


def _language(category: str) -> str:
    for p in _LANG_PREFIXES:
        if category.startswith(p + "_"):
            return p
    return "en"


def _action(forbidden_tool: Any) -> str:
    if forbidden_tool in _EGRESS_TOOLS:
        return "egress"
    if forbidden_tool in _DESTRUCTIVE_TOOLS:
        return "destructive"
    return "echo"


def _one_of(value: str, known: tuple[str, ...]) -> str:
    return value if value in known else "other"


def cell_of(result: Any) -> Cell:
    """Map anything carrying tactic/category/check/forbidden_tool (an AttackResult
    or a Payload) to its behavioral cell."""
    framing = _one_of(getattr(result, "tactic", "") or "other", FRAMINGS)
    surface = "tool-call" if getattr(result, "check", "canary") == "tool" else "content-echo"
    language = _language(getattr(result, "category", "") or "")
    action = _action(getattr(result, "forbidden_tool", None))
    return Cell(framing=framing, surface=surface, language=language, action=action)


def all_cells() -> list[Cell]:
    """Every cell in the behavioral map (cartesian product of axis values).
    Some combinations are unreachable by construction (e.g. content-echo + egress);
    the director targets empty cells nearest the frontier, so it won't chase them."""
    return [
        Cell(f, s, l, a)
        for f, s, l, a in itertools.product(FRAMINGS, SURFACES, LANGUAGES, ACTIONS)
    ]
