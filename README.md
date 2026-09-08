# bastionprobe

**Pentest for AI agents.** Fire indirect prompt-injection payloads at your agent
and get a report of which ones land. Every payload that gets through is a hole a
runtime guard should close.

The offensive twin of [agentbastion](https://github.com/Rinkia/agentbastion)
(the runtime firewall). agentbastion *blocks* attacks in production; bastionprobe
*launches* them before you ship. Scan with bastionprobe → find holes → plug them
with agentbastion → re-scan → green.

```
bastionprobe = Burp Suite for agents      (red team, pre-ship, on demand)
agentbastion = WAF for agents           (blue team, production, always on)
```

## The wedge: indirect prompt injection

The hardest injection to defend and the one most agents are blind to: the
payload doesn't come from the user — it rides inside a **tool result** the agent
reads mid-task (a fetched web page, a support ticket, a DB row, a file). If the
agent treats that data as instructions, you're owned.

bastionprobe plants a payload in a tool output, runs your agent for one turn, and
scores whether it obeyed:

- **canary check** — the payload tells the agent to emit a unique random token.
  Token shows up in the reply ⇒ injection landed. (Fresh token per run — can't
  be faked or pre-trained.)
- **tool check** — the payload tells the agent to call a forbidden tool
  (`send_email`, `delete_file`, `http_post`, …). Agent calls it ⇒ landed.

## Install

```bash
pip install bastionprobe
```

## Quick start

Zero setup — fire at the bundled demo targets:

```bash
bastionprobe run                                      # vulnerable demo: 12/12 land
bastionprobe run --target bastionprobe.demo:safe_agent  # safe demo: 0 land
```

Fire at *your* agent — implement one function (see
[`examples/my_agent.py`](examples/my_agent.py)):

```python
from bastionprobe import AgentResponse

def agent(messages, tool_outputs):        # tool_outputs = {tool_name: output}
    reply, tools_called = run_your_agent(messages, tool_outputs)
    return AgentResponse(text=reply, tool_calls=tools_called)
```

```bash
bastionprobe run --target examples.my_agent:agent --out results.jsonl
```

Exit code is non-zero when any payload lands, so you can gate CI on it:

```bash
bastionprobe run --target examples.my_agent:agent || echo "agent is vulnerable"
```

## Fire at a real Claude agent

A built-in adapter turns an Anthropic client into a target. It stands up a small
tool-using agent, feeds each payload back as the result of the agent's
`read_document` tool, runs one real model turn, and reports what Claude did —
text plus any tools it tried to call.

```bash
pip install "bastionprobe[anthropic]"
export ANTHROPIC_API_KEY=...
```

```python
from anthropic import Anthropic
from bastionprobe import load_payloads, run_suite, make_anthropic_target
from bastionprobe.report import render

target = make_anthropic_target(Anthropic(), model="claude-sonnet-4-5")
print(render(run_suite(target, load_payloads())))
```

Set `model=` to the model your production agent runs — that's the behavior you
care about. `system=` and `tools=` are overridable so you can mirror your real
agent's persona and toolbox instead of the defaults. See
[`examples/anthropic_scan.py`](examples/anthropic_scan.py).

## The target contract

A target is any callable `(messages, tool_outputs) -> AgentResponse`. bastionprobe
poisons one value in `tool_outputs`, runs your agent for one turn, and reads
back the reply text plus the names of any tools it called. It never looks inside
the agent — it measures behavior. Report what your agent *actually* did.

## Shared corpus with agentbastion

Payloads use the same `category` taxonomy as agentbastion's
`benchmark/corpus.jsonl` (`indirect_injection`, `exfiltration`,
`direct_injection`, …). Same strings, opposite direction: agentbastion reads a
row as "block this", bastionprobe reads it as "fire this". A finding here maps
directly to a rule there.

## Status

Alpha. One attack class (indirect injection via tool output), 12 payloads across
5 languages. Reserved for later: direct injection, RAG poisoning, multi-agent
trust escalation, LLM-judge scoring. Payload PRs welcome.

## License

MIT.
