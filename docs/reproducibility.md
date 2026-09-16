# Reproducibility

The committed GMRP and GAP toy instances permit offline validation, scoring, exact solving, and
incremental-state checks. A clean Python 3.11+ environment can install the package with
`pip install -e ".[dev]"`, then run `pytest`, `ruff check .`, and `mypy`.

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
