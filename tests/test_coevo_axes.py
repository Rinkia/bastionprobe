"""Axes map every attack to a stable behavioral cell derived from metadata."""

from bastionprobe import load_payloads
from bastionprobe.coevo import Cell, all_cells, cell_of
from bastionprobe.coevo.axes import is_coherent
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


def test_all_cells_are_coherent_and_enumerated():
    cells = all_cells()
    # 7 framings x 5 languages x 3 coherent (surface,action) pairs
    assert len(cells) == 7 * 5 * 3
    assert len({c.key for c in cells}) == len(cells)  # keys unique
    assert all(is_coherent(c) for c in cells)
    # the incoherent combos are excluded
    assert not is_coherent(Cell("data-field", "tool-call", "en", "echo"))
    assert not is_coherent(Cell("data-field", "content-echo", "en", "egress"))


def test_bundled_payloads_map_into_the_coherent_map():
    keys = {c.key for c in all_cells()}
    for p in load_payloads():
        assert cell_of(p).key in keys  # every real payload occupies a real cell


def test_distance():
    a = Cell("data-field", "content-echo", "en", "echo")
    b = Cell("data-field", "content-echo", "de", "echo")
    assert a.distance(b) == 1 and a.distance(a) == 0
