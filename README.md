# GMRP-ALNS

GMRP-ALNS is a reproducible research implementation for the
[ROADEF/EURO Challenge 2012 Machine Reassignment Problem](https://roadef.org/challenge/2012/en/).
It combines an independently implemented validator and objective evaluator with an incremental
move engine, local search, basic LNS, and adaptive large-neighborhood search. Restricted exact
repair is the next stage.
A classic Generalized Assignment Problem (GAP) track provides a smaller exact and heuristic baseline.

> **Status:** pre-alpha, M0–M5 complete. The GMRP parser, full validator/objective,
> incremental relocate/swap state, first/best local search, VND, random-removal LNS, Adaptive
> ALNS, and the classic GAP exact/heuristic track are present. Restricted exact repair remains TBD.

## Scope

The current code reads the official integer-stream instance format and assignment format,
checks capacity, conflict, spread, dependency, and transient-usage constraints, and computes
all official objective components. Cached GMRP state supports feasibility checks, exact objective
deltas, apply/undo, and Top-K relocate candidates. Search supports strict-feasible first/best
relocate improvement, relocate/swap VND, random removal, and Adaptive ALNS with five destroy and
three repair operators, simulated annealing, adaptive weights, and restart under a shared seed and
time-limit protocol. The GAP track supports the OR-Library format, CP-SAT,
cost/regret construction, repair, relocate, and swap. It deliberately does not copy a competition
entry or claim unmeasured performance.

## Quick start

Python 3.11 or newer is required.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"  # Windows PowerShell
.venv/Scripts/python -m pytest
.venv/Scripts/python -m ruff check .
```

Run the bundled official-format toy example:

```bash
gmrp-alns parse data/toy/model_toy.txt
gmrp-alns validate data/toy/model_toy.txt data/toy/assignment_toy.txt data/toy/solution_toy.txt
gmrp-alns score data/toy/model_toy.txt data/toy/assignment_toy.txt data/toy/solution_toy.txt
gmrp-alns solve data/toy/model_toy.txt data/toy/assignment_toy.txt \
  --algorithm adaptive-alns --time-limit 2 --seed 42 --output candidate.sol
gmrp-alns gap parse data/toy/gap_toy.txt --sense minimize
gmrp-alns gap solve data/toy/gap_toy.txt --sense minimize --algorithm exact --reference-value 8
```

The toy optimized assignment has official example cost `2411`. Commands emit JSON so they
can be used by tests and experiment scripts. Validation returns exit code `0` for a feasible
solution and `1` for an infeasible solution; malformed input returns `2`.

## Data and reproducibility

External benchmark files are not committed. See [data/README.md](data/README.md) for official
sources and expected placement. `data/raw/` and generated run outputs are ignored by Git.
Every published result must retain its configuration, seed, time limit, environment, and raw
output. No result numbers will be added here before they are reproducible.

## Project documents

- [中文输入输出与快速上手指南](docs/getting_started_zh.md)
- [Project knowledge and conversation log](QA.md)
- [Project plan](docs/project_plan.md)
- [Mathematical model](docs/mathematical_model.md)
- [Experiment protocol](docs/experiment_protocol.md)
- [Reproducibility](docs/reproducibility.md)
- [M1 verification record](docs/m1_verification.md)
- [M2–M3 verification record](docs/m2_m3_verification.md)
- [M4 verification record](docs/m4_verification.md)
- [M5 verification record](docs/m5_verification.md)
- [Roadmap](ROADMAP.md)
- [Third-party sources](THIRD_PARTY.md)

## License

Project-authored source code is available under the MIT License. External data, papers, and
tools retain their own terms; see [THIRD_PARTY.md](THIRD_PARTY.md).

## Official A-set cross-check

The A files remain ignored, but their source URLs and SHA-256 hashes are committed in
`data/manifests/`. To reproduce the M1 cross-check:

```bash
python data/download_roadef.py a1
python data/download_roadef.py a2
python data/download_roadef.py checker
g++ data/raw/roadef/checker/solution_checker.cc data/raw/roadef/checker/solution_checker_run.cc -O2 -std=c++11 -o data/raw/roadef/checker/solution_checker
python scripts/crosscheck_official_dataset.py data/raw/roadef/checker/solution_checker data/raw/roadef/a1
python scripts/crosscheck_official_dataset.py data/raw/roadef/checker/solution_checker data/raw/roadef/a2
```

## M2–M3 verification

OR-Library stores the objective direction outside the integer data stream. Pass it explicitly:

```bash
python data/download_orlib.py gap1
python scripts/verify_gap_reference.py data/manifests/orlib_gap1.json --time-limit 10 --seed 42
```

The recorded M2 run reproduced all five official `gap1` maximization reference values. The M3
property test applies and undoes 10,000 seeded legal moves against the full validator/objective.
An additional recorded A1_2 run checked 10,000 legal relocate deltas and measured 111.94x higher
evaluation throughput than full validation plus objective recomputation on that machine:

```bash
python scripts/benchmark_incremental.py \
  data/raw/roadef/a1/model_a1_2.txt \
  data/raw/roadef/a1/assignment_a1_2.txt \
  --samples 10000 --seed 42
```

This is a development-machine measurement, not a cross-machine performance claim; full details
and limitations are in the M2–M3 verification record.

## M4 verification

The committed M4 verification command runs one-second seeded VND searches on all local A1/A2
instances, then checks every emitted assignment with both project oracles and the unmodified
official checker:

```bash
python scripts/verify_m4_a_set.py \
  data/raw/roadef/checker/solution_checker \
  data/raw/roadef/a1 data/raw/roadef/a2 \
  --algorithm vnd-first --time-limit 1 --seed 42
```

The recorded development run improved all ten initial assignments and all ten final objective
values matched the official checker. This is an M4 acceptance check, not a competitive benchmark;
see the M4 verification record for the exact results and limitations.

## M5 verification

The frozen M5 development configuration compares Random LNS and Adaptive ALNS over three A
instances and three seeds under equal one-second budgets. The recorded run produced six Adaptive
ALNS wins in nine pairs and a 416,047,975 lower summed objective; all 18 assignments passed the
official checker. A separate feasibility gate verified all ten A1/A2 instances plus B1/B2:

```bash
python scripts/verify_m5_development.py configs/m5_development.json \
  data/raw/roadef/checker/solution_checker data/raw/roadef
python scripts/verify_m5_feasibility.py \
  data/raw/roadef/checker/solution_checker data/raw/roadef/b \
  --time-limit 1 --seed 42 --instances b_1 b_2
```

These are machine-dependent M5 engineering gates, not the preregistered M7 benchmark. See the M5
verification record for the frozen criteria, configuration revision, results, and limitations.
