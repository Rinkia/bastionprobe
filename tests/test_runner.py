"""The one runnable check the wedge leaves behind: the scorer must catch a
vulnerable agent on every payload and clear a safe agent on every payload. If
either direction breaks, the whole tool is lying about results."""

from bastionprobe import load_payloads, run_suite
from bastionprobe.demo import safe_agent, vulnerable_agent


def test_vulnerable_agent_fails_every_payload():
    payloads = load_payloads()
    results = run_suite(vulnerable_agent, payloads)
    assert results, "no payloads loaded"
    landed = [r for r in results if r.landed]
    assert len(landed) == len(results), (
        "vulnerable agent should let every payload land; missed: "
        + ", ".join(r.payload_id for r in results if not r.landed)
    )


def test_safe_agent_blocks_every_payload():
    payloads = load_payloads()
    results = run_suite(safe_agent, payloads)
    assert all(not r.landed for r in results), (
        "safe agent should block all; leaked: "
        + ", ".join(r.payload_id for r in results if r.landed)
    )


def test_canary_is_unique_per_attack():
    payloads = load_payloads()
    canaries = {run_suite(safe_agent, [p])[0].canary for p in payloads}
    assert len(canaries) == len(payloads), "canaries must be unique per attack"
