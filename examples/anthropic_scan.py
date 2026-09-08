"""Fire bastionprobe at a real Claude agent.

    pip install "bastionprobe[anthropic]"
    export ANTHROPIC_API_KEY=...
    python examples/anthropic_scan.py

This scans the built-in demo agent (support assistant with read_document +
send_email/delete_file/http_post tools). To test YOUR agent, override model=,
system=, and tools= in make_anthropic_target to match it.
"""

from __future__ import annotations

import sys

from bastionprobe import load_payloads, make_anthropic_target, run_suite
from bastionprobe.report import render


def main() -> int:
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit("pip install \"bastionprobe[anthropic]\" first")

    target = make_anthropic_target(Anthropic(), model="claude-sonnet-4-5")
    results = run_suite(target, load_payloads())
    print(render(results))
    return 1 if any(r.landed for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
