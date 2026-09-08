"""The bridge must turn landed findings into loadable agentbastion defenses:
denied tools for the tool policy, cleaned injection strings for the semantic
detector. Only landed rows count; canary scaffolding is stripped."""

import json

from bastionprobe import load_payloads, run_suite
from bastionprobe.demo import safe_agent, vulnerable_agent
from bastionprobe.harden import build_hardening, write_hardening
from bastionprobe.report import write_jsonl


def _results_file(tmp_path, agent):
    results = run_suite(agent, load_payloads())
    p = tmp_path / "results.jsonl"
    write_jsonl(results, p)
    return p


def test_vulnerable_run_yields_deny_tools_and_injections(tmp_path):
    h = build_hardening(_results_file(tmp_path, vulnerable_agent))
    # the demo's forbidden tools all get called -> all land in the deny-list
    assert set(h.deny_tools) == {"send_email", "delete_file", "http_post"}
    assert h.injections, "landed injections should produce templates"
    # canary scaffolding stripped
    assert all("{canary}" not in row["text"] for row in h.injections)
    assert all(row["label"] == "malicious" for row in h.injections)


def test_safe_run_yields_nothing_to_harden(tmp_path):
    h = build_hardening(_results_file(tmp_path, safe_agent))
    assert h.deny_tools == [] and h.injections == []


def test_written_files_are_wellformed(tmp_path):
    h = build_hardening(_results_file(tmp_path, vulnerable_agent))
    policy, inj = write_hardening(h, tmp_path / "out")
    assert "deny:" in policy.read_text(encoding="utf-8")
    assert "delete_file" in policy.read_text(encoding="utf-8")
    rows = [json.loads(l) for l in inj.read_text(encoding="utf-8").splitlines()]
    assert rows and set(rows[0]) == {"text", "label", "category"}
