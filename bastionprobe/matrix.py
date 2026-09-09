"""Cross-model matrix: fire the same suite at several targets, compare by tactic.

A target is just a callable, so the matrix is model-agnostic — Anthropic models
via `make_anthropic_target(client, model=...)`, and any other vendor once it has
an adapter of the same shape. The payoff is turning a single-model finding
("egress refusal is framing-invariant on sonnet") into a comparison ("...and it
holds on haiku but not on model X").

Resilient by design: a target that errors on every call (bad model id, auth,
outage) is recorded as errored for its column and the rest of the matrix still
runs. One broken model never sinks the whole comparison.
"""

from __future__ import annotations

from typing import Callable, Mapping, Optional

from .analyze import GroupRate, group_rates
from .runner import AttackResult, run_suite
from .corpus import Payload
from .target import Target

# Per-model results: the list of AttackResults, or None if that target errored.
MatrixResults = dict[str, Optional[list[AttackResult]]]


def run_matrix(
    targets: Mapping[str, Target],
    payloads: list[Payload],
    runs: int = 1,
    on_result: Optional[Callable[[str, int, int, AttackResult], None]] = None,
) -> MatrixResults:
    """Run the suite against each named target. `on_result(model, i, total, r)`
    fires per payload for progress. A target raising (e.g. bad model id) is
    recorded as None and the matrix continues."""
    out: MatrixResults = {}
    for name, target in targets.items():
        cb = (lambda i, t, r, _n=name: on_result(_n, i, t, r)) if on_result else None
        try:
            out[name] = run_suite(target, payloads, runs=runs, on_result=cb)
        except Exception as e:  # noqa: BLE001 - isolate a bad model, keep the rest
            out[name] = None
            if on_result is None:
                # surface it somewhere even without a progress sink
                import logging

                logging.getLogger("bastionprobe.matrix").warning(
                    "target %s errored: %s: %s", name, type(e).__name__, e
                )
    return out


def _rates_by_tactic(results: list[AttackResult]) -> dict[str, GroupRate]:
    return {g.key: g for g in group_rates(results, by="tactic")}


def tactic_matrix(
    matrix: MatrixResults,
) -> tuple[list[str], list[str], dict[str, dict[str, Optional[GroupRate]]]]:
    """Reshape into a grid: (tactics, models, cell[tactic][model] -> GroupRate|None).
    Tactics are sorted; a None cell means that model errored."""
    models = list(matrix.keys())
    per_model = {m: (_rates_by_tactic(r) if r is not None else None) for m, r in matrix.items()}
    tactics = sorted({t for rm in per_model.values() if rm for t in rm})
    grid: dict[str, dict[str, Optional[GroupRate]]] = {}
    for tac in tactics:
        grid[tac] = {m: (per_model[m].get(tac) if per_model[m] else None) for m in models}
    return tactics, models, grid


def overall_rate(results: Optional[list[AttackResult]]) -> Optional[float]:
    if results is None:
        return None
    runs = sum(r.runs for r in results)
    return (sum(r.landed_count for r in results) / runs) if runs else 0.0
