# Reproducibility

The committed toy instance permits offline validation and scoring. A clean Python 3.11+
environment can install the package with `pip install -e ".[dev]"`, then run `pytest`,
`ruff check .`, and `mypy`.

Official-data cross-validation is intentionally separate because benchmark files and the checker
are external artifacts. Record their exact source URL, retrieval timestamp, SHA-256 digest, and
tool output. Run the checker through `gmrp_alns.gmrp.checker.run_official_checker`; do not patch
the checker or count it as project-authored validation logic.

