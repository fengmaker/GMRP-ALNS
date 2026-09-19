# Reproducibility

The committed GMRP and GAP toy instances permit offline validation, scoring, exact solving, and
incremental-state checks. A clean Python 3.11+ environment can install the package with
`pip install -e ".[dev]"`, then run `pytest`, `ruff check .`, and `mypy`. M7 report generation and
worker-memory measurement additionally require `pip install -e ".[dev,experiments]"`.

For the v1.0 release smoke test, one command runs the complete offline toy path and asserts every
expected result:

```powershell
.\.venv\Scripts\python.exe scripts/demo.py
```

It parses, validates and scores GMRP; runs a fixed-seed/fixed-iteration Restricted ALNS search;
revalidates the emitted candidate; and proves the GAP toy reference optimum. Temporary output is
created outside the repository and removed automatically.

Official-data cross-validation is intentionally separate because benchmark files and the checker
are external artifacts. Record their exact source URL, retrieval timestamp, SHA-256 digest, and
tool output. Run the checker through `gmrp_alns.gmrp.checker.run_official_checker`; do not patch
the checker or count it as project-authored validation logic.

OR-Library data is also external. `python data/download_orlib.py gap1` records URL, retrieval
timestamp, byte size, SHA-256, objective direction, and published reference values. Use
`scripts/verify_gap_reference.py` for the exact-baseline cross-check. Incremental performance
measurements are intentionally separate from CI; commands, environment, results, and timing
boundaries are recorded in `docs/m2_m3_verification.md`.

M4 search acceptance is reproduced by `scripts/verify_m4_a_set.py`. It writes candidate files only
inside a temporary directory, rechecks them with the full validator and objective, and then calls
the unmodified official checker. The recorded one-second A1/A2 development run is documented in
`docs/m4_verification.md`; it is not a preregistered M7 quality benchmark. For deterministic
algorithm regression independent of machine speed, use a fixed seed together with
`--max-iterations`; elapsed-time fields themselves are observational and need not be byte-identical.

M5 adds two separate gates. `scripts/verify_m5_development.py` consumes the version-controlled
`configs/m5_development.json` paired comparison; `scripts/verify_m5_feasibility.py` checks Adaptive
ALNS outputs with the unmodified official checker over declared A/B instances. Exact recorded
results, the failed first configuration revision, and the in-budget warm-start revision are in
`docs/m5_verification.md`. These development-set observations are explicitly excluded from M7's
future reportable benchmark evidence.

M6 adds `scripts/verify_m6_development.py` and `configs/m6_development.json`. The script runs the
same Adaptive ALNS settings with Restricted CP-SAT Repair disabled and enabled, checks every final
assignment with the unmodified official checker, and fails if any exact call exceeds the declared
assignment-variable, solver-time, or bounded call-overhead limits. The exhaustive toy-neighborhood
oracle comparison and recorded A-set ablation are documented in `docs/m6_verification.md`. As with
earlier gates, these one-second development observations are excluded from M7 evidence.

M7 uses a frozen manifest and resumable, isolated, serial worker processes. With all externally
downloaded A/B files and the compiled checker in their documented `data/raw/roadef/` locations,
the following freezes a new run, executes just one reproducible subset, resumes the complete
matrix, and builds the standalone archive:

```powershell
.\.venv\Scripts\python.exe -m gmrp_alns.experiments freeze `
  configs/m7_benchmark.json results/runs/m7-local `
  --checker data/raw/roadef/checker/solution_checker.exe
.\.venv\Scripts\python.exe -m gmrp_alns.experiments run `
  results/runs/m7-local --instances a1_1
.\.venv\Scripts\python.exe -m gmrp_alns.experiments run results/runs/m7-local
.\.venv\Scripts\python.exe -m gmrp_alns.experiments report `
  results/runs/m7-local results/report/m7-local
```

The second command is the one-command experiment-subset reproduction after freezing. Resume first
verifies the source, environment, input, checker, manifest, and completed-record hashes. Profiling
is deliberately separate so instrumentation cannot alter benchmark observations:

```powershell
.\.venv\Scripts\python.exe scripts/profile_m7.py `
  data/raw/roadef/b/model_b_3.txt `
  data/raw/roadef/b/assignment_b_3.txt `
  results/report/profile_b3.json --time-limit 1
```

The checked-in M7 archive and interpretation are linked from `results/README.md` and
`docs/m7_verification.md`. The archive's `manifest.json`, `records.jsonl`, summaries, figures and
checksums are sufficient to regenerate and audit the report without external benchmark files.
