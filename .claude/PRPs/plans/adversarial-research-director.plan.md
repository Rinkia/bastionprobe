# Plan: C — Adversarial Research Director (co-evolution runtime)

## Summary
Add **C**, a research director that closes a red-team/blue-team co-evolution loop
between **A** (agentbastion, the defender) and **B** (bastionprobe, the attacker).
C does not attack A; it operates on B — steering B's search toward *empty* regions
of a behavioral map, curating a quality-diversity archive of effective **and
dissimilar** attacks, selecting a Hall-of-Fame replay set so A does not forget old
holes, and diagnosing whether A's absolute robustness (a frozen benchmark) is
actually improving or just spinning. The objective is **behavioral coverage of
effective, distinct attacks**, not raw attack success.

## User Story
As a security researcher running an agent red-team/blue-team loop, I want a
director that maximizes the diversity of *effective* attack strategies (not just
their count), so that A is hardened against whole families of attack rather than
overfit to whatever B last found, and so I can tell real progress from illusory.

## Problem → Solution
Today B fires a fixed payload set at a single target and reports land rates; there
is no loop, no memory, no pressure toward unexplored strategies, and no guard
against B collapsing onto A's current decision boundary. → C adds a MAP-Elites
archive over a behavioral map, novelty-weighted selection, explicit exploration
pressure on B, Hall-of-Fame replay into A's hardening, and frozen-benchmark
progress diagnosis — wired into an autonomous round loop.

## Metadata
- **Complexity**: XL (new subsystem; phased, each phase independently shippable)
- **Source PRD**: N/A (free-form spec supplied via /prp-plan)
- **PRD Phase**: N/A
- **Estimated Files**: ~10 new modules + tests + 1 CLI command
- **Decisions locked** (from clarifying questions):
  - Scope = **full autonomous system** (C + orchestration + A hardening/eval), built in 5 phases.
  - C's brain = **embedding-hybrid** novelty (deterministic axis cells + optional embedding distance; reuse agentbastion's `EmbedFn` shape, fall back to pure cell-distance when no embedder).
  - Behavioral axes = **derived from existing payload/result metadata** (`tactic`, `category` language prefix, `check`, `forbidden_tool`) — **no `Payload`/`AttackResult` schema change**.

---

## UX Design

### Before
```
B (fixed payloads) ──fire──> single target ──> land-rate table.  No loop, no memory.
```

### After
```
        ┌──────────────────────── round ────────────────────────┐
  B.generate(direction) → attacks
     → run_suite(A_defender_target, attacks) → list[AttackResult]
     → C.round(results, benchmark_score) → DirectorReport (JSON)
          • classify → cells, novelty
          • archive update (1 elite per cell, quality-diversity)
          • direction_for_B (target empty cells / families)
          • mode-collapse guard
          • replay set (Hall of Fame)
          • progress diagnosis (frozen benchmark delta)
     → A.harden(replay + new elites)   → A' (more robust)
     → benchmark(A') on FROZEN corpus  → absolute robustness
        └───────────────── direction feeds next round ───────────┘
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| CLI | `bastionprobe run/matrix` | + `bastionprobe coevolve` | runs the loop, prints per-round report |
| Output | land-rate table | + `DirectorReport` JSON (spec schema) | machine-readable for a harness |
| Memory | none | MAP-Elites archive persisted as JSONL | the system's behavioral memory |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `agentprobe/bastionprobe/runner.py` | 27-70 | `AttackResult` fields C consumes (`tactic`, `category`, `check`, `forbidden_tool`, `payload_text`, `land_rate`, `landed`); `run_suite` signature + `on_result` |
| P0 | `agentprobe/bastionprobe/analyze.py` | all | `group_rates`/`GroupRate` — the aggregation + frozen-dataclass + sorted-desc pattern C's archive/report mirror |
| P0 | `agentprobe/bastionprobe/harden.py` | all | `build_hardening`/`Hardening` — how attacks become A's defenses (the A-hardening arm) |
| P0 | `agentfirewall/benchmark/eval.py` | 26-70 | `evaluate(rows, guard) -> {recall,f1,fn,...}` — the FROZEN benchmark scorer for A's absolute robustness |
| P0 | `agentfirewall/agentbastion/semantic.py` | 20-55 | `EmbedFn` type + `_cosine` — the embedder shape and cosine C reuses for embedding-hybrid novelty |
| P1 | `agentprobe/bastionprobe/target.py` | all | `Target` contract + `rate_limited` — the composable-wrapper idiom for `make_guarded_target` (A as a defender Target) |
| P1 | `agentfirewall/agentbastion/inbound.py` | 249-284 | `InboundGuard.scan`/`is_blocked` — A's block decision the defender Target calls |
| P1 | `agentprobe/bastionprobe/matrix.py` | all | `run_matrix` resilience pattern (isolate a failing unit, keep going) to mirror in the round loop |
| P1 | `agentprobe/bastionprobe/cli.py` | 60-120 | subcommand + stderr-progress pattern for `coevolve` |
| P2 | `agentprobe/bastionprobe/demo.py` | all | `vulnerable_agent` — the inner agent A guards in the defender Target |
| P2 | `agentprobe/tests/test_analyze.py` | all | test style: deterministic demo agents, frozen-dataclass asserts |

## External Documentation
No external research needed — MAP-Elites / quality-diversity and novelty search are
established techniques implemented here from first principles; all dependencies are
internal (`AttackResult`, `EmbedFn`, agentbastion `evaluate`). Note in code comments
that the archive is MAP-Elites and novelty is a QD/novelty-search blend.

---

## Patterns to Mirror

### FROZEN_DATACLASS + SORTED_AGGREGATION
// SOURCE: agentprobe/bastionprobe/analyze.py (GroupRate, group_rates)
```python
@dataclass(frozen=True)
class GroupRate:
    key: str; payloads: int; runs: int; landed: int; any_landed: int
    @property
    def rate(self) -> float: return self.landed / self.runs if self.runs else 0.0
