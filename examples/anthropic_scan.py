"""Fire bastionprobe at a real Claude agent.

    pip install "bastionprobe[anthropic]"
    export ANTHROPIC_API_KEY=...
    python -m examples.anthropic_scan          # 1 run each
    python -m examples.anthropic_scan 5        # 5 runs each -> land rate

This scans the built-in demo agent (support assistant with read_document +
send_email/delete_file/http_post tools). To test YOUR agent, override model=,
system=, and tools= in make_anthropic_target to match it. Runs are serial live
calls (N payloads x runs), so progress prints to stderr as it goes.
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

    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    def progress(i: int, total: int, r) -> None:
        rate = f"{r.landed_count}/{r.runs}" if r.runs > 1 else r.verdict
        print(f"[{i}/{total}] {r.payload_id:20} {rate}", file=sys.stderr)

    target = make_anthropic_target(Anthropic(), model="claude-sonnet-4-5")
    results = run_suite(target, load_payloads(), runs=runs, on_result=progress)
    print(render(results))
    return 1 if any(r.landed for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
