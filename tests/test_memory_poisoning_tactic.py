"""Memory-poisoning is a fireable, reported probe tactic (BASTION_INTEL, bastionmemory).

The corpus carries fireable memory-poisoning payloads (a document that tries to get
the agent to persist an attacker standing-order). bastionprobe fires them via
to_probe and groups land-rate by `tactic` — no probe code change, this locks the
wiring. Ships in bastioncorpus >= 0.4.0; skip on older corpus (propagation ordering).
"""

from __future__ import annotations

import pytest

from bastionprobe.analyze import group_rates
from bastionprobe.corpus import _load_from_bastioncorpus
from bastionprobe.runner import AttackResult

_payloads = _load_from_bastioncorpus() or []
_has_mp = any(p.tactic == "memory-poisoning" for p in _payloads)
_skip = pytest.mark.skipif(not _has_mp, reason="needs bastioncorpus>=0.4.0 (memory-poisoning payloads)")


@_skip
def test_memory_poisoning_payloads_are_fireable():
    mp = [p for p in _payloads if p.tactic == "memory-poisoning"]
    assert mp, "no fireable memory-poisoning payload in the corpus"
    for p in mp:
        assert p.channel == "tool_output"
        assert p.check in {"canary", "tool"}
        assert "{canary}" in p.text or p.forbidden_tool  # actually scoreable


def test_land_rate_analysis_surfaces_memory_poisoning():
    results = [
        AttackResult(payload_id="mp-fire-001", category="indirect_injection", check="canary",
                     landed=True, canary="AGP-T", signal="", reply_excerpt="", tool_calls=(),
                     tactic="memory-poisoning", runs=1, landed_count=1),
        AttackResult(payload_id="mp-fire-001", category="indirect_injection", check="canary",
                     landed=False, canary="AGP-T", signal="", reply_excerpt="", tool_calls=(),
                     tactic="memory-poisoning", runs=1, landed_count=0),
    ]
    groups = {g.key: g for g in group_rates(results, by="tactic")}
    assert "memory-poisoning" in groups
    assert groups["memory-poisoning"].landed == 1
