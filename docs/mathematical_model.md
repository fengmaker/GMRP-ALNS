# Mathematical model

The normative definition is
[ROADEF/EURO 2012 problem definition v1.1](https://roadef.org/challenge/2012/files/problem_definition_v1_1.pdf).
This document records the implementation interpretation used by the full evaluator.

For every process, a solution stores exactly one zero-based destination machine index. The
validator checks:

1. non-transient resource usage does not exceed machine capacity;
2. transient resource usage counts every process on the union of its original and destination
   machines (once when both are the same);
3. two processes of one service never share a machine;
4. each service occupies at least its declared number of distinct locations; and
5. for every directed dependency `s -> d`, each neighborhood containing `s` also contains `d`.

The objective is a weighted sum of resource load above safety capacity, balance penalties on
available resources, process move cost, the maximum moved-process count among services, and
source-to-destination machine move cost. Full recomputation uses Python integers, avoiding
overflow from the official 32-bit input values. This implementation is the correctness oracle
for future incremental calculations.

## Explicit formulation

Let `x[p,m]` be binary, `o[p]` the original machine, `a[p,r]` the resource demand,
`C[m,r]` the hard capacity and `SC[m,r]` the safety capacity. Each process belongs to service
`s[p]`; machines have location `L[m]` and neighborhood `N[m]`.

Unique assignment and usage:

\[
\sum_m x_{pm}=1,\qquad U_{mr}=\sum_p a_{pr}x_{pm},\qquad U_{mr}\le C_{mr}.
\]

For a transient resource, original occupancy is unavoidable and destination occupancy is added
only for processes whose original machine differs from that destination:

\[
T_{mr}=\sum_{p:o(p)=m}a_{pr}+\sum_{p:o(p)\ne m}a_{pr}x_{pm}\le C_{mr}.
\]

Conflict: `sum(x[p,m] for p in service s) <= 1`. Define binary presence `y[s,l]` and
`z[s,n]` as the maximum of the corresponding assignment variables at location `l` and neighborhood
`n`. Then spread is `sum_l y[s,l] >= spreadMin[s]`; each directed dependency `s -> d` requires
`z[s,n] <= z[d,n]` for every neighborhood. Presence must be equivalent to occupancy, not merely
an unconstrained indicator that can be set to one.

With `[v]+ = max(0,v)` and remaining capacity `A[m,r] = C[m,r] - U[m,r]`, minimize

\[
\begin{aligned}
f(x)={}&\sum_{m,r}w_r[U_{mr}-SC_{mr}]_+\\
&+\sum_{m,b}w_b[t_b A_{m,r_1(b)}-A_{m,r_2(b)}]_+\\
&+w_P\sum_p PMC_p(1-x_{p,o(p)})\\
&+w_S\max_s\sum_{p:s(p)=s}(1-x_{p,o(p)})\\
&+w_M\sum_{p,m}MMC_{o(p),m}x_{pm}.
\end{aligned}
\]

The machine-move term includes the diagonal if input supplies a nonzero diagonal cost. The service
term is a maximum over service move counts, not their sum. Load and balance are computed from
final usage rather than transient usage.

## Restricted model and implementation correspondence

For a selected process set `P'`, fix all `p` outside `P'` at the incumbent assignment. Each selected
process receives a limited machine domain containing its incumbent. Fixed usage, service presence
and moved counts become constants. Transient constants still include original occupancy of removed
processes. Model all dependencies incident to changed services, including incoming dependencies
from fixed services; these can prevent removal of the final provider from a neighborhood.

Candidate domains use residual capacity/conflict screening and insertion cost ranking. They do not
guarantee inclusion of the unrestricted global optimum. An `optimal` CP-SAT status therefore means
optimal in this restricted neighborhood only. Auxiliary variables express positive parts and the
service maximum; the configured variable limit counts assignment binaries, not all auxiliaries.

The implementation uses integer coefficients and single-worker CP-SAT. Full Python-integer
validation and objective evaluation govern write-back. Cost minimization of positive-part lower
bounds is equivalent for the nonnegative weights accepted by the parser; a time-limited feasible
solution is still re-evaluated exactly before acceptance. All failed or non-improving calls leave
the incumbent untouched.

`gmrp/validator.py` implements feasibility, `gmrp/objective.py` implements the formula above,
`gmrp/state.py` implements relocate/swap deltas, and `exact/restricted_repair.py` builds the local
model. The toy exhaustive tests enumerate every assignment within each nonempty process subset.
