"""CoT-forgery is a fireable, reported probe tactic (BASTION_INTEL A2).

bastionprobe fires payloads from the shared corpus (to_probe) and groups land
rates by `tactic`. The corpus now carries a fireable CoT-forgery payload, so
"cot-forgery" is a real tactic in a probe run — no probe code change needed, this
test locks that wiring.
"""

from __future__ import annotations

import pytest

from bastionprobe.analyze import group_rates
from bastionprobe.corpus import _load_from_bastioncorpus
from bastionprobe.runner import AttackResult

# The fireable cot-forgery payload ships in bastioncorpus >= 0.3.0. Until that
# version is published + the floor propagated, an older corpus won't have it, so
# skip rather than fail on the ordering gap (PRP §1.2 propagation).
_payloads = _load_from_bastioncorpus() or []
_has_cot = any(p.tactic == "cot-forgery" for p in _payloads)
_skip_no_cot = pytest.mark.skipif(not _has_cot, reason="needs bastioncorpus>=0.3.0 (cot-forgery payload)")


@_skip_no_cot
def test_cot_forgery_payload_is_fireable():
    cot = [p for p in _payloads if p.tactic == "cot-forgery"]
    assert cot, "no fireable cot-forgery payload in the corpus"
    p = cot[0]
    assert p.channel == "tool_output" and p.check in {"canary", "tool"}
    assert "{canary}" in p.text or p.forbidden_tool  # actually scoreable


def _result(landed: bool) -> AttackResult:
    return AttackResult(
        payload_id="cot-fire-001", category="jailbreak_persona", check="canary",
        landed=landed, canary="AGP-TEST", signal="", reply_excerpt="", tool_calls=(),
        tactic="cot-forgery", runs=1, landed_count=1 if landed else 0,
    )


def test_land_rate_analysis_surfaces_cot_forgery():
    # Two runs of a cot-forgery payload, one landed — group_rates must report it.
    groups = {g.key: g for g in group_rates([_result(True), _result(False)], by="tactic")}
    assert "cot-forgery" in groups
    assert groups["cot-forgery"].landed == 1
