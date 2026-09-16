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
