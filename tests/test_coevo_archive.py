"""Quality-diversity archive: one best elite per cell, coverage never sacrificed."""

from bastionprobe.coevo import Archive
from bastionprobe.runner import AttackResult


def mk(pid, tactic="data-field", category="indirect_injection", check="canary", forbidden_tool=None):
    return AttackResult(
        payload_id=pid, category=category, check=check, landed=True, canary="",
        signal="", reply_excerpt="", tool_calls=(), payload_text=f"text-{pid}",
        forbidden_tool=forbidden_tool, tactic=tactic, runs=5, landed_count=5,
    )


def test_add_then_replace_only_if_better():
    a = Archive()
    assert a.update(mk("p1"), quality=0.4, novelty=0.5, round=1) == "added"
    # same cell, higher quality -> replace
    assert a.update(mk("p2"), quality=0.8, novelty=0.1, round=2) == "replaced"
    # same cell, lower quality -> reject
    assert a.update(mk("p3"), quality=0.2, novelty=0.9, round=3) == "rejected"
    filled, _ = a.coverage()
    assert filled == 1 and a.elites()[0].attack_id == "p2"


def test_different_cells_coexist():
    a = Archive()
    a.update(mk("p1", category="indirect_injection"), 0.5, 0.5, 1)  # en
    a.update(mk("p2", category="de_indirect_injection"), 0.5, 0.5, 1)  # de
    assert a.coverage()[0] == 2  # coverage grows, not a global leaderboard


def test_empty_cells_excludes_filled():
    a = Archive()
    a.update(mk("p1"), 0.5, 0.5, 1)
    keys = {c.key for c in a.empty_cells()}
    assert a.elites()[0].cell_key not in keys


def test_jsonl_roundtrip(tmp_path):
    a = Archive()
    a.update(mk("p1"), 0.5, 0.5, 1)
    a.update(mk("p2", category="fr_indirect_injection"), 0.7, 0.3, 2)
    p = tmp_path / "arc.jsonl"
    a.to_jsonl(p)
    b = Archive.from_jsonl(p)
    assert b.filled_keys() == a.filled_keys()
    assert Archive.from_jsonl(tmp_path / "missing.jsonl").coverage()[0] == 0  # fail-soft
