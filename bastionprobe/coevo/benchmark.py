"""Frozen benchmark: A's absolute robustness, held constant across the loop.

The co-evolution loop can lie to itself — B keeps "winning" while A never actually
gets more robust. The guard against that is a FROZEN, labeled corpus that A is
scored on every round but is NEVER hardened against. Rising recall on it = real
progress; flat recall while B still lands = illusory progress (director rule 3).

Defender-agnostic: A is just a `block_fn(text) -> bool` (did A block this text).
For A = agentbastion: `lambda t: fw.is_blocked(fw.scan(t))`. The confusion matrix
is computed here, mirroring agentbastion's benchmark/eval.py, so bastionprobe does
not import that (non-package) directory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# A defender's block decision on one text: True = blocked (good, for malicious).
BlockFn = Callable[[str], bool]


@dataclass(frozen=True)
class BenchmarkScore:
    tp: int
    fp: int
    tn: int
    fn: int
    recall: float      # malicious blocked / malicious total  <- A's robustness
    precision: float
    f1: float
    fpr: float         # benign wrongly blocked / benign total

    @property
    def robustness(self) -> float:
        """The single number the director tracks: recall on the frozen malicious set."""
        return self.recall


def load_corpus(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def evaluate(rows: list[dict], block_fn: BlockFn) -> BenchmarkScore:
    """Score a defender against a labeled corpus ({text, label} rows, label in
    {"malicious","benign"}). Recall is the robustness signal; f1/fpr guard against
    a defender that blocks everything."""
    tp = fp = tn = fn = 0
    for row in rows:
        malicious = row.get("label") == "malicious"
        blocked = bool(block_fn(row["text"]))
        if malicious and blocked:
            tp += 1
        elif malicious and not blocked:
            fn += 1
        elif not malicious and blocked:
            fp += 1
        else:
            tn += 1
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return BenchmarkScore(tp=tp, fp=fp, tn=tn, fn=fn, recall=recall,
                          precision=precision, f1=f1, fpr=fpr)


class BenchmarkHistory:
    """Round-over-round robustness, with stall detection."""

    def __init__(self) -> None:
        self._scores: list[float] = []

    def append(self, score: float) -> None:
        self._scores.append(score)

    def latest(self) -> float | None:
        return self._scores[-1] if self._scores else None

    def delta(self) -> float | None:
        if len(self._scores) < 2:
            return None
        return round(self._scores[-1] - self._scores[-2], 4)

    def stalled(self, rounds: int, eps: float) -> bool:
        """True once the last `rounds`+1 scores sit within `eps` of each other."""
        if len(self._scores) <= rounds:
            return False
        window = self._scores[-(rounds + 1):]
        return (max(window) - min(window)) < eps


def frozen_contamination(frozen_rows: list[dict], hardening_texts: set[str]) -> list[str]:
    """Texts that appear in BOTH the frozen corpus and the hardening set — a
    contaminated benchmark. Returns the overlap ([] = clean). The loop must keep
    these disjoint or the robustness metric is meaningless."""
    frozen_texts = {r["text"] for r in frozen_rows}
    return sorted(frozen_texts & set(hardening_texts))
