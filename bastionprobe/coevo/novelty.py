"""Novelty: how behaviorally distant an attack is from the archive.

Embedding-hybrid (per the plan): a deterministic cell-distance component always,
plus an optional embedding-distance component when an embed_fn is supplied. With
no embedder it degrades to pure cell-distance — fully deterministic and offline.

Novelty weighs equal to success in the director's selection, so B is pushed
toward dissimilar attacks, not just successful ones (anti-degeneration rule 1).
"""

from __future__ import annotations

from math import sqrt
from typing import Any, Callable, Optional, Sequence

from .archive import Archive
from .axes import cell_of

# Same shape as agentbastion's semantic.EmbedFn.
EmbedFn = Callable[[Sequence[str]], Sequence[Sequence[float]]]

_NUM_AXES = 4


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _cell_novelty(result: Any, archive: Archive) -> float:
    """Normalized distance (0-1) to the nearest filled cell. 1.0 if the archive is
    empty or this cell is maximally far from every occupied one."""
    filled = archive.elites()
    if not filled:
        return 1.0
    cell = cell_of(result)
    # reconstruct each elite's cell from its key
    nearest = min(
        _key_distance(cell.key, e.cell_key) for e in filled
    )
    return nearest / _NUM_AXES


def _key_distance(k1: str, k2: str) -> int:
    return sum(a != b for a, b in zip(k1.split("|"), k2.split("|")))


def _embed_novelty(result: Any, archive: Archive, embed_fn: EmbedFn) -> Optional[float]:
    """1 - max cosine to any archived elite's text. None on any embedder failure
    (fail-soft: the cell component still carries novelty)."""
    elites = archive.elites()
    if not elites:
        return 1.0
    try:
        texts = [getattr(result, "payload_text", "")] + [e.payload_text for e in elites]
        vecs = list(embed_fn(texts))
        target, rest = vecs[0], vecs[1:]
        best = max((_cosine(target, v) for v in rest), default=0.0)
        return max(0.0, 1.0 - best)
    except Exception:  # noqa: BLE001 - fail soft; cell component still applies
        return None


def novelty_score(result: Any, archive: Archive, embed_fn: Optional[EmbedFn] = None) -> float:
    """Novelty in [0,1]. Cell-distance always; blended 50/50 with embedding distance
    when an embedder is given and succeeds."""
    cell = _cell_novelty(result, archive)
    if embed_fn is None:
        return cell
    emb = _embed_novelty(result, archive, embed_fn)
    if emb is None:
        return cell
    return 0.5 * cell + 0.5 * emb
