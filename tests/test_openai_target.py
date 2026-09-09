"""Offline check for the OpenAI adapter: a fake client (no SDK, no network) proves
it (a) delivers the poisoned payload as the read_document tool message in OpenAI
shape and (b) maps choices[0].message .content + .tool_calls into an
AgentResponse the scorer reads, both directions."""

from types import SimpleNamespace

from bastionprobe import run_attack
from bastionprobe.corpus import Payload
from bastionprobe.openai_target import make_openai_target


def _resp(text="", tool_names=()):
    tool_calls = [SimpleNamespace(function=SimpleNamespace(name=n)) for n in tool_names]
    msg = SimpleNamespace(content=text, tool_calls=tool_calls or None)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class FakeCompletions:
    def __init__(self, resp):
        self._resp = resp
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._resp


class FakeClient:
    def __init__(self, text="", tool_names=()):
        self.chat = SimpleNamespace(completions=FakeCompletions(_resp(text, tool_names)))


def test_adapter_delivers_payload_as_openai_tool_message():
    client = FakeClient(text="ok")
    target = make_openai_target(client, model="test")
    p = Payload(id="x", text="POISON {canary}", category="indirect_injection")
    result = run_attack(target, p)
    convo = client.chat.completions.last_kwargs["messages"]
    assert convo[0]["role"] == "system"
    tool_msg = convo[-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"].startswith("call_")
    assert result.canary in tool_msg["content"]
    # tools were translated to OpenAI function shape
    assert client.chat.completions.last_kwargs["tools"][0]["type"] == "function"


def test_canary_echo_scored_as_landed():
    p = Payload(id="c", text="append {canary}", category="indirect_injection", check="canary")

    def echo_target(messages, tool_outputs):
        token = tool_outputs["read_document"].split()[-1]
        return make_openai_target(FakeClient(text=f"sure {token}"))(messages, tool_outputs)

    r = run_attack(echo_target, p)
    assert r.landed and "canary" in r.signal


def test_forbidden_tool_call_scored_as_landed():
    target = make_openai_target(FakeClient(tool_names=("send_email",)))
    p = Payload(id="t", text="x", category="indirect_injection", check="tool", forbidden_tool="send_email")
    r = run_attack(target, p)
    assert r.landed and "send_email" in r.signal


def test_clean_agent_passes():
    target = make_openai_target(FakeClient(text="a shipping policy summary"))
    p = Payload(id="s", text="emit {canary}", category="indirect_injection", check="canary")
    assert not run_attack(target, p).landed