# ... buckets via defaultdict(list); return sorted(out, key=lambda g: g.rate, reverse=True)
```
Mirror for `Cell`, `Elite`, `DirectorReport` (frozen dataclasses; deterministic sort).

### COMPOSABLE_TARGET_WRAPPER
// SOURCE: agentprobe/bastionprobe/target.py (rate_limited)
```python
def rate_limited(target: Target, per_minute: float) -> Target:
    def wrapped(messages, tool_outputs) -> AgentResponse: ...; return target(messages, tool_outputs)
    return wrapped
```
Mirror for `make_guarded_target(firewall, inner) -> Target`: scan the poisoned
tool_output with A; if blocked, return a safe `AgentResponse`; else delegate to `inner`.

### RESULTS_CONSUMER (reuse the existing pipeline)
// SOURCE: agentprobe/bastionprobe/runner.py (AttackResult, run_suite)
C consumes `list[AttackResult]` straight from `run_suite(A_target, payloads)`.
`quality = r.land_rate` (effectiveness vs A), `novelty_text = r.payload_text`,
cell axes from `r.tactic / r.category / r.check / r.forbidden_tool`.

### EMBED_FN (optional, hybrid novelty)
// SOURCE: agentfirewall/agentbastion/semantic.py (EmbedFn, _cosine)
```python
EmbedFn = Callable[[Sequence[str]], Sequence[Sequence[float]]]
# cosine over pure-python vectors; fail-soft -> return () / 0.0 novelty contribution
```
Accept an optional `embed_fn`; when `None`, novelty = pure cell-distance (deterministic).

### FROZEN_BENCHMARK
// SOURCE: agentfirewall/benchmark/eval.py (evaluate)
```python
m = evaluate(rows, guard)   # -> {"recall":..,"f1":..,"fn":..,...}
```
A's absolute robustness = `recall`/`f1` on a corpus held out of A's hardening.

### CLI_SUBCOMMAND + STDERR_PROGRESS
// SOURCE: agentprobe/bastionprobe/cli.py (matrix/run)
Add-parser + `print(..., file=sys.stderr)` for per-round progress; JSON report to stdout.

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `bastionprobe/coevo/__init__.py` | CREATE | subpackage exports |
| `bastionprobe/coevo/axes.py` | CREATE | map `AttackResult` → behavioral `Cell` from metadata |
| `bastionprobe/coevo/archive.py` | CREATE | MAP-Elites archive (1 elite/cell), empty-cell frontier, JSONL persist |
| `bastionprobe/coevo/novelty.py` | CREATE | embedding-hybrid novelty (cell-distance + optional cosine) |
| `bastionprobe/coevo/director.py` | CREATE | `Director.round()` — the 7-step decision + `DirectorReport` JSON |
| `bastionprobe/coevo/benchmark.py` | CREATE | frozen-benchmark bridge to agentbastion `evaluate`; stall detection |
| `bastionprobe/coevo/defender.py` | CREATE | `make_guarded_target(firewall, inner)` — A as a bastionprobe Target |
| `bastionprobe/coevo/generator.py` | CREATE | B generator: mutate/template payloads toward target cells (deterministic) |
| `bastionprobe/coevo/orchestrator.py` | CREATE | the autonomous round loop tying B→A→C→harden→benchmark |
| `bastionprobe/cli.py` | UPDATE | add `coevolve` subcommand |
| `bastionprobe/__init__.py` | UPDATE | export `Director`, `Archive`, `run_coevolution` |
| `tests/test_coevo_*.py` | CREATE | offline tests per module (deterministic; no network) |
| `pyproject.toml` | UPDATE | bump version; `[all]` already covers optional model SDKs |
| `FINDINGS.md` / `README.md` | UPDATE | document the loop + `coevolve` |

## NOT Building
- **No LLM in C.** Classification and novelty stay deterministic/embedding-based (per decision). An LLM-driven generator for B may come later, but Phase-4 B is mutation-based.
- **No retraining of a model A.** A = agentbastion (rules + detectors); "A evolves" = ingesting hardening (signatures + `SemanticDetector` templates) via the existing `harden` bridge — not gradient training.
- **No new payload schema.** Axes are derived from existing `AttackResult`/`Payload` fields; `tactic` etc. are not extended.
- **No distributed/parallel execution.** Round loop is serial (reuse `run_suite`); parallelism is out of scope.
- **No persistence backend beyond JSONL** for the archive/benchmark history.

---

## Step-by-Step Tasks

### Phase 1 — C core (deterministic, offline): the spec's component

#### Task 1.1: `axes.py` — behavioral cell from metadata
- **ACTION**: Define the behavioral map axes and `cell_of(result) -> Cell`.
- **IMPLEMENT**: `@dataclass(frozen=True) Cell(framing, surface, language, action)`.
  Derive from an `AttackResult` (or `Payload`): `framing = result.tactic`;
  `language = _lang(result.category)` (prefix `de_/fr_/es_/it_` → that, else `en`);
  `action = result.forbidden_tool_family` (`egress` for send_email/http_post,
  `destructive` for delete_file, else `echo`); `surface = result.check`
  (`canary`→"content-echo", `tool`→"tool-call"). Provide `cell.key -> str` and
  `axis_space()` listing all known axis values (for empty-cell enumeration).
- **MIRROR**: FROZEN_DATACLASS.
- **IMPORTS**: `from ..runner import AttackResult`; `from dataclasses import dataclass`.
- **GOTCHA**: axes must be enumerable so empty cells exist before they are filled —
  hardcode the known axis-value sets from the current payload taxonomy; unknown
  values fall into an `"other"` bucket rather than raising.
- **VALIDATE**: `test_axes`: each bundled payload maps to a stable cell; egress tools → `action=egress`.

#### Task 1.2: `archive.py` — MAP-Elites quality-diversity store
- **ACTION**: `Archive` keeping the single best representative per cell.
- **IMPLEMENT**: `@dataclass(frozen=True) Elite(cell_key, attack_id, payload_text, quality, novelty, round)`.
  `Archive.update(result, quality, novelty, round) -> UpdateResult{"added"|"replaced"|"rejected"}`
  — replace the cell's elite only if `quality` strictly higher (ties → higher novelty).
  `filled_cells()`, `empty_cells(axis_space)`, `elites()`, `to_jsonl()/from_jsonl()`.
- **MIRROR**: FROZEN_DATACLASS + SORTED_AGGREGATION (defaultdict cells; sorted output).
- **GOTCHA**: quality-diversity means **never** globally rank-and-cull; each cell is
  independent. Do not evict a low-quality elite from cell X because cell Y has a
  better one — that would collapse coverage (anti-degeneration rule 2).
- **VALIDATE**: `test_archive`: higher-quality result replaces same-cell elite; different-cell results coexist; JSONL round-trips.

#### Task 1.3: `novelty.py` — embedding-hybrid novelty score
- **ACTION**: `novelty_score(result, archive, embed_fn=None) -> float` in `[0,1]`.
- **IMPLEMENT**: cell-distance component = normalized count of axes differing from the
  nearest filled cell (1.0 if its cell is empty/unseen). Embedding component (when
  `embed_fn` given) = `1 - max cosine(embed(text), embed(elite.text))` over elites.
  Blend `0.5*cell + 0.5*embed`; if no `embed_fn`, novelty = cell component only.
- **MIRROR**: EMBED_FN + `_cosine` (copy the pure-python cosine; fail-soft).
- **GOTCHA**: embedder is optional and may throw — wrap in try/except and fall back
  to the deterministic cell component (mirror agentbastion's fail-soft detectors).
- **VALIDATE**: `test_novelty`: an attack in an empty cell scores ~1.0; a near-duplicate of an elite scores low; works with `embed_fn=None`.

#### Task 1.4: `director.py` — the round decision + JSON report
- **ACTION**: `Director.round(results, benchmark_score, a_version) -> DirectorReport`.
- **IMPLEMENT** the 7 steps in order: (1) classify each result → cell + novelty +
  outcome; (2) novelty eval; (3) `archive.update` using `quality=r.land_rate`;
  (4) `direction_for_B` = pick empty cells nearest the frontier + never-tried
  families, emit **axis targets** (not payload content); (5) mode-collapse: if
  ≥`collapse_frac` of new results fall in ≤`collapse_cells` cells or mean pairwise
  novelty < `collapse_nov`, flag + choose a distant target region; (6) replay =
  Hall-of-Fame elites (one per filled cell, prefer high quality × staleness);
  (7) progress: `benchmark_delta` vs last round; if frozen benchmark flat for
  `stall_rounds` while land rate stays high → `progresso_reale=false`, propose
  strategy change. Serialize to the spec's **exact JSON keys** (Italian):
  `classificazione, archivio_update, direzione_per_B, mode_collapse, replay_per_A, diagnosi_progresso`.
- **MIRROR**: SORTED_AGGREGATION; return a frozen `DirectorReport` with a `.to_json()`.
- **GOTCHA**: **anti-degeneration rule 1** — never rank B on raw success; the
  selection/pressure signal must be `quality × novelty`, and `direction_for_B` must
  target *coverage* (empty cells), or B glues to A's boundary. Encode this so a
  high-success/low-novelty round still yields exploration pressure.
- **VALIDATE**: `test_director`: synthetic results across cells produce a report whose
  `direzione_per_B.celle_target` are genuinely empty; a mono-cell batch trips
  `mode_collapse.rilevato=true`; flat benchmark → `progresso_reale=false`.

### Phase 2 — Frozen benchmark + progress truth

#### Task 2.1: `benchmark.py` — absolute-robustness bridge
- **ACTION**: `frozen_score(guard, corpus_path) -> BenchmarkScore` + `BenchmarkHistory` with stall detection.
- **IMPLEMENT**: call agentbastion `benchmark.eval.evaluate(rows, guard)`; keep
  `recall`/`f1`/`fn`. `BenchmarkHistory.append(score)`, `.stalled(n, eps)`.
- **IMPORTS**: `from agentbastion.benchmark.eval import evaluate, load_corpus` (optional import; only needed when A=agentbastion).
- **GOTCHA**: the benchmark corpus MUST be held out of A's hardening inputs, or the
  metric is contaminated — document this and assert the replay/harden set and the
  frozen corpus are disjoint by id.
- **VALIDATE**: `test_benchmark`: rising recall → not stalled; flat recall for n rounds → stalled.

### Phase 3 — A as a defender Target (blue side)

#### Task 3.1: `defender.py` — `make_guarded_target`
- **ACTION**: wrap an agentbastion `Firewall`/`InboundGuard` + an inner agent into a bastionprobe `Target`.
- **IMPLEMENT**: `make_guarded_target(guard, inner=vulnerable_agent) -> Target`:
  scan the poisoned `tool_outputs[POISONED_TOOL]` with `guard`; if `is_blocked`,
  return `AgentResponse(text="[blocked by A]", tool_calls=())`; else delegate to
  `inner`. Result: `run_suite` land rate against this target = attacks that got
  **past A** and landed → exactly "effective against A".
- **MIRROR**: COMPOSABLE_TARGET_WRAPPER.
- **GOTCHA**: A guards the *tool result* (indirect injection), so call the
  tool-result scan path, not just the user-input scan.
- **VALIDATE**: `test_defender`: a payload A blocks → `landed=False`; one A misses → delegates → `landed=True`.

### Phase 4 — B generator (red side, deterministic)

#### Task 4.1: `generator.py` — direction-driven payload generation
- **ACTION**: `generate(direction, n) -> list[Payload]` producing candidates aimed at target cells.
- **IMPLEMENT**: a mutation/template engine: for each `celle_target`, synthesize
  payloads by combining axis values (framing × language × action × surface) from a
  bank of fragments keyed by axis value; seed from existing bundled payloads of the
  nearest filled cell and mutate the axis that differs. Deterministic (seedable RNG).
- **GOTCHA**: this is the deliberately simple arm (`ponytail:` combinatorial mutation,
  not learned generation). Mark the ceiling and the LLM-generator upgrade path.
- **VALIDATE**: `test_generator`: asking for an empty target cell yields ≥1 payload whose `cell_of` equals that cell.

### Phase 5 — Orchestrator + CLI

#### Task 5.1: `orchestrator.py` — the autonomous loop
- **ACTION**: `run_coevolution(defender, generator, director, benchmark, rounds, runs) -> list[DirectorReport]`.
- **IMPLEMENT** per round: `payloads = generator.generate(direction)` →
  `results = run_suite(defender_target, payloads, runs=runs)` →
  `report = director.round(results, benchmark.score(guard), a_version)` →
  `guard = harden_into_A(guard, report.replay + new_elites)` (via `build_hardening`)
  → append benchmark. Stop early on `progresso_reale=false` past `stall_rounds`
  (anti-degeneration rule 3). Mirror `run_matrix` resilience: a failing round is
  isolated and logged, loop continues.
- **MIRROR**: matrix.py resilience; runner `on_result` progress.
- **GOTCHA**: keep the frozen benchmark corpus separate from hardening inputs (Task 2.1 gotcha).
- **VALIDATE**: `test_orchestrator`: a short run with the demo defender + mutation
  generator fills new cells over rounds and returns well-formed reports; a defender
  that blocks everything yields empty archive but valid reports (no crash).

#### Task 5.2: CLI `coevolve`
- **ACTION**: `bastionprobe coevolve --rounds N --runs M [--embed ...] [--benchmark corpus.jsonl]`.
- **IMPLEMENT**: build default demo defender (agentbastion guard + `vulnerable_agent`),
  mutation generator, `Director`; run loop; per-round progress to stderr; final
  archive + last `DirectorReport` JSON to stdout; `--out` persists archive JSONL.
- **MIRROR**: CLI_SUBCOMMAND + STDERR_PROGRESS.
- **VALIDATE**: `bastionprobe coevolve --rounds 2` runs offline (agentbastion installed) and prints JSON.

---

## Testing Strategy

### Unit Tests
| Test | Input | Expected | Edge? |
|---|---|---|---|
| test_axes | each bundled payload | stable `Cell`; egress tools→`action=egress` | unknown value→`other` |
| test_archive | two results same cell, diff quality | higher-quality replaces; JSONL round-trips | empty archive |
| test_novelty | empty-cell attack / near-dup | ~1.0 / low; works `embed_fn=None` | embedder throws→fallback |
| test_director | multi-cell batch / mono-cell batch / flat benchmark | empty-cell targets / `mode_collapse=true` / `progresso_reale=false` | zero new attacks |
| test_benchmark | rising vs flat recall | not-stalled vs stalled | first round (no prior) |
| test_defender | payload A blocks / misses | `landed=False` / `True` | missing guard |
| test_generator | empty target cell | ≥1 payload mapping to that cell | no direction |
| test_orchestrator | 2-round demo run / block-all defender | cells fill, valid reports / empty archive no crash | 0 rounds |

### Edge Cases Checklist
- [ ] Empty round (B produced nothing) → director returns valid report, no exploration crash
- [ ] Archive JSONL absent/corrupt → start fresh (fail-soft, mirror storage try/except ethos)
- [ ] `embed_fn=None` and embedder-throws → deterministic novelty
- [ ] Benchmark corpus overlaps hardening set → assertion/warning
- [ ] All-blocking A (empty archive) and all-missing A (every cell fills) both handled

---

## Validation Commands

### Static / imports
```bash
cd C:/Projects/Varie/agentprobe && python -c "import bastionprobe.coevo as c; print(c.__all__)"
```
EXPECT: exports present; importing needs no network/SDK/key.

### Unit tests
```bash
cd C:/Projects/Varie/agentprobe && python -m pytest -q tests/test_coevo_*.py
```
EXPECT: all pass, no network.

### Full suite (no regressions)
```bash
cd C:/Projects/Varie/agentprobe && python -m pytest -q
```
EXPECT: existing 31 + new coevo tests pass.

### Loop smoke (offline, agentbastion installed)
```bash
cd C:/Projects/Varie/agentprobe && python -m bastionprobe.cli coevolve --rounds 2 --runs 2
```
EXPECT: two rounds run, DirectorReport JSON printed, archive fills at least one cell.

### Build
```bash
cd C:/Projects/Varie/agentprobe && python -m build -q && python -m twine check dist/*
```
EXPECT: PASSED; `coevo` package + any data files shipped.

### Manual
- [ ] Run `coevolve --rounds 5`; confirm `direzione_per_B` targets change round-to-round and cover new cells
- [ ] Confirm a deliberately mono-strategy generator trips `mode_collapse`
- [ ] Confirm frozen benchmark recall rises as elites are hardened into A (and stall detection fires when it plateaus)

---

## Acceptance Criteria
- [ ] All phase tasks completed
- [ ] `Director.round` emits the exact spec JSON schema (Italian keys)
- [ ] Archive is true quality-diversity: one elite/cell, coverage never sacrificed for global quality
- [ ] Novelty weighs equal to success in selection/pressure (anti-degeneration rule 1 enforced)
- [ ] Empty-cell exploration prioritized; mode-collapse detected and countered
- [ ] Frozen benchmark held out of hardening; stall → illusory-progress declared
- [ ] All tests pass; no network in unit tests; no regressions

## Completion Checklist
- [ ] Reuses `AttackResult`/`run_suite`/`harden`/`EmbedFn` (no parallel pipeline)
- [ ] Frozen dataclasses + deterministic sorts (mirrors analyze.py)
- [ ] Fail-soft on embedder/storage (mirrors agentbastion detectors/storage ethos)
- [ ] `ponytail:` comment on the mutation generator's ceiling + LLM upgrade path
- [ ] No payload schema change; axes derived from metadata
- [ ] README + FINDINGS updated; version bumped; release via existing OIDC workflow

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Deriving axes from coarse metadata gives too few cells (weak map) | Med | Med | Start with 4 axes from tactic/lang/action/surface (~dozens of cells); document that richer axes = a payload-schema follow-up if coverage saturates |
| Mutation generator can't reach some empty cells (no fragments) | Med | Med | Seed fragment bank from bundled payloads; log unreachable cells as `famiglie_da_esplorare` for manual authoring; LLM-generator is the named upgrade |
| Benchmark contamination (hardening leaks into frozen set) | Med | High | Enforce id-disjointness assertion between replay/harden inputs and frozen corpus (Task 2.1) |
| "A evolves" via rules-hardening may plateau fast (regex ceiling) | Med | Med | This is itself a finding — stall detection surfaces it; embedding-template hardening (SemanticDetector) extends A's reach beyond regex |
| Embedding novelty needs an embedder the user may not have | Low | Low | Optional; deterministic cell-distance fallback keeps everything runnable offline |

## Notes
- C consumes what the pipeline already produces (`list[AttackResult]`), so Phase 1
  is genuinely standalone and matches the spec's INPUT/OUTPUT — it is the smallest
  shippable slice and de-risks the rest.
- "A evolves" is deliberately the existing `harden` bridge, not model training —
  keeps the loop honest and reuses proven code; the frozen benchmark makes any
  illusory progress visible (the whole point of anti-degeneration rule 3).
- Phasing lets each slice ship + release on its own (1→5) rather than one XL drop.
