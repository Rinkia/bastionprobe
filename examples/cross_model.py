"""Cross-model matrix: fire the suite at several Anthropic models and compare.

    pip install "bastionprobe[anthropic]"
    export ANTHROPIC_API_KEY=...
    python -m examples.cross_model                       # default trio, 3 runs
    python -m examples.cross_model 5 claude-sonnet-4-5 claude-haiku-4-5

A bad model id just shows `err` for its column - the rest of the matrix still
runs. To add a non-Anthropic model, write a Target of the same shape and drop it
into the `targets` dict.
"""

from __future__ import annotations

import sys

from bastionprobe import load_payloads, make_anthropic_target, run_matrix
from bastionprobe.report import format_matrix

DEFAULT_MODELS = ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"]


def main() -> int:
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit('pip install "bastionprobe[anthropic]" first')

    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    models = sys.argv[2:] or DEFAULT_MODELS

    client = Anthropic()
    targets = {m: make_anthropic_target(client, model=m) for m in models}

    def progress(model, i, total, r):
        rate = f"{r.landed_count}/{r.runs}" if r.runs > 1 else r.verdict
        print(f"[{model}] [{i}/{total}] {r.payload_id:20} {rate}", file=sys.stderr)

    matrix = run_matrix(targets, load_payloads(), runs=runs, on_result=progress)
    print(format_matrix(matrix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
