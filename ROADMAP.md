# Roadmap

The detailed milestones and acceptance criteria live in `docs/project_plan.md`.

- [x] **M0 — repository foundation:** package layout, metadata, documentation skeleton,
  test/lint/type-check configuration, CI, licensing, and data-source records.
- [x] **M1 — full-evaluation foundation:** official-format parser, assignment I/O, full hard
  constraint validator, full objective evaluator, toy instance, minimal CLI, checker adapter,
  and focused unit/integration tests.
- [x] **M1 cross-check — official A data/checker:** download A1/A2 and checker source, record
  hashes, and compare all ten initial assignments and objective values with the official checker.
- [x] **M2 — classic GAP track:** OR-Library parser, exact small-instance baseline, greedy and
  regret construction, relocate/swap, and unified result JSON.
- [x] **M3 — GMRP incremental state:** cached state plus relocate/swap delta, apply, undo, and
  randomized comparison against the full evaluator.
- [x] **M4 — local search and basic LNS:** seeded first/best relocate search,
  relocate/swap VND, random removal with greedy/regret repair, telemetry, and official A-set
  checker verification.
- [ ] **M5 — adaptive ALNS.**
- [ ] **M6 — restricted exact repair.**
- [ ] **M7 — preregistered benchmark and technical report.**
- [ ] **M8 — public release and evidence-backed project summary.**
