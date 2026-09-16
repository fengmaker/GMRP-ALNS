# Changelog

All notable project changes are documented here. The project follows Semantic Versioning once
the public API stabilizes.

## [Unreleased]

### Added

- Initial Python package, project metadata, quality configuration, and GitHub Actions workflow.
- ROADEF 2012 model and assignment parsers with structural validation.
- Full hard-constraint validator and official objective evaluator.
- JSON CLI commands for parsing, validating, and scoring assignments.
- Official-format toy fixture, checker adapter, documentation, and M0–M1 tests.
- Reproducible downloader manifests and official-checker dataset cross-check scripts.
- Repository-level AI instructions and an append-only project knowledge/conversation log.
- Classic GAP track with strict OR-Library parsing, explicit objective direction, a CP-SAT exact
  model, cost/regret construction and repair, relocate/swap local search, and unified JSON CLI.
- Reproducible OR-Library `gap1` downloader manifest and reference-value verification script.
- Cached GMRP `SolutionState` with incremental relocate/swap feasibility, objective deltas,
  apply/undo, sparse service counts, candidate prefiltering, and Top-K ranking.
- Ten-thousand-move oracle comparison tests and an A-instance incremental evaluation benchmark.
- Chinese input/output and quick-start guide covering file formats, execution paths, core code,
  reading order, and current project boundaries.
- Strict-feasible GMRP first/best relocate search and relocate/swap variable-neighborhood descent.
- Seeded random-removal LNS with bounded greedy or regret repair and incumbent protection.
- Unified GMRP `solve` CLI with time/iteration limits, official assignment output, convergence
  traces, time-to-best, objective components, candidate counts, and operator statistics.
- Reproducible M4 A1/A2 verification script and record; all ten one-second development runs
  improved their initial assignments and matched the unmodified official checker.
- Adaptive ALNS with five destroy operators, three strict-feasible repair operators, simulated
  annealing, segmented roulette weights, in-budget relocate warm start, restart, and historical
  best protection.
- Per-operator acceptance/best/failure/timing/weight statistics, weight history, and objective
  component traces exposed through the GMRP JSON result.
- Frozen M5 paired-development and A/B feasibility scripts, complete official B-set provenance,
  and official-checker verification records.
