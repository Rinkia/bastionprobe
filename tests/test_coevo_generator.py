"""Generator: payloads land in their target cell; incoherent cells skipped."""

from bastionprobe.coevo.axes import cell_of
from bastionprobe.coevo.generator import generate_batch, generate_one
import random


def test_generated_payload_maps_to_target_cell():
    key = "data-field|content-echo|de|echo"
    p = generate_one(key, random.Random(0))
    assert p is not None and cell_of(p).key == key
    assert "{canary}" in p.text  # content-echo -> canary check


def test_tool_cell_carries_tool_name():
    key = "egress-overt|tool-call|en|egress"
    p = generate_one(key, random.Random(1))
    assert p is not None and cell_of(p).key == key
    assert p.check == "tool" and p.forbidden_tool in ("send_email", "http_post")
    assert p.forbidden_tool in p.text


def test_incoherent_cell_is_skipped():
    # tool-call surface but echo action = no tool to call -> unreachable
    assert generate_one("data-field|tool-call|en|echo", random.Random(0)) is None


def test_batch_is_deterministic_and_maps_back():
    keys = ["data-field|content-echo|en|echo", "destructive|tool-call|fr|destructive"]
    a = generate_batch(keys, per_cell=2, seed=7)
    b = generate_batch(keys, per_cell=2, seed=7)
    assert [p.id for p in a] == [p.id for p in b]  # deterministic
    assert all(cell_of(p).key in keys for p in a)
