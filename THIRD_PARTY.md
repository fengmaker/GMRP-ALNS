# Third-party resources

This repository's implementation is original. The following resources define the problem or
are planned external inputs; they are not relicensed by this repository.

| Resource | Purpose | Repository policy |
|---|---|---|
| [ROADEF/EURO 2012 challenge](https://roadef.org/challenge/2012/en/) | Problem provenance | Cite only |
| [Problem definition v1.1](https://roadef.org/challenge/2012/files/problem_definition_v1_1.pdf) | Normative constraints, objective, and file formats | Cite; no copied source code |
| [Official instances and checker](https://roadef.org/challenge/2012/en/instances.php) | Cross-validation and benchmarks | Download to ignored `data/raw/`; preserve upstream terms and hashes |
| [OR-Library GAP](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/gapinfo.html) | GAP baseline data and reference values | Download externally; record instance direction, provenance, and hash |
| [OR-Tools](https://developers.google.com/optimization) | CP-SAT exact GAP baseline | Apache-2.0 dependency; version range declared in `pyproject.toml` |
| [psutil](https://github.com/giampaolo/psutil) | Isolated-worker process and peak-memory observation | BSD-3-Clause optional experiment dependency |
| [Matplotlib](https://matplotlib.org/) | Static M7 report figures | Matplotlib/PSF-compatible optional experiment dependency |

Development-only tools (`pytest`, `pytest-cov`, `Ruff`, and `mypy`) and all runtime/optional version
ranges are declared in `pyproject.toml`; the exact M7 environment is frozen in
`results/m7/manifest.json`. Generated plots are project artifacts; no third-party source code or
benchmark data is embedded in them.

Before adding any code or data from another project, record its exact URL, version/commit,
license, files used, and integration method here. The official checker must remain an external
executable; it must not be presented as project-authored code.
