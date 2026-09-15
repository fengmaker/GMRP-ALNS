# Data

`toy/` contains a tiny official-format example transcribed from the format table in the
ROADEF/EURO 2012 problem definition. It exists for parser, validator, objective, and CLI tests.

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

Do not commit downloaded archives or extracted benchmarks until their redistribution terms are
explicitly reviewed. A future download command must write a manifest containing source URL,
UTC download timestamp, byte size, and SHA-256 digest. Version-controlled manifests live in
`manifests/`, while the artifacts themselves remain ignored. Never modify an official instance
while retaining its official name or reference result.
