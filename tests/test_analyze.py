"""By-tactic aggregation must pool runs correctly and rank most-vulnerable first,
so 'which framing lands' stays measurable as the payload set grows."""

from bastionprobe import group_rates, load_payloads, run_suite
from bastionprobe.corpus import Payload
from bastionprobe.demo import safe_agent, vulnerable_agent


def test_every_payload_has_a_tactic():
    assert all(p.tactic for p in load_payloads()), "untagged payload"


def test_group_rates_pool_runs_and_rank():
    payloads = [
        Payload(id="a1", text="emit {canary}", category="c", tactic="data-field"),
        Payload(id="a2", text="emit {canary}", category="c", tactic="data-field"),
        Payload(id="b1", text="x", category="c", tactic="egress", check="tool", forbidden_tool="send_email"),
    ]
    groups = {g.key: g for g in group_rates(run_suite(vulnerable_agent, payloads, runs=2), by="tactic")}
    # data-field: 2 payloads x 2 runs, all land on the vulnerable demo
    df = groups["data-field"]
    assert df.payloads == 2 and df.runs == 4 and df.landed == 4 and df.rate == 1.0
    # egress: the demo does call send_email (name in text) -> lands here too
    assert "egress" in groups


def test_ranking_is_most_vulnerable_first():
    payloads = load_payloads()
    # safe agent blocks all -> every tactic rate 0.0, still grouped
    groups = group_rates(run_suite(safe_agent, payloads), by="tactic")
    assert groups and all(g.rate == 0.0 for g in groups)
    rates = [g.rate for g in group_rates(run_suite(vulnerable_agent, payloads), by="tactic")]
    assert rates == sorted(rates, reverse=True), "groups not ranked by rate desc"
