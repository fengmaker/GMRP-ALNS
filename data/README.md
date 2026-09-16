# Data

`toy/` contains a tiny official-format GMRP example transcribed from the format table in the
ROADEF/EURO 2012 problem definition and a project-authored GAP instance. They support parser,
validator, objective, exact-baseline, heuristic, incremental-state, and CLI tests.

Official benchmark downloads belong below ignored `raw/`:

```text
data/raw/roadef/a1/
data/raw/roadef/a2/
data/raw/roadef/b/
data/raw/roadef/checker/
data/raw/orlib/
```

Normative sources:

- Problem definition: https://roadef.org/challenge/2012/files/problem_definition_v1_1.pdf
- Instances and checker: https://roadef.org/challenge/2012/en/instances.php
- Program/evaluation protocol: https://roadef.org/challenge/2012/en/reponse.php
- OR-Library GAP format and reference values:
  https://people.brunel.ac.uk/~mastjjb/jeb/orlib/gapinfo.html

Reproducible downloads:

```text
python data/download_roadef.py a1
python data/download_orlib.py gap1
```

Do not commit downloaded archives or extracted benchmarks until their redistribution terms are
explicitly reviewed. Each download command writes a manifest containing source URL,
UTC download timestamp, byte size, and SHA-256 digest. Version-controlled manifests live in
`manifests/`, while the artifacts themselves remain ignored. Never modify an official instance
while retaining its official name or reference result.
