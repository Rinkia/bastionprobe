"""Producer field-contract: AttackResult still exposes what bastiontrace reads.

bastiontrace's `from_bastionprobe` adapter duck-types an AttackResult by these
attribute names. If bastionprobe renames or drops one, the probe->trace trace
schema silently breaks on the bastiontrace side. This locks the field set here so
the break is loud at the producer (PRP §1.3).
"""

from __future__ import annotations

from dataclasses import fields

from bastionprobe.runner import AttackResult

# The exact attributes bastiontrace.trace_schema.from_bastionprobe reads.
_ADAPTER_FIELDS = {
    "payload_id", "canary", "forbidden_tool", "category", "tactic",
    "payload_text", "landed", "tool_calls", "reply_excerpt",
}


def test_attackresult_exposes_every_field_the_trace_adapter_reads():
    names = {f.name for f in fields(AttackResult)}
    missing = _ADAPTER_FIELDS - names
    assert not missing, (
        f"AttackResult dropped/renamed fields bastiontrace's adapter needs: {missing}"
    )
