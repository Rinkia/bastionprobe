"""Offline encoding bench: how often do the local defenders catch an encoded attack?

No model, no API key, deterministic. For every malicious corpus row (canary filled
with a fixed token) and every encoding, ask each installed defender whether it
would flag the text; do the same for every benign row to get the false-positive
rate. The `plain` row is the unencoded baseline.

    defender      flagged when
    agentbastion  InboundGuard blocks it (enforce) / a shadow detector would (shadow)
    supply        bastionsupply finds tool-poisoning, hidden-unicode or
                  encoded-injection in it (the scan bastiongate and bastionmesh reuse)

Run it before changing a detector (baseline) and after (evidence), and put both in
the CHANGELOG.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .encode import NAMES, encode

CANARY = "CANARY-0000"
_SUPPLY_FLAGS = {"tool-poisoning", "hidden-unicode", "encoded-injection"}


@dataclass
class Cell:
    flagged: int = 0
    total: int = 0
    shadow: int = 0  # agentbastion only: allowed, but a shadow detector would have blocked

    def rate(self) -> float:
        return self.flagged / self.total if self.total else 0.0


@dataclass
class BenchResult:
    defenders: tuple[str, ...]
    encodings: tuple[str, ...]
    malicious: dict = field(default_factory=dict)  # (defender, encoding) -> Cell
    benign: dict = field(default_factory=dict)
    skipped: dict = field(default_factory=dict)  # defender -> reason


def _defenders(wanted: tuple[str, ...]):
    """{name: callable(text) -> (flagged, shadow_flagged)} for the importable ones."""
    found, skipped = {}, {}
    if "agentbastion" in wanted:
        try:
            from agentbastion.inbound import InboundGuard

            guard = InboundGuard()

            def ab(text: str) -> tuple[bool, bool]:
                result = guard.scan(text)
                return guard.is_blocked(result), guard.would_flip(result)

            found["agentbastion"] = ab
        except Exception as e:  # noqa: BLE001 - optional defender
            skipped["agentbastion"] = f"not installed ({type(e).__name__})"
    if "supply" in wanted:
        try:
            from bastionsupply.models import Server, Tool
            from bastionsupply.scanner import scan

            def sup(text: str) -> tuple[bool, bool]:
                report = scan(Server("bench", (Tool(name="bench", description=text),)))
                return any(f.check in _SUPPLY_FLAGS for f in report.findings), False

            found["supply"] = sup
        except Exception as e:  # noqa: BLE001
            skipped["supply"] = f"not installed ({type(e).__name__})"
    return found, skipped


def _samples():
    """(malicious texts, benign texts, encoded-row texts by label) from bastioncorpus."""
    from bastioncorpus import load_corpus

    malicious, benign, enc_rows = [], [], []
    for r in load_corpus():
        text = r.render(CANARY)
        if r.tactic.startswith("enc-"):
            enc_rows.append((r.tactic[4:], r.is_malicious, text))
        elif r.is_malicious:
            malicious.append(text)
        else:
            benign.append(text)
    return malicious, benign, enc_rows


def run_bench(encodings: tuple[str, ...] = NAMES,
              defenders: tuple[str, ...] = ("agentbastion", "supply")) -> BenchResult:
    found, skipped = _defenders(defenders)
    malicious, benign, enc_rows = _samples()
    result = BenchResult(defenders=tuple(found), encodings=("plain",) + tuple(encodings), skipped=skipped)
    for name, check in found.items():
        for enc in result.encodings:
            for texts, bucket in ((malicious, result.malicious), (benign, result.benign)):
                cell = bucket.setdefault((name, enc), Cell())
                for text in texts:
                    shown = text if enc == "plain" else encode(text, enc)
                    flagged, shadow = check(shown)
                    cell.total += 1
                    cell.flagged += flagged
                    cell.shadow += shadow
        for enc, is_mal, text in enc_rows:  # the corpus's own encoded rows count too
            if enc not in result.encodings:
                continue
            cell = (result.malicious if is_mal else result.benign).setdefault((name, enc), Cell())
            flagged, shadow = check(text)
            cell.total += 1
            cell.flagged += flagged
            cell.shadow += shadow
    return result


def format_bench(r: BenchResult) -> str:
    lines = ["encoding-bench (offline, deterministic): % flagged",
             "  detection = malicious rows flagged (higher is better); "
             "FP = benign rows flagged (lower is better); "
             "+shadow = extra rows a shadow detector would block", ""]
    head = f"  {'encoding':<11}" + "".join(f"{d + ' det':>18}{d + ' FP':>16}" for d in r.defenders)
    lines.append(head)
    for enc in r.encodings:
        row = f"  {enc:<11}"
        for d in r.defenders:
            m, b = r.malicious.get((d, enc), Cell()), r.benign.get((d, enc), Cell())
            det = f"{m.rate():.0%}" + (f" +{m.shadow / m.total:.0%}" if m.shadow and m.total else "")
            row += f"{det:>18}{b.rate():>16.0%}"
        lines.append(row)
    for d, why in r.skipped.items():
        lines.append(f"  (skipped {d}: {why})")
    return "\n".join(lines)


def to_json(r: BenchResult) -> str:
    def cells(bucket):
        return {f"{d}/{e}": {"flagged": c.flagged, "shadow": c.shadow, "total": c.total}
                for (d, e), c in sorted(bucket.items())}

    return json.dumps({"defenders": list(r.defenders), "encodings": list(r.encodings),
                       "malicious": cells(r.malicious), "benign": cells(r.benign),
                       "skipped": r.skipped}, indent=2)
