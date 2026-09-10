"""C — the Adversarial Research Director and its co-evolution machinery.

Phase 1 (this slice): the standalone director component — behavioral map (axes),
quality-diversity archive, embedding-hybrid novelty, and the round-decision that
emits the spec's structured report. Deterministic and offline; later phases add
the frozen-benchmark bridge, the A-as-defender target, the B generator, and the
autonomous loop.
"""

from .archive import Archive, Elite
from .axes import Cell, all_cells, cell_of
from .benchmark import (
    BenchmarkHistory,
    BenchmarkScore,
    evaluate,
    frozen_contamination,
    load_corpus,
)
from .defender import make_guarded_target
from .director import Director, DirectorConfig, DirectorReport
from .generator import generate_batch, generate_one
from .novelty import novelty_score
from .orchestrator import CoevoConfig, memorizing_harden, run_coevolution

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
    "BenchmarkScore",
    "BenchmarkHistory",
    "evaluate",
    "load_corpus",
    "frozen_contamination",
    "make_guarded_target",
    "generate_batch",
    "generate_one",
    "run_coevolution",
    "CoevoConfig",
    "memorizing_harden",
]
