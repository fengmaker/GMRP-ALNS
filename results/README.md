# Results

Generated experiment runs belong in ignored `results/runs/`; disposable local reports belong in
ignored `results/report/`. A completed, audited benchmark archive may be copied to a dedicated
version-controlled directory such as `results/m7/` only when it includes the frozen manifest,
projected raw JSONL, aggregate JSON/CSV, plots, checksums, and a verification record. Published
results must remain traceable to raw records, configuration, seed, time limit, dependency
versions, hardware, and Git commit. The M3
incremental-state microbenchmark, M4 one-second A-set acceptance run, M5 paired development gate,
and M6 exact-repair ablation are documented separately in `docs/m2_m3_verification.md`,
`docs/m4_verification.md`, `docs/m5_verification.md`, and `docs/m6_verification.md`; none is a
competitive benchmark.

M7's preregistered protocol is `docs/m7_protocol.md`. The completed archive is `results/m7/`, its
generated full table is `results/m7/report.md`, and the interpretation and limitations are in
`docs/m7_verification.md`. All 660 v2 records are official-checker valid; `checksums.json` covers
the remaining 11 archived files. The excluded 45-record v1 attempt remains under ignored
`results/runs/` and is documented as a corrected memory-measurement attempt, not benchmark data.
