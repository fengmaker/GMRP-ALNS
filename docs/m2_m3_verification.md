# M2–M3 verification record

Date: 2026-09-16

This record separates correctness checks from machine-specific performance evidence. External
OR-Library and ROADEF files remain ignored; their source URLs and SHA-256 hashes are recorded in
`data/manifests/`.

## Environment

- Windows 11 10.0.22621, AMD64 Family 25 Model 68, 16 logical processors reported by the OS;
- Python 3.12.4;
- OR-Tools 9.15.6755;
- CP-SAT reference checks use one worker and seed 42.

## M2: classic GAP track

The committed `gap_toy.txt` minimization instance has exact optimum 8. The external official
`gap1.txt` is parsed explicitly as maximization; objective direction is not inferred or negated.

Reproduction:

```bash
python data/download_orlib.py gap1
python scripts/verify_gap_reference.py data/manifests/orlib_gap1.json --time-limit 10 --seed 42
```

Recorded result:

| Instance | CP-SAT objective | OR-Library reference | Status |
|---|---:|---:|---|
| gap1-1 | 336 | 336 | optimal, match |
| gap1-2 | 327 | 327 | optimal, match |
| gap1-3 | 339 | 339 | optimal, match |
| gap1-4 | 341 | 341 | optimal, match |
| gap1-5 | 326 | 326 | optimal, match |

Cost-greedy and regret-greedy construction use bounded fail-first repair when direct construction
dead-ends. On `gap1-1`, both returned validator-confirmed feasible assignments in the recorded
run; their objectives were 316 and 330 respectively. These are feasibility/implementation checks,
not quality claims against other solvers.

## M3: incremental GMRP state

The property test uses seed 42 for 10,000 legal relocate/swap selections. For every move it:

1. compares the cached total delta with full objective recomputation;
2. applies the move and compares the complete cached state with a fresh reconstruction;
3. checks the full validator;
4. undoes the move and requires an exactly equal immutable snapshot.

The committed test uses the GMRP toy, which exercises load, balance, process/service/machine move
costs, transient capacity, conflict, spread, and dependency, plus a separate feasible swap fixture.

The external A1_2 performance/correctness run used:

```bash
python scripts/benchmark_incremental.py \
  data/raw/roadef/a1/model_a1_2.txt \
  data/raw/roadef/a1/assignment_a1_2.txt \
  --samples 10000 --seed 42
```

Recorded output summary:

- dimensions: 1,000 processes, 100 machines, 4 resources, 980 services;
- legal relocate pool: 18,779;
- all 10,000 sampled deltas matched the full validator plus full objective oracle;
- cached evaluation: 0.2043838 seconds, about 48,928 evaluations/second;
- full recomputation: 22.8784963 seconds, about 437 evaluations/second;
- measured speedup: 111.9389x.

Timing includes Python assignment construction, full validation, and full objective evaluation in
the oracle path. It excludes candidate-pool construction in both timed paths. This is one local
development-machine run and is intentionally not generalized to other hardware or instance sets.
