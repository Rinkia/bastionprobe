"""bastionprobe CLI.

    bastionprobe run                      # fire at the bundled demo target
    bastionprobe run --target mod:func    # fire at your agent
    bastionprobe run --out results.jsonl  # also save every result

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
    parser = argparse.ArgumentParser(prog="bastionprobe")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="fire indirect-injection payloads at a target")
    run.add_argument(
        "--target",
        default="bastionprobe.demo:vulnerable_agent",
        help="module:function of the agent under test (default: bundled demo)",
    )
    run.add_argument("--out", type=Path, default=None, help="write results as JSONL")
    run.add_argument(
        "--category",
        default=None,
        help="only fire payloads whose category contains this substring",
    )
    run.add_argument(
        "--runs",
        type=int,
        default=1,
        help="fire each payload N times and report the land rate (models are "
        "non-deterministic; N>1 is the stable signal)",
    )

    hd = sub.add_parser(
        "harden", help="turn landed findings into agentbastion defenses"
    )
    hd.add_argument("results", type=Path, help="results.jsonl from `run --out`")
    hd.add_argument(
        "--out-dir",
        type=Path,
        default=Path("bastion_hardening"),
        help="where to write policy.yaml + injections.jsonl",
    )

    args = parser.parse_args(argv)

    if args.cmd == "run":
        target = _load_target(args.target)
        payloads = load_payloads()
        if args.category:
            payloads = [p for p in payloads if args.category in p.category]
        if not payloads:
            raise SystemExit("no payloads matched")
        if args.runs < 1:
            raise SystemExit("--runs must be >= 1")
        results = run_suite(target, payloads, runs=args.runs)
        print(render(results, out=args.out))
        if any(r.landed for r in results) and args.out:
            print(f"  -> harden the shield: bastionprobe harden {args.out}\n")
        # exit nonzero if anything landed - lets CI gate on it.
        return 1 if any(r.landed for r in results) else 0

    if args.cmd == "harden":
        from .harden import build_hardening, render_report, write_hardening

        h = build_hardening(args.results)
        policy, inj = write_hardening(h, args.out_dir)
        print(render_report(h, policy, inj))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
