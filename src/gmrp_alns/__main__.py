"""Allow ``python -m gmrp_alns`` to run the CLI."""

from gmrp_alns.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

