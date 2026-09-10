"""MAP-Elites quality-diversity archive: one best representative per cell.

Quality-diversity, not a global leaderboard: each cell keeps its own best elite
independently. A weak elite in cell X is NEVER evicted because cell Y has a better
one — that would trade away coverage, which is the whole objective (anti-
degeneration rule 2). The archive is the system's behavioral memory.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from .axes import Cell, all_cells, cell_of


@dataclass(frozen=True)
class Elite:
    cell_key: str
    attack_id: str
    payload_text: str
    quality: float  # effectiveness against A (land rate)
    novelty: float  # distance from the rest of the archive when added
    round: int


class Archive:
    def __init__(self) -> None:
        self._cells: dict[str, Elite] = {}

    def update(self, result: Any, quality: float, novelty: float, round: int) -> str:
        """Insert if the cell is empty, replace if strictly better (ties broken by
        novelty), else reject. Returns "added" | "replaced" | "rejected"."""
        key = cell_of(result).key
        elite = Elite(
            cell_key=key,
            attack_id=getattr(result, "payload_id", ""),
            payload_text=getattr(result, "payload_text", ""),
            quality=quality,
            novelty=novelty,
            round=round,
        )
        cur = self._cells.get(key)
        if cur is None:
            self._cells[key] = elite
            return "added"
        if quality > cur.quality or (quality == cur.quality and novelty > cur.novelty):
            self._cells[key] = elite
            return "replaced"
        return "rejected"

    def get(self, cell_key: str) -> Optional[Elite]:
        return self._cells.get(cell_key)

    def filled_keys(self) -> set[str]:
        return set(self._cells)

    def elites(self) -> list[Elite]:
        return list(self._cells.values())

    def empty_cells(self) -> list[Cell]:
        filled = self.filled_keys()
        return [c for c in all_cells() if c.key not in filled]

    def coverage(self) -> tuple[int, int]:
        """(filled, total) cells."""
        return len(self._cells), len(all_cells())

    # --- persistence (fail-soft) --------------------------------------------
    def to_jsonl(self, path: Path) -> None:
        with Path(path).open("w", encoding="utf-8") as f:
            for e in self._cells.values():
                f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")

    @classmethod
    def from_jsonl(cls, path: Path) -> "Archive":
        arc = cls()
        try:
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                arc._cells[d["cell_key"]] = Elite(**d)
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            return cls()  # corrupt/absent -> start fresh
        return arc
