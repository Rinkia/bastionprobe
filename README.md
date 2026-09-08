# agentprobe

**Pentest for AI agents.** Fire indirect prompt-injection payloads at your agent
and get a report of which ones land. Every payload that gets through is a hole a
runtime guard should close.

The offensive twin of [agentbastion](https://github.com/Rinkia/agentbastion)
(the runtime firewall). agentbastion *blocks* attacks in production; agentprobe
*launches* them before you ship. Scan with agentprobe → find holes → plug them
with agentbastion → re-scan → green.

```
agentprobe = Burp Suite for agents      (red team, pre-ship, on demand)
agentbastion = WAF for agents           (blue team, production, always on)
```

## The wedge: indirect prompt injection

The hardest injection to defend and the one most agents are blind to: the
payload doesn't come from the user — it rides inside a **tool result** the agent
reads mid-task (a fetched web page, a support ticket, a DB row, a file). If the
agent treats that data as instructions, you're owned.

agentprobe plants a payload in a tool output, runs your agent for one turn, and
scores whether it obeyed:

- **canary check** — the payload tells the agent to emit a unique random token.
  Token shows up in the reply ⇒ injection landed. (Fresh token per run — can't
  be faked or pre-trained.)
- **tool check** — the payload tells the agent to call a forbidden tool
  (`send_email`, `delete_file`, `http_post`, …). Agent calls it ⇒ landed.

## Install

```bash
pip install agentprobe   # (not yet published — clone + pip install -e . for now)
```

## Quick start

Zero setup — fire at the bundled demo targets:

```bash
agentprobe run                                      # vulnerable demo: 12/12 land
agentprobe run --target agentprobe.demo:safe_agent  # safe demo: 0 land
```

Fire at *your* agent — implement one function (see
[`examples/my_agent.py`](examples/my_agent.py)):

```python
from agentprobe import AgentResponse

def agent(messages, tool_outputs):        # tool_outputs = {tool_name: output}
    reply, tools_called = run_your_agent(messages, tool_outputs)
    return AgentResponse(text=reply, tool_calls=tools_called)
```

```bash
agentprobe run --target examples.my_agent:agent --out results.jsonl
```

Exit code is non-zero when any payload lands, so you can gate CI on it:

```bash
agentprobe run --target examples.my_agent:agent || echo "agent is vulnerable"
```

## The target contract

A target is any callable `(messages, tool_outputs) -> AgentResponse`. agentprobe
poisons one value in `tool_outputs`, runs your agent for one turn, and reads
back the reply text plus the names of any tools it called. It never looks inside
the agent — it measures behavior. Report what your agent *actually* did.

## Shared corpus with agentbastion

Payloads use the same `category` taxonomy as agentbastion's
`benchmark/corpus.jsonl` (`indirect_injection`, `exfiltration`,
`direct_injection`, …). Same strings, opposite direction: agentbastion reads a
row as "block this", agentprobe reads it as "fire this". A finding here maps
directly to a rule there.

## Status

Alpha. One attack class (indirect injection via tool output), 12 payloads across
5 languages. Reserved for later: direct injection, RAG poisoning, multi-agent
trust escalation, LLM-judge scoring. Payload PRs welcome.

## License

MIT.
