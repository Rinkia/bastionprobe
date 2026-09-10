"""Director round: classify, steer to empty cells, detect collapse, diagnose progress."""

from bastionprobe.coevo import Director, DirectorConfig
from bastionprobe.runner import AttackResult


def mk(pid, tactic="data-field", category="indirect_injection", check="canary",
       forbidden_tool=None, landed_count=5):
    return AttackResult(
        payload_id=pid, category=category, check=check, landed=landed_count > 0, canary="",
        signal="", reply_excerpt="", tool_calls=(), payload_text=f"text-{pid}",
        forbidden_tool=forbidden_tool, tactic=tactic, runs=5, landed_count=landed_count,
    )


def test_report_schema_and_empty_targets():
    d = Director()
    results = [
        mk("a", category="indirect_injection"),
        mk("b", category="de_indirect_injection"),
        mk("c", tactic="egress-overt", check="tool", forbidden_tool="send_email"),
    ]
    rep = d.round(results, benchmark_score=None)
    body = rep.to_dict()
    assert set(body) == {
        "classification", "archive_update", "direction_for_b",
        "mode_collapse", "replay_for_a", "progress_diagnosis",
    }
    assert len(body["classification"]) == 3
    # every steered target cell is genuinely empty (not already filled)
    filled = d.archive.filled_keys()
    assert all(k not in filled for k in body["direction_for_b"]["target_cells"])
    assert body["archive_update"]["cells_added"]  # new cells added


def test_mono_cell_batch_trips_mode_collapse():
    d = Director()
    # four attacks, all the SAME cell -> distinct/total = 0.25 < 0.5
    results = [mk(f"p{i}") for i in range(4)]
    rep = d.round(results)
    assert rep.mode_collapse["detected"] is True
    assert rep.mode_collapse["action"] != "none"


def test_diverse_batch_no_collapse():
    d = Director()
    results = [
        mk("a", category="indirect_injection"),
        mk("b", category="de_indirect_injection", tactic="operational-note"),
        mk("c", tactic="destructive", check="tool", forbidden_tool="delete_file"),
        mk("d", tactic="egress-overt", category="fr_indirect_injection", check="tool", forbidden_tool="http_post"),
    ]
    assert d.round(results).mode_collapse["detected"] is False


def test_flat_benchmark_declares_illusory_progress():
    d = Director(DirectorConfig(stall_rounds=3, stall_eps=0.01))
    results = [mk("a"), mk("b", category="de_indirect_injection")]  # keep winning
    rep = None
    for _ in range(4):  # stall_rounds + 1 rounds at the same benchmark
        rep = d.round(results, benchmark_score=0.700)
    assert rep.progress_diagnosis["real_progress"] is False
    assert "Illusory" in rep.progress_diagnosis["note"]


def test_rising_benchmark_is_real_progress():
    d = Director()
    r1 = d.round([mk("a")], benchmark_score=0.60)
    r2 = d.round([mk("b", category="de_indirect_injection")], benchmark_score=0.72)
    assert r2.progress_diagnosis["benchmark_delta"] == 0.12
    assert r2.progress_diagnosis["real_progress"] is True
