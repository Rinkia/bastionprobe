"""Producer shape-lock: bastionprobe harden emits the tool-policy contract (PRP §1.3).

bastionprobe's `harden` emits a policy.yaml (default + deny-list) that agentbastion
and bastiongate load. This locks the key vocabulary so a rename (`default:`/`deny:`)
fails loudly at the producer. The full byte-golden lock lives on the bastionsupply
producer; probe/trace emit the same contract's default-allow/deny-list subset.
"""

from __future__ import annotations

from bastionprobe.harden import _policy_yaml


def test_policy_has_contract_keys():
    out = _policy_yaml(["send_email", "delete_file"])
    assert "default: allow" in out
    assert "deny:" in out
    assert "- send_email" in out and "- delete_file" in out


def test_empty_denylist_still_valid_shape():
    out = _policy_yaml([])
    assert "default: allow" in out and "deny:" in out
