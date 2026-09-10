"""Novelty: high in empty regions, low near existing elites; embed_fn optional."""

from bastionprobe.coevo import Archive, novelty_score
from bastionprobe.runner import AttackResult


def mk(pid, tactic="data-field", category="indirect_injection", text="alpha beta"):
    return AttackResult(
        payload_id=pid, category=category, check="canary", landed=True, canary="",
        signal="", reply_excerpt="", tool_calls=(), payload_text=text,
        forbidden_tool=None, tactic=tactic, runs=5, landed_count=5,
    )


def test_empty_archive_is_maximally_novel():
    assert novelty_score(mk("p1"), Archive()) == 1.0


def test_same_cell_is_low_novelty():
    a = Archive()
    r = mk("p1")
    a.update(r, 0.5, 1.0, 1)
    # a second attack in the SAME cell has cell-distance 0
    assert novelty_score(mk("p2"), a) == 0.0


def test_distant_cell_more_novel_than_near():
    a = Archive()
    a.update(mk("p1", category="indirect_injection"), 0.5, 1.0, 1)  # en
    near = novelty_score(mk("p2", category="de_indirect_injection"), a)  # 1 axis away
    far = novelty_score(mk("p3", tactic="egress-overt", category="it_indirect_injection"), a)  # 2 axes
    assert far > near > 0.0


def test_embed_fn_blends_and_fails_soft():
    a = Archive()
    a.update(mk("p1", text="alpha beta"), 0.5, 1.0, 1)
    probe = mk("p2", category="de_indirect_injection", text="alpha beta")

    def embed(texts):  # fixed shared vocab so vectors are comparable
        vocab = sorted({w for t in texts for w in t.split()})
        return [[t.split().count(w) for w in vocab] for t in texts]

    blended = novelty_score(probe, a, embed_fn=embed)
    cell_only = novelty_score(probe, a)  # 0.25 (1 axis of 4)
    assert 0.0 <= blended <= 1.0

    def boom(texts):
        raise RuntimeError("embedder down")

    # embedder failure falls back to the deterministic cell component
    assert novelty_score(probe, a, embed_fn=boom) == cell_only
