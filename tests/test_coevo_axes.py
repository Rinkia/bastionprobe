"""Axes map every attack to a stable behavioral cell derived from metadata."""

from bastionprobe.coevo import Cell, all_cells, cell_of
from bastionprobe.runner import AttackResult


def mk(tactic="data-field", category="indirect_injection", check="canary", forbidden_tool=None):
    return AttackResult(
        payload_id="x", category=category, check=check, landed=True, canary="",
        signal="", reply_excerpt="", tool_calls=(), payload_text="t",
        forbidden_tool=forbidden_tool, tactic=tactic, runs=5, landed_count=5,
    )


def test_egress_tool_maps_to_egress_action():
    c = cell_of(mk(tactic="egress-legit", check="tool", forbidden_tool="send_email"))
    assert c.framing == "egress-legit" and c.action == "egress" and c.surface == "tool-call"


def test_destructive_tool():
    assert cell_of(mk(check="tool", forbidden_tool="delete_file")).action == "destructive"


def test_language_from_category_prefix():
    assert cell_of(mk(category="de_indirect_injection")).language == "de"
    assert cell_of(mk(category="indirect_injection")).language == "en"


def test_unknown_tactic_falls_back_to_other():
    assert cell_of(mk(tactic="brand-new-tactic")).framing == "other"


def test_canary_is_content_echo():
    assert cell_of(mk(check="canary")).surface == "content-echo"


def test_all_cells_enumerated_and_distance():
    cells = all_cells()
    assert len(cells) == 7 * 2 * 5 * 3  # framings x surfaces x languages x actions
    assert len({c.key for c in cells}) == len(cells)  # keys unique
    a = Cell("data-field", "content-echo", "en", "echo")
    b = Cell("data-field", "content-echo", "de", "echo")
    assert a.distance(b) == 1 and a.distance(a) == 0
