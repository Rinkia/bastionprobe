"""C — the Adversarial Research Director and its co-evolution machinery.

Phase 1 (this slice): the standalone director component — behavioral map (axes),
quality-diversity archive, embedding-hybrid novelty, and the round-decision that
emits the spec's structured report. Deterministic and offline; later phases add
the frozen-benchmark bridge, the A-as-defender target, the B generator, and the
autonomous loop.
"""

from .archive import Archive, Elite
from .axes import Cell, all_cells, cell_of
from .director import Director, DirectorConfig, DirectorReport
from .novelty import novelty_score

__all__ = [
    "Cell",
    "cell_of",
    "all_cells",
    "Archive",
    "Elite",
    "novelty_score",
    "Director",
    "DirectorConfig",
    "DirectorReport",
]
