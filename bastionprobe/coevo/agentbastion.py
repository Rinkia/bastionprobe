"""Wire agentbastion in as A — a real, hardening blue side.

A defends by scanning the poisoned tool result; A "evolves" by ingesting the
attacks that landed as SemanticDetector templates (the same `harden` bridge
output), so next round it blocks them and their paraphrases via embedding
similarity. This replaces the loop's memorizing stub with real hardening.

The block decision is `base heuristics OR semantic match against accumulated
landed attacks`. Accumulation is the Hall-of-Fame the director replays, so A does
not forget old holes.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .embedders import EmbedFn
from .benchmark import BlockFn

# harden_fn shape from the orchestrator: (current block_fn, landed texts) -> block_fn.
HardenFn = Callable[[BlockFn, list], BlockFn]


def guard_to_block_fn(guard: Any) -> BlockFn:
    """Any agentbastion InboundGuard -> a block_fn(text) -> bool."""
    return lambda t: guard.is_blocked(guard.scan(t))


def _make_default_detector_factory(threshold: float):
    def factory(embed_fn: EmbedFn, templates: list):
        from agentbastion.semantic import SemanticDetector  # optional dep

        return SemanticDetector(embed_fn, templates=templates, threshold=threshold)

    return factory


def make_hardening_defender(
    embed_fn: EmbedFn,
    base_guard: Optional[Any] = None,
    detector_factory: Optional[Callable[[EmbedFn, list], Any]] = None,
    threshold: float = 0.4,
) -> tuple[BlockFn, HardenFn]:
    """Return (block_fn, harden_fn) for a self-hardening agentbastion defender.

    `base_guard` is any object with `.scan(text)` + `.is_blocked(result)` (a real
    agentbastion InboundGuard, or a stand-in for tests). `detector_factory(embed_fn,
    templates) -> detector` builds the semantic layer (default: agentbastion's
    SemanticDetector). Both default to agentbastion, imported only when used — so
    tests can inject fakes and skip the dependency entirely.

    harden_fn accumulates the landed attack texts and rebuilds the detector over
    them; the returned block_fn reads that live detector, so A gets stricter every
    round it is hardened.
    """
    if base_guard is None:
        from agentbastion.inbound import InboundGuard  # optional dep

        base_guard = InboundGuard()
    make_detector = detector_factory or _make_default_detector_factory(threshold)

    state: dict = {"templates": [], "detector": None}

    def block_fn(text: str) -> bool:
        if base_guard.is_blocked(base_guard.scan(text)):
            return True
        det = state["detector"]
        if det is not None:
            matches, _ = det.scan(text)
            if matches:
                return True
        return False

    def harden_fn(_prev: BlockFn, landed_texts: list) -> BlockFn:
        added = False
        for t in landed_texts:
            if t and t not in state["templates"]:
                state["templates"].append(t)
                added = True
        if added:
            state["detector"] = make_detector(embed_fn, list(state["templates"]))
        return block_fn

    return block_fn, harden_fn
