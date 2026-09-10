"""Both adapters must support both injection vectors, so a cross-vendor grid can
run the same vector on every model and remove the tool_result-vs-user_message
confound."""

from types import SimpleNamespace

import pytest

from bastionprobe import run_attack
from bastionprobe.anthropic_target import make_anthropic_target
from bastionprobe.corpus import Payload
from bastionprobe.openai_target import make_openai_target


# --- fakes ---------------------------------------------------------------
class _AnthClient:
    def __init__(self):
        self.last = None

    class _M:
        def __init__(self, outer):
            self.outer = outer

        def create(self, **kw):
            self.outer.last = kw
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="ok")])

    @property
    def messages(self):
        return _AnthClient._M(self)


def _openai_client():
    box = {}

    class _C:
        def create(self, **kw):
            box["kw"] = kw
            msg = SimpleNamespace(content="ok", tool_calls=None)
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=_C()))
    return client, box


P = Payload(id="v", text="POISON {canary}", category="indirect_injection")


# --- anthropic vectors ---------------------------------------------------
def test_anthropic_user_message_vector_has_no_tool_use():
    c = _AnthClient()
    r = run_attack(make_anthropic_target(c, vector="user_message"), P)
    convo = c.last["messages"]
    assert convo[-1]["role"] == "user"
    assert r.canary in convo[-1]["content"]
    assert not any(
        isinstance(m["content"], list) and any(b.get("type") == "tool_use" for b in m["content"])
        for m in convo
        if isinstance(m.get("content"), list)
    )


def test_anthropic_tool_result_vector_is_default():
    c = _AnthClient()
    run_attack(make_anthropic_target(c), P)  # default
    convo = c.last["messages"]
    assert any(
        isinstance(m["content"], list) and any(b.get("type") == "tool_result" for b in m["content"])
        for m in convo
        if isinstance(m.get("content"), list)
    )


# --- openai vectors ------------------------------------------------------
def test_openai_tool_result_vector_emits_tool_message():
    client, box = _openai_client()
    run_attack(make_openai_target(client, vector="tool_result"), P)
    convo = box["kw"]["messages"]
    assert any(m.get("role") == "tool" and m.get("tool_call_id") for m in convo)


def test_openai_user_message_vector_is_default():
    client, box = _openai_client()
    run_attack(make_openai_target(client), P)  # default
    convo = box["kw"]["messages"]
    assert convo[-1]["role"] == "user" and not any(m.get("role") == "tool" for m in convo)


# --- validation ----------------------------------------------------------
def test_bad_vector_rejected():
    with pytest.raises(ValueError):
        make_anthropic_target(_AnthClient(), vector="nonsense")
    with pytest.raises(ValueError):
        make_openai_target(_openai_client()[0], vector="nonsense")
