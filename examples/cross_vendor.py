"""Cross-vendor matrix: Anthropic + OpenAI models in one grid.

    pip install "bastionprobe[anthropic,openai]"
    export ANTHROPIC_API_KEY=...
    export OPENAI_API_KEY=...
    python -m examples.cross_vendor            # default set, 5 runs

The whole point: does a finding that holds across the Claude family (e.g. the
egress refusal) also hold on GPT? A missing key or bad model id just shows `err`
for that column - the rest of the grid still runs.
"""

from __future__ import annotations

import os
import sys

from bastionprobe import load_payloads, make_anthropic_target, make_openai_target, run_matrix
from bastionprobe.report import format_matrix

ANTHROPIC_MODELS = ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"]
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini"]


def main() -> int:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    targets = {}

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from anthropic import Anthropic

            ac = Anthropic()
            targets.update({m: make_anthropic_target(ac, model=m) for m in ANTHROPIC_MODELS})
        except ImportError:
            print('anthropic SDK missing; pip install "bastionprobe[anthropic]"', file=sys.stderr)

    if os.environ.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI

            oc = OpenAI()
            targets.update({m: make_openai_target(oc, model=m) for m in OPENAI_MODELS})
        except ImportError:
            print('openai SDK missing; pip install "bastionprobe[openai]"', file=sys.stderr)

    if not targets:
        sys.exit("set ANTHROPIC_API_KEY and/or OPENAI_API_KEY first")

    def progress(model, i, total, r):
        rate = f"{r.landed_count}/{r.runs}" if r.runs > 1 else r.verdict
        print(f"[{model}] [{i}/{total}] {r.payload_id:20} {rate}", file=sys.stderr)

    matrix = run_matrix(targets, load_payloads(), runs=runs, on_result=progress)
    print(format_matrix(matrix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
