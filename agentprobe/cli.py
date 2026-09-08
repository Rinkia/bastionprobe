"""agentprobe CLI.

    agentprobe run                      # fire at the bundled demo target
    agentprobe run --target mod:func    # fire at your agent
    agentprobe run --out results.jsonl  # also save every result

--target is "module:function" (import path). The function must match the
Target contract in target.py: (messages, tool_outputs) -> AgentResponse.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from .corpus import load_payloads
from .report import render
from .runner import run_suite
from .target import Target


def _load_target(spec: str) -> Target:
    if ":" not in spec:
        raise SystemExit(f"--target must be 'module:function', got {spec!r}")
    mod_name, func_name = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    try:
        return getattr(mod, func_name)
    except AttributeError:
        raise SystemExit(f"{mod_name!r} has no attribute {func_name!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agentprobe")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="fire indirect-injection payloads at a target")
    run.add_argument(
        "--target",
        default="agentprobe.demo:vulnerable_agent",
        help="module:function of the agent under test (default: bundled demo)",
    )
    run.add_argument("--out", type=Path, default=None, help="write results as JSONL")
    run.add_argument(
        "--category",
        default=None,
        help="only fire payloads whose category contains this substring",
    )

    args = parser.parse_args(argv)

    if args.cmd == "run":
        target = _load_target(args.target)
        payloads = load_payloads()
        if args.category:
            payloads = [p for p in payloads if args.category in p.category]
        if not payloads:
            raise SystemExit("no payloads matched")
        results = run_suite(target, payloads)
        print(render(results, out=args.out))
        # exit nonzero if anything landed - lets CI gate on it.
        return 1 if any(r.landed for r in results) else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
