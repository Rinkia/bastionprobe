"""The autonomous co-evolution loop: B -> A -> C -> harden -> benchmark.

Each round: B generates payloads toward the director's target cells, they are
fired at A (as a guarded Target) via the existing run_suite, C classifies the
outcomes and steers the next round, A hardens against what landed, and A is
re-scored on the FROZEN benchmark. Stops early when the director declares
illusory progress (benchmark stalled while B keeps winning).

Both arms are pluggable (defender-agnostic, generator-agnostic), matching the
codebase's callable-interface ethos. `harden_fn` is how A evolves; the default
memorizes what landed (a deliberately simple ceiling — real A hardens via the
`harden` bridge into agentbastion signatures/templates).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from ..corpus import Payload
from ..runner import run_suite
from ..target import Target
from .benchmark import BenchmarkHistory, BlockFn, evaluate, frozen_contamination
from .defender import make_guarded_target
from .director import Director, DirectorReport
from .generator import generate_batch

log = logging.getLogger("bastionprobe.coevo")

# How A evolves: given the current block_fn and the texts that just landed,
# return a new block_fn. Default = memorize (block those texts next round).
HardenFn = Callable[[BlockFn, list[str]], BlockFn]


def memorizing_harden(block_fn: BlockFn, texts: list[str]) -> BlockFn:
    """ponytail: A memorizes landed attack texts (substring match). A real A
    generalizes via SemanticDetector templates from the harden bridge; this is
    the minimal stand-in so the loop runs end to end."""
    mem = [t for t in texts if t]
    if not mem:
        return block_fn
    return lambda t: block_fn(t) or any(m in t or t in m for m in mem)


@dataclass(frozen=True)
class CoevoConfig:
    rounds: int = 5
    per_cell: int = 2
    runs: int = 2


def run_coevolution(
    defender: BlockFn,
    frozen_rows: list[dict],
    seed_payloads: list[Payload],
    *,
    config: Optional[CoevoConfig] = None,
    director: Optional[Director] = None,
    harden_fn: HardenFn = memorizing_harden,
    inner: Optional[Target] = None,
    generator: Callable[[list, int, int], list] = generate_batch,
    on_round: Optional[Callable[[int, DirectorReport], None]] = None,
) -> list[DirectorReport]:
    """Run the loop. Returns one DirectorReport per round. `generator(target_cells,
    per_cell, seed)` builds B's next round (default: template mutation; pass an
    LLM generator for novel families)."""
    cfg = config or CoevoConfig()
    director = director or Director()
    history = BenchmarkHistory()
    guard = defender
    reports: list[DirectorReport] = []
    targets: list[str] = []

    contamination = frozen_contamination(frozen_rows, {p.text for p in seed_payloads})
    if contamination:
        log.warning("frozen benchmark contaminated by %d seed payloads", len(contamination))

    for i in range(cfg.rounds):
        payloads = seed_payloads if i == 0 else generator(targets, cfg.per_cell, i)
        if not payloads:
            log.info("no payloads to explore at round %d; stopping", i + 1)
            break

        target = make_guarded_target(guard, inner) if inner else make_guarded_target(guard)
        results = run_suite(target, payloads, runs=cfg.runs)
        score = evaluate(frozen_rows, guard).recall
        report = director.round(results, benchmark_score=score)
        history.append(score)
        reports.append(report)
        if on_round is not None:
            on_round(i + 1, report)

        # A learns what landed (Hall of Fame + new elites) and hardens.
        landed = [r.payload_text for r in results if r.landed]
        guard = harden_fn(guard, landed)
        targets = report.direction_for_b["target_cells"]

        if (not report.progress_diagnosis["real_progress"]
                and history.stalled(director.config.stall_rounds, director.config.stall_eps)):
            log.info("illusory progress at round %d; stopping", i + 1)
            break

    return reports
