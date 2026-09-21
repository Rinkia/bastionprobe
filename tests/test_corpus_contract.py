"""Consumer contract: bastionprobe still parses the shared corpus (PRP §1.3).

bastionprobe consumes bastioncorpus's `to_probe` output. If that format drifts,
`_load_from_bastioncorpus` swallows the error and silently falls back to the
bundled snapshot — recall degrades with no failure. This test defeats that
silent fallback by asserting the corpus path actually produced usable payloads.
"""

from __future__ import annotations

from bastionprobe.corpus import Payload, _load_from_bastioncorpus


def test_corpus_payloads_load_and_are_usable():
    payloads = _load_from_bastioncorpus()
    assert payloads is not None, (
        "corpus path failed and fell back — to_probe output no longer parses; "
        "check the bastioncorpus contract"
    )
    assert payloads, "corpus returned zero fireable payloads"
    for p in payloads:
        assert isinstance(p, Payload)
        assert p.id and p.text
        assert p.channel == "tool_output"
        assert p.check in {"canary", "tool"}
        # to_probe's own invariant, re-checked on the consumer side:
        if p.check == "tool":
            assert p.forbidden_tool, f"{p.id}: check=tool without forbidden_tool"
