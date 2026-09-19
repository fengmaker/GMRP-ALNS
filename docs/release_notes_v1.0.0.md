# GMRP-ALNS v1.0.0

GMRP-ALNS v1.0.0 is the first complete research release. It provides an independently implemented
correctness foundation, several reproducible heuristic and matheuristic solvers, and a frozen
short-budget evidence archive for the ROADEF/EURO 2012 Machine Reassignment Problem.

## Highlights

- Strict official-format model and assignment parsing.
- Full validation of capacity, conflict, spread, dependency, and transient-usage constraints.
- Full official objective with load, balance, process-move, service-move, and machine-move costs.
- Incremental relocate/swap feasibility, exact deltas, apply/undo, candidate filtering and ranking.
- First/best relocate, relocate/swap VND, Random LNS, and Adaptive ALNS.
- Five destroy and three strict-feasible repair operators, simulated annealing, segmented adaptive
  weights, restart and historical-best protection.
- Fixed-complement Restricted CP-SAT Repair with bounded domains, assignment variables, local time,
  one solver worker, full-oracle verification, and safe fallback.
- Separate classic GAP track with OR-Library parsing, CP-SAT and constructive/local heuristics.
- JSON CLI, official assignment output, convergence and operator telemetry.
- Immutable experiment manifests, isolated/resumable workers, official-checker audit, aggregation,
  plots, memory/timing measurement, and artifact checksums.

## Verified evidence

- All ten official A1/A2 initial assignments match the unmodified official checker's feasibility
  and objective values.
- Five OR-Library `gap1` exact reference values are reproduced.
- 10,000 seeded legal incremental moves match the full validator/objective and restore exact state
  after undo.
- The frozen M7 study contains 660/660 official-valid returned assignments with no missing or
  failed records.
- In that requested one-second study, mean relative improvements over the initial assignment are
  12.032% for Relocate, 12.008% for VND, 5.584% for Random LNS, 9.126% for ALNS, and 8.994% for
  Restricted ALNS.
- Relocate and VND beat/tied/lost against ALNS in 72/10/18 and 74/8/18 paired observations.
  Restricted ALNS is nearly neutral at 32/35/33 and -0.131 percentage points mean gain.

Every number above maps to a committed verification document or `results/m7` record. The release
does not claim best-known-solution gaps or competition-level performance.

## Reproduce the offline demo

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts/demo.py
```

The demo parses and validates the bundled GMRP toy, reproduces its cost 2411 with a fixed
seed/iteration search, revalidates the written candidate, and proves the bundled GAP optimum 8.

## Known limitations

- M7 uses one Windows host and a single requested one-second budget; it does not cover 10/60/300
  seconds, multiple machines, statistical significance, BKS gaps, or competition programs.
- 208/660 solver calls exceed the preregistered 1.1-second tolerance. None of the held-out B3–B10
  ALNS/Restricted pairs have both observations within tolerance.
- The no-restart ablation is inconclusive because no compared run reached the restart interval.
- The cProfile run is instrumented separately and its objective is excluded from quality results.
- Official data and checker binaries are external and must be downloaded under their own terms.

## Release contents

- English and Chinese project entry points: `README.md`, `README_zh.md`.
- Architecture and flow diagrams: `docs/architecture.md`.
- Detailed model, algorithm and reproduction documentation under `docs/`.
- Two-to-three-minute recording script: `docs/demo_video_zh.md`.
- Evidence-backed resume wording and interview questions: `docs/portfolio_zh.md`.
- Frozen experiment archive: `results/m7/`.
- Citation, MIT license and third-party provenance: `CITATION.cff`, `LICENSE`, `THIRD_PARTY.md`.
- Release-size, package, link, secret and claims audit: `docs/release_audit_v1.0.0.md`.

## Compatibility

Python 3.11, 3.12 and 3.13 are covered by CI. v1.0.0 is the first declared release, so no prior
stable public API is deprecated. CLI JSON and experiment schemas should still be treated as
research interfaces whose future incompatible changes will be documented in the changelog.
