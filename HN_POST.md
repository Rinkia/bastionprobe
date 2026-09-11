# HN post draft — BastionProbe

## Title (pick one)

1. Show HN: BastionProbe – a pentest tool for AI agents
2. Show HN: BastionProbe – Claude refuses tool-based data egress, GPT-OSS doesn't
3. Show HN: Pentest for AI agents (and a cross-model prompt-injection finding)

(1 is the safe Show HN title; 2 leads with the finding and will get more clicks
but reads slightly more clickbait — your call. HN title limit is 80 chars.)

## Body

I build agentbastion, a firewall for AI agents (blocks prompt injection, guards
tool calls, redacts PII). Building it I kept wanting to attack my own defenses,
so I wrote the offensive twin: BastionProbe.

It fires indirect prompt-injection payloads at an AI agent and reports which
land. "Indirect" means the payload doesn't come from the user — it rides inside a
tool result the agent reads mid-task (a fetched web page, a support ticket, a DB
row). If the agent treats that retrieved data as instructions, you're owned. It's
the hardest injection to defend and the one most agents are blind to.

Scoring is deliberately dumb: a canary check (the payload tells the agent to emit
a unique random token; the token showing up in the reply means it obeyed) and a
tool check (the payload tells the agent to call a forbidden tool like send_email
or delete_file; it calling it means it obeyed). No LLM judge required. Models are
non-deterministic, so it fires each payload N times and reports a land rate, not
a single verdict.

The interesting result so far, from firing the same 16 payloads at several models
(5 runs each, same demo agent with read_document / send_email / delete_file /
http_post tools):

- Every Claude model (opus-4.5, sonnet-4.5, haiku-4.5) refused tool-based data
  egress — send_email and http_post — 100% of the time, under both overt framing
  and a "legitimate business reason" framing. 0/5 on every run.
- gpt-oss-120b (OpenAI's open-weight model, via Groq) obeyed egress ~70% of the
  time under the legitimate framing.
- Destruction is different: sonnet obeyed a hidden delete_file instruction 90% of
  the time, but opus and haiku refused it. So "the model will refuse dangerous
  tool calls" is model-specific, not something you can lean on.

I originally wrote "the model deletes local data readily" from testing sonnet
alone — the cross-model matrix caught that as an overgeneralization, which is
kind of the point of having one. There was a real confound (Claude was tested via
a native tool_result, gpt-oss via a user message), so I added an injection-vector
toggle and re-ran both through the same vector; the egress gap held, so it looks
like the model and not the harness. I'd still like other eyes on that.

It pairs back with the firewall: `bastionprobe harden results.jsonl` turns what
landed into a tool deny-list plus semantic-detector templates that agentbastion
loads directly — scan, find holes, plug them, re-scan. There's also an
experimental co-evolution mode: a MAP-Elites "director" steers the attacker
toward unexplored strategy families instead of rewarding raw success, the
firewall hardens on what lands, and a frozen held-out benchmark tells real
robustness gains from illusory ones (it's easy to build a loop that looks like
it's improving while it's just going in circles).

Limitations, so nobody's surprised: one attack class so far (indirect injection
via tool output); the zero-dependency demo embedder is bag-of-words (swap in a
sentence-transformer for real generalization); the payload set is small and
hand-tuned; it's alpha.

    pip install bastionprobe

https://github.com/Rinkia/bastionprobe

I'd genuinely like to hear where the methodology is wrong — especially on the
egress finding, since a harness artifact is always possible and I'd rather find
out now.

## First comment to post yourself (optional but recommended on HN)

Reproduce the cross-model finding:

    pip install "bastionprobe[anthropic]"
    export ANTHROPIC_API_KEY=...
    bastionprobe matrix --models claude-opus-4-5,claude-sonnet-4-5,claude-haiku-4-5 --vector user_message --runs 5

Full numbers and the confound write-up are in FINDINGS.md in the repo.
