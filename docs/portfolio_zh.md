# 证据化简历表述与面试问答

本页只使用仓库中已经冻结、可定位的证据。投递时应按岗位选取 2～3 条，不要把全部数字堆进
一段，也不要省略“一秒请求预算”“单机测量”等边界。

## 简历表述

### 中文版本

- 独立实现 ROADEF 2012 Machine Reassignment Problem 求解与验证框架，覆盖 5 类硬约束、
  5 类官方成本、官方整数流解析和 JSON CLI；自研成本在 A1/A2 十个实例上逐一匹配官方
  checker。
- 设计 GMRP 增量 `SolutionState`，支持 relocate/swap 精确 delta、apply/undo 和候选裁剪；
  10,000 次 seeded 合法移动与全量 oracle 逐次一致，在 A1_2 本机微基准中候选评估吞吐为
  全量重算的 111.94 倍。
- 实现 VND、Random LNS、Adaptive ALNS 和有界 Restricted CP-SAT Repair，包含 5 种 destroy、
  3 种严格可行 repair、模拟退火、自适应权重、restart、单线程局部精确修复与失败安全回退。
- 构建可审计实验流水线：冻结源码/输入/checker/环境哈希，隔离串行 worker、断点续跑、记录
  实际耗时与峰值内存，并归档 JSONL/CSV/图表/校验和；660/660 个 M7 返回解通过官方 checker。
- 用冻结实验验证复杂度取舍：一秒请求预算下 Relocate/VND 平均改善 12.032%/12.008%，高于
  ALNS 的 9.126%；同时披露 208/660 次超 1.1 秒容差，未把负面结果包装成严格时限优势。

### English version

- Built an independent ROADEF 2012 Machine Reassignment solver and validation stack covering five
  hard-constraint families, five official cost terms, strict parsing, and a JSON CLI; matched the
  official checker on all ten A1/A2 initial objectives.
- Designed an incremental solution state with exact relocate/swap deltas, apply/undo, and candidate
  pruning; matched a full oracle over 10,000 seeded legal moves and measured 111.94x candidate
  evaluation throughput on a documented single-host A1_2 microbenchmark.
- Implemented VND, Random LNS, Adaptive ALNS, and bounded Restricted CP-SAT Repair with five destroy
  and three strict-feasible repair operators, simulated annealing, adaptive weights, restart, and
  failure-safe full-oracle handoff.
- Built an auditable experiment pipeline with frozen source/input/checker/environment hashes,
  isolated resumable workers, actual runtime/memory measurement, official checking, and a raw
  JSONL/CSV/figure/checksum archive; all 660 M7 returned assignments were official-valid.
- Quantified a negative short-budget result: Relocate/VND averaged 12.032%/12.008% improvement vs
  9.126% for ALNS, while retaining all 208/660 solver-call overruns rather than presenting them as
  strict one-second evidence.

## 数字到证据的映射

| 简历数字 | 证据文件 | 限制 |
|---|---|---|
| A1/A2 10/10 checker 一致 | `docs/m1_verification.md` | 初始 assignment 的交叉验证 |
| 10,000 move 对拍 | `docs/m2_m3_verification.md` | seeded legal moves |
| 111.94x | `docs/m2_m3_verification.md` | 单机 A1_2 增量评估微基准 |
| M6 135 次 CP-SAT 调用、83 次改善 | `docs/m6_verification.md` | 参与过开发调整，不是 M7 |
| M7 660/660 official-valid | `results/m7/records.jsonl` | returned assignments |
| 12.032%、12.008%、9.126%、8.994% | `docs/m7_verification.md` | 单机一秒请求预算 |
| 208/660 超容差 | `results/m7/summary.json` | 完整 solver call > 1.1 s |

## 面试问答

### 1. 为什么先实现 Validator 和完整 Objective，而不是直接写 ALNS？

增量缓存和复杂搜索很容易产生“速度正确、语义错误”的假象。完整实现更简单、独立，是所有
delta、repair 和最终输出的 oracle。项目用官方 checker 交叉验证它，再用它对拍增量路径。

### 2. GMRP 最容易实现错的约束是什么？

Transient resource。进程迁移时，它的 transient 需求同时占用原机器和目标机器；但 load 和
balance 目标仍按最终 assignment 的普通使用量计算。另一个常见错误是把 dependency 当成
machine 级，而官方语义是 neighborhood 级。

### 3. 如何证明增量 delta 没有漂移？

固定 seed 生成合法 relocate/swap，逐次比较增量总成本与完整 Objective、比较缓存 assignment
与完整 Validator，并在 undo 后比较完整快照。当前记录覆盖 10,000 次移动；每个新增邻域都
必须维持这条 oracle 路径。

### 4. Restricted Repair 如何保证失败不破坏当前解？

它在副本上固定邻域外进程，为邻域内变量保留 incumbent 候选，限制 candidate machine、变量
数、单次求解时间和 worker 数。unknown、infeasible、超时、无改善或全量 oracle 拒绝时返回
空结果；只有严格改善且复核通过的完整 assignment 才回写。

### 5. 为什么 ALNS 在 M7 中输给简单局部搜索？

一秒预算太短。ALNS 需要状态构建、20% relocate warm start、destroy/repair 调度、自适应更新
和最终 oracle；B3–B10 甚至没有严格及时的 ALNS/Restricted 配对。独立 cProfile 也显示状态
构建和全量验证占据显著时间。结论只适用于这台机器和这个短预算。

### 6. 为什么仍保留没有胜出的复杂算法？

它们验证了可扩展架构、精确邻域建模、安全回退和实验可观测性，也为更长预算提供可检验假设。
但发布结论必须由当前证据决定，所以 README 明确把“一秒档复杂度未回本”作为负面结果。

### 7. 实验怎样防止选择性报告？

运行前冻结实例、seed、方法、预算、held-out、顺序、源码/输入/checker/环境哈希。每条观察在
独立进程中运行；失败、missing、checker rejection 和 overrun 都保留。配对只使用相同实例、
seed 和预算，原始 JSONL 与校验和随报告提交。

### 8. 为什么不把 660 条都称为“一秒结果”？

算法截止是协作式的：初始化、一次在途操作和最终 oracle 可能越过 deadline。项目记录完整
solver call，并预注册 0.1 秒容差；208 条超出容差。返回结果仍可分析，但必须与严格及时的
敏感性统计分开。

### 9. 项目下一步最有价值的工程改进是什么？

先优化 B 实例的状态构建和重复全量计算，再运行预注册的 10/60/300 秒多机矩阵；之后才判断
ALNS 自适应与 Restricted Repair 是否在更长预算回本。不能先看结果再改 held-out 协议。

### 10. 如果只能展示一个设计决定，会选什么？

选择“增量引擎负责速度，全量 oracle 负责真值”。它把高性能搜索与正确性定义解耦，也让局部
搜索、ALNS、CP-SAT Repair、CLI 和实验 worker 都共享同一个可验证的输出边界。
