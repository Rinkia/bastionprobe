"""The matrix must run every target, aggregate per model×tactic, and survive a
target that errors (bad model id / outage) without sinking the others."""

from bastionprobe import load_payloads, run_matrix, tactic_matrix
from bastionprobe.demo import safe_agent, vulnerable_agent
from bastionprobe.matrix import overall_rate
from bastionprobe.report import format_matrix


def _broken(messages, tool_outputs):
    raise RuntimeError("bad model id")


def test_matrix_runs_all_targets_and_isolates_failures():
    payloads = load_payloads()
    targets = {"vuln": vulnerable_agent, "safe": safe_agent, "broken": _broken}
    matrix = run_matrix(targets, payloads, runs=2)

    assert matrix["vuln"] is not None and matrix["safe"] is not None
    assert matrix["broken"] is None  # errored target isolated, not raised

    assert overall_rate(matrix["vuln"]) == 1.0
    assert overall_rate(matrix["safe"]) == 0.0
    assert overall_rate(matrix["broken"]) is None


def test_tactic_grid_shape():
    payloads = load_payloads()
    matrix = run_matrix({"vuln": vulnerable_agent, "broken": _broken}, payloads)
    tactics, models, grid = tactic_matrix(matrix)
    assert set(models) == {"vuln", "broken"}
    assert "egress-overt" in tactics and "data-field" in tactics
    # vuln lands everything; broken column is None for every tactic
    assert all(grid[t]["vuln"].rate == 1.0 for t in tactics)
    assert all(grid[t]["broken"] is None for t in tactics)


def test_format_matrix_renders_err_column():
    matrix = run_matrix({"vuln": vulnerable_agent, "broken": _broken}, load_payloads())
    out = format_matrix(matrix)
    assert "cross-model land rate by tactic" in out
    assert "err" in out and "OVERALL" in out
