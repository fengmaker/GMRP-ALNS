# GMRP-ALNS

GMRP-ALNS is a reproducible research implementation for the
[ROADEF/EURO Challenge 2012 Machine Reassignment Problem](https://roadef.org/challenge/2012/en/).
It will combine an independently implemented validator and objective evaluator with local
search and adaptive large-neighborhood search. A classic Generalized Assignment Problem
(GAP) track is planned as a smaller exact-baseline track.

> **Status:** pre-alpha, M0–M1 foundation. The parser, full validator, objective evaluator,
> toy instance, and minimal CLI are present. Search algorithms and benchmark claims are TBD.

## Scope

The current code reads the official integer-stream instance format and assignment format,
checks capacity, conflict, spread, dependency, and transient-usage constraints, and computes
all official objective components. It deliberately does not copy a competition entry or
claim unmeasured performance.

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

- [Project knowledge and conversation log](QA.md)
- [Project plan](docs/project_plan.md)
- [Mathematical model](docs/mathematical_model.md)
- [Experiment protocol](docs/experiment_protocol.md)
- [Reproducibility](docs/reproducibility.md)
- [M1 verification record](docs/m1_verification.md)
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
