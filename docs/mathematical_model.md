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

