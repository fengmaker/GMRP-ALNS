# GMRP-ALNS 项目计划书与 AI 启动提示词

> 项目名称：GMRP-ALNS——面向云计算集群的多资源机器重分配与自适应大邻域搜索  
> 英文名称：GMRP-ALNS: Adaptive Large Neighborhood Search for Large-Scale Machine Reassignment  
> 文档用途：项目立项、开发路线、实验协议、开源合规，以及新 Codex 项目的独立启动提示词  
> 文档版本：v1.0  
> 日期：2026-09-15

---

## 1. 项目定位

本项目以 Google 提出的 ROADEF/EURO Challenge 2012 Machine Reassignment Problem（机器重分配问题，以下简称 GMRP）为主要研究对象，实现一个可复现、可验证、可扩展的大规模组合优化求解器。

系统接收机器、资源、服务、进程、服务依赖、初始分配和迁移成本等数据，在满足全部硬约束的条件下重新分配进程，降低资源负载、资源失衡和迁移成本。

项目采用双轨结构：

```text
Track A：经典 Generalized Assignment Problem（GAP）
目的：验证整数规划、构造算法、局部搜索和 ALNS 的基本正确性

Track B：Google Machine Reassignment Problem（GMRP）
目的：处理多资源、初始解、服务冲突、分散部署、依赖和迁移成本等工业约束
```

完整能力证据链为：

```text
工业问题定义 → 数据解析 → 独立验证器 → 数学模型 → 可行基线
             → 增量评估 → 局部搜索 → ALNS/Matheuristic
             → 公开实例实验 → 消融分析 → 工程接口与技术报告
```

### 1.1 核心目标

1. 实现 OR-Library 经典 GAP 实例解析、数学模型、精确求解基线和启发式算法。
2. 实现 ROADEF/EURO 2012 GMRP 官方格式的模型文件、初始解和输出解解析器。
3. 独立实现 GMRP 可行性检查器和目标值计算器，并与官方 checker 交叉验证。
4. 实现支持 `relocate`、`swap`、`chain move` 的增量求值引擎。
5. 实现可行域局部搜索和允许暂时违反部分约束的罚函数搜索。
6. 实现自适应大邻域搜索（ALNS），包含多种移除、修复、接受和重启策略。
7. 实现至少一种 Matheuristic：Restricted MIP/CP-SAT Repair 或局部精确搜索。
8. 在公开 A/B 实例上完成固定时间、固定种子、多次重复的可复现实验。
9. 最终产出公开 GitHub 仓库、技术报告、结果表、收敛图和简历可用的真实量化结论。

### 1.2 非目标

第一版明确不做以下内容：

- 不复刻竞赛冠军程序或逐行翻译第三方代码。
- 不从一开始实现 Branch-and-Price、完整 Branch-and-Cut 或分布式求解器。
- 不把调用 Gurobi/OR-Tools 后输出一个解当作项目完成。
- 不同时实现十余种元启发式算法，只做有对照和消融的核心方法。
- 不在核心约束和增量求值尚未验证前引入强化学习。
- 不优先开发复杂前端、数据库、微服务或云端部署。
- 不声称超过竞赛冠军或 SOTA，除非遵守同一实例、硬件、时限和评分协议。
- 不伪造优化比例、最优 gap、运行时间或业务部署经历。

---

## 2. GAP、GMRP 与调度问题的关系

### 2.1 经典广义指派问题 GAP

令任务集合为 \(J\)，资源或代理集合为 \(I\)。任务 \(j\) 分配给代理 \(i\) 时产生成本 \(c_{ij}\)，消耗资源 \(a_{ij}\)，代理容量为 \(b_i\)。

决策变量：

\[
x_{ij}=\begin{cases}
1,&\text{任务 }j\text{ 分配给代理 }i\\
0,&\text{否则}
\end{cases}
\]

标准最小化模型：

\[
\min \sum_{i\in I}\sum_{j\in J}c_{ij}x_{ij}
\]

\[
\sum_{i\in I}x_{ij}=1,\quad \forall j\in J
\]

\[
\sum_{j\in J}a_{ij}x_{ij}\le b_i,\quad \forall i\in I
\]

\[
x_{ij}\in\{0,1\}
\]

GAP 解决“任务分给哪个资源”，通常没有开始时间、完成时间和执行顺序。

### 2.2 GMRP 是工业级广义指派扩展

GMRP 的核心变量仍然是“进程分配到哪台机器”，但相比 GAP 增加：

- 多维资源容量；
- 一个已知的初始可行分配；
- 迁移期间的瞬时资源占用；
- 同一服务进程的机器冲突约束；
- 服务跨位置分散部署约束；
- 服务之间的邻域依赖约束；
- 机器安全容量、资源平衡和多类迁移成本。

官方定义明确说明该问题没有时间维度，并假设迁移同时发生。因此它属于复杂指派/重分配问题，而不是严格意义上的调度问题。

### 2.3 与调度问题的区别

调度问题除资源分配外，还需要确定：

- 任务何时开始和完成；
- 同一机器上的任务执行顺序；
- 工序优先关系；
- 释放时间、截止时间和延期；
- 换型、抢占、机器维护等时间约束。

若未来将本项目扩展为“进程在线到达、具有运行时间、迁移需要持续时间、机器上的任务不可重叠”，问题就从重分配进入了动态调度或指派—调度联合优化范畴。该扩展不属于 v1.0 范围。

---

## 3. GMRP 正式问题定义

### 3.1 集合与参数

- \(M\)：机器集合。
- \(P\)：进程集合。
- \(R\)：资源集合，例如 CPU、RAM、DISK。
- \(TR\subseteq R\)：具有瞬时占用特性的资源集合。
- \(S\)：服务集合，每个进程只属于一个服务。
- \(L\)：位置集合，每台机器属于一个位置。
- \(N\)：邻域集合，每台机器属于一个邻域。
- \(C_{mr}\)：机器 \(m\) 对资源 \(r\) 的最大容量。
- \(SC_{mr}\)：机器 \(m\) 对资源 \(r\) 的安全容量。
- \(R_{pr}\)：进程 \(p\) 对资源 \(r\) 的需求量。
- \(M_0(p)\)：进程 \(p\) 的初始机器。
- \(PMC_p\)：移动进程 \(p\) 的成本。
- \(MMC_{m_1m_2}\)：从机器 \(m_1\) 移到机器 \(m_2\) 的成本。
- \(spreadMin_s\)：服务 \(s\) 至少需要覆盖的位置数。
- \(Dep(s)\)：服务 \(s\) 依赖的服务集合。

### 3.2 决策变量

\[
x_{pm}=1
\]

表示进程 \(p\) 在新方案中被分配到机器 \(m\)。每个进程必须且只能分配一次。

### 3.3 硬约束

#### 唯一分配

\[
\sum_{m\in M}x_{pm}=1,\quad \forall p\in P
\]

#### 多资源容量

\[
\sum_{p\in P}R_{pr}x_{pm}\le C_{mr},
\quad \forall m\in M,r\in R
\]

#### 服务冲突

属于同一服务的两个进程不能在同一机器上。

#### 服务分散部署

服务 \(s\) 必须部署在至少 \(spreadMin_s\) 个不同位置上。

#### 服务依赖

若服务 \(s_a\) 依赖 \(s_b\)，则部署了 \(s_a\) 的每个邻域中必须至少部署一个 \(s_b\) 进程。

#### 瞬时资源

对于 \(r\in TR\)，进程迁移时可能在原机器和目标机器同时占用该资源。验证器必须严格按照官方定义计算，不能只检查新分配的容量。

### 3.4 目标函数

官方目标由以下部分加权组成：

```text
total_cost
  = weighted_load_cost
  + weighted_balance_cost
  + process_move_cost
  + service_move_cost
  + machine_move_cost
```

- `load_cost`：超过安全容量但未超过最大容量的部分。
- `balance_cost`：资源之间剩余容量比例的不平衡成本。
- `process_move_cost`：被移动进程的个体成本。
- `service_move_cost`：单个服务中被移动进程数的最大值。
- `machine_move_cost`：原机器到目标机器的迁移成本。

所有目标分量都需要提供：

1. 全量计算函数；
2. 移动前后的增量变化函数；
3. 独立单元测试；
4. 与官方 checker 的一致性验证。

---

## 4. 研究问题与计划贡献

### 4.1 主研究问题

在具有多资源、服务冲突、分散部署和依赖约束的大规模机器重分配问题中，如何在固定时间内快速构造高质量可行解，并通过增量评估和自适应邻域选择持续改进解质量？

### 4.2 计划贡献

#### 贡献 A：统一的双轨实验框架

用同一套 CLI、配置、随机数控制和结果格式求解标准 GAP 与 GMRP，展示算法从基础指派到工业复杂约束的演进。

#### 贡献 B：约束感知的增量评估

对单进程移动、双进程交换和链式移动，只更新受影响机器、服务、位置和邻域的数据，避免每次候选评估都重新扫描全部进程。

#### 贡献 C：违反引导的大邻域选择

根据资源紧张度、负载成本、服务集中程度、依赖关系和迁移收益选择待移除进程，使搜索集中在最可能产生收益的区域。

#### 贡献 D：混合修复策略

普通迭代使用贪心或 Regret Repair；周期性选择一个小规模邻域交给 CP-SAT/HiGHS 精确修复，形成 ALNS 与数学规划结合的 Matheuristic。

### 4.3 可验证假设

- H1：增量评估相较全量重算能显著提高每秒候选移动评估数，且目标值完全一致。
- H2：约束/成本引导的 destroy 算子优于纯随机 destroy。
- H3：自适应算子权重优于固定均匀选择。
- H4：Restricted MIP Repair 能在相同总时限内改善 ALNS 最终目标值。
- H5：方法在 B 组大实例上仍能始终保持可行并稳定改善初始解。

---

## 5. 算法范围与成果所有权

### 5.1 必须独立实现的模块

以下模块是本项目的核心能力证明：

1. GAP 和 GMRP 数据模型及解析器。
2. 全量可行性检查器和全量目标函数计算器。
3. 解状态及机器、服务、位置、邻域的缓存结构。
4. `relocate`、`swap`、`chain move` 的合法性与增量目标值计算。
5. 至少两种 GAP 构造算法：cost greedy 与 regret greedy。
6. GMRP 初始解读取与保持可行的邻域搜索。
7. ALNS 主循环、算子评分、接受准则和终止准则。
8. 至少四种 destroy 和三种 repair 算子。
9. Restricted MIP/CP-SAT Repair 的邻域构造和结果回写。
10. 实验运行器、结果聚合器、绘图和报告生成。
11. 独立测试，包括增量值与全量值一致性的性质测试。

“独立实现”不要求所有代码都完全脱离第三方库。允许调用 NumPy、OR-Tools、HiGHS 等通用库，但问题状态、邻域逻辑、增量计算、实验协议和验证器必须由本项目实现并能够解释。

### 5.2 允许作为外部参考的资源

| 资源 | 用途 | 使用要求 |
|---|---|---|
| ROADEF/EURO 2012 官方题目与实例 | 主问题、数据和官方评分定义 | 固定下载地址，记录校验值和引用 |
| 官方 solution checker | 独立交叉验证 | 作为外部进程运行，不修改其逻辑冒充自研 |
| OR-Library GAP | 标准 GAP 测试 | 数据来源、实例方向和参考值写清楚 |
| J25 ROADEF2012 | VLSN/CP 邻域设计参考 | MIT；标注来源，不逐行翻译 |
| J19 ROADEF2012 | Local IP、装箱启发式参考 | LGPL-3.0；若复制/链接代码需遵守许可证 |
| N-Wouda/ALNS | ALNS 接口设计和接受准则参考 | 可选择调用或自研主循环，但必须说明 |
| Timefold Machine Reassignment | 约束解释与规模核对 | 文档参考，不作为结果基线 |

### 5.3 可选后期扩展

- 拉格朗日松弛下界。
- 基于 bandit 的智能算子选择。
- 基于 LightGBM 的候选移动收益预测。
- C++/Rust 增量评估核心及 Python 绑定。
- 并行候选评估和多起点搜索。
- 使用 Alibaba Cluster Trace 构造时间切片重分配实例。
- 加入在线到达和迁移持续时间，扩展为动态调度问题。

这些扩展不能阻塞 v1.0 完成。

---

## 6. 数据与开源资源

### 6.1 官方竞赛资源

- 项目主页：<https://roadef.org/challenge/2012/en/>
- 问题定义：<https://roadef.org/challenge/2012/files/problem_definition_v1_1.pdf>
- 公开实例与官方 checker：<https://roadef.org/challenge/2012/en/instances.php>
- 提交格式、时限和评分：<https://roadef.org/challenge/2012/en/reponse.php>

公开实例因保密原因由生成器产生，但约束结构面向真实集群资源重分配。A 组用于开发和回归，B 组用于大规模性能实验。

### 6.2 经典 GAP 资源

- OR-Library GAP：<https://people.brunel.ac.uk/~mastjjb/jeb/orlib/gapinfo.html>
- Google OR-Tools Assignment with Task Sizes：<https://developers.google.com/optimization/assignment/assignment_cp>
- GeneralizedAssignmentSolver：<https://github.com/fontanf/generalizedassignmentsolver>

OR-Library 同时包含最大化和最小化实例。解析器必须记录实例方向，不能在不说明的情况下通过符号变化混用参考最优值。

### 6.3 竞赛代码参考

- J25，Constraint-Based Very Large-Scale Neighborhood Search：  
  <https://github.com/fbrandt/ROADEF2012-J25>
- J19，ROADEF 2012 Final Submission：  
  <https://github.com/TeamJ19ROADEF2012/ROADEF2012-J19>
- Timefold Machine Reassignment 文档：  
  <https://docs.timefold.ai/timefold-solver/0.8.x/use-cases-and-examples/machine-reassignment/machine-reassignment>

### 6.4 真实轨迹扩展

- Alibaba Cluster Trace Program：<https://github.com/alibaba/clusterdata>

真实轨迹不直接等于 GMRP 实例。若后期使用，需要单独定义从机器和任务轨迹到容量、需求、初始分配、迁移成本的转换规则，并做敏感性分析。不得把人工定义的成本称为企业真实成本。

### 6.5 数据管理原则

1. 优先提供下载脚本，不盲目把全部外部数据提交到仓库。
2. 下载脚本记录 URL、日期、文件哈希和来源。
3. `data/raw/` 默认加入 `.gitignore`；小型许可明确的数据可单独处理。
4. 测试使用自建 toy instances，保证仓库在无外部数据时也能运行单元测试。
5. 不修改官方实例后仍沿用原实例名和参考结果。

---

## 7. 技术架构

### 7.1 技术选择

- Python 3.11+：主开发语言。
- NumPy：紧凑数组、资源使用缓存和增量计算。
- SciPy/Pandas：实验整理和统计分析。
- OR-Tools CP-SAT：小实例精确求解和 Restricted Repair。
- HiGHS/highspy：MIP 或 LP 基线，可作为 OR-Tools 的替代。
- Matplotlib/Plotly：收敛图、资源利用图、消融图。
- Typer 或 argparse：命令行接口。
- Pydantic/dataclass：配置和数据对象。
- pytest：单元、性质、回归和端到端测试。
- Hypothesis：可选，用于增量计算的性质测试。
- Ruff：格式和静态检查。
- GitHub Actions：小实例测试和基础质量检查。

Gurobi 只能作为可选后端，项目默认路径必须在没有商业许可证时可运行。

### 7.2 建议仓库结构

```text
gmrp-alns-solver/
├── README.md
├── LICENSE
├── CITATION.cff
├── THIRD_PARTY.md
├── ROADMAP.md
├── CHANGELOG.md
├── pyproject.toml
├── configs/
│   ├── gap/
│   ├── gmrp/
│   └── experiments/
├── data/
│   ├── README.md
│   ├── download_orlib.py
│   ├── download_roadef.py
│   ├── raw/                  # 默认不提交
│   └── toy/                  # 自建小实例，随仓库提交
├── src/gmrp_alns/
│   ├── cli.py
│   ├── common/
│   │   ├── random.py
│   │   ├── timer.py
│   │   └── result.py
│   ├── gap/
│   │   ├── model.py
│   │   ├── parser.py
│   │   ├── checker.py
│   │   ├── exact.py
│   │   └── heuristics.py
│   ├── gmrp/
│   │   ├── model.py
│   │   ├── parser.py
│   │   ├── solution.py
│   │   ├── validator.py
│   │   ├── objective.py
│   │   ├── state.py
│   │   └── delta.py
│   ├── search/
│   │   ├── moves.py
│   │   ├── local_search.py
│   │   ├── acceptance.py
│   │   ├── operator_selection.py
│   │   ├── stopping.py
│   │   └── alns.py
│   ├── operators/
│   │   ├── destroy/
│   │   └── repair/
│   ├── exact/
│   │   ├── gmrp_cpsat.py
│   │   └── restricted_repair.py
│   ├── experiments/
│   │   ├── runner.py
│   │   ├── aggregate.py
│   │   └── plots.py
│   └── reporting/
│       └── report.py
├── tests/
│   ├── unit/
│   ├── property/
│   ├── integration/
│   └── regression/
├── scripts/
│   ├── run_a_set.py
│   ├── run_b_set.py
│   └── verify_with_official_checker.py
├── results/
│   └── README.md
├── notebooks/
│   └── analysis.ipynb
└── docs/
    ├── mathematical_model.md
    ├── algorithm.md
    ├── experiment_protocol.md
    └── reproducibility.md
```

### 7.3 核心数据结构

实现时优先使用整数索引和紧凑数组：

```text
Instance
  machine_capacity[m, r]
  machine_safety_capacity[m, r]
  machine_location[m]
  machine_neighborhood[m]
  machine_move_cost[m_from, m_to]
  process_requirement[p, r]
  process_service[p]
  process_move_cost[p]
  service_spread_min[s]
  service_dependencies[s]
  original_machine[p]

SolutionState
  machine_of_process[p]
  usage[m, r]
  transient_usage[m, r]
  service_machine_count[s, m]
  service_location_count[s, l]
  service_neighborhood_count[s, n]
  moved_count_by_service[s]
  objective_components
```

避免在候选移动的内层循环频繁创建 Python 对象或复制完整解。先保证正确，再使用 NumPy、Numba、C++ 或 Rust 做性能扩展。

---

## 8. 算法设计

### 8.1 基线算法

必须保留以下基线：

1. `initial_assignment`：官方给出的原始可行解。
2. `first_improvement_relocate`：枚举或采样可行单点移动。
3. `best_improvement_relocate`：在受限候选集中选最优移动。
4. `relocate_swap_vnd`：先 relocate，局部最优后切换 swap。
5. `random_destroy_greedy_repair`：不带自适应权重的基础 LNS。
6. `adaptive_alns`：计划提出的主要方法。
7. `adaptive_alns_restricted_mip`：高级混合方法。

### 8.2 邻域移动

#### Relocate

将一个进程从当前机器移动到另一台机器。

候选目标机器通过以下方式裁剪：

- 资源容量预筛；
- 服务冲突预筛；
- 依赖和 spread 风险预筛；
- 机器相似度或资源互补度排序；
- 只保留 Top-K 候选。

#### Swap

交换两个进程的机器。适合单个 relocate 因容量受阻，但交换后可行的情况。

#### Chain Move

尝试长度为 2～4 的移动链，用一个进程的迁出为另一个进程创造容量。第一版限制链长和分支数，避免组合爆炸。

#### Service Neighborhood

选择同一服务、依赖相连服务或同一拥挤邻域内的进程联合优化。

### 8.3 Destroy 算子

至少实现：

- `random_removal`：随机移除进程。
- `high_load_cost_removal`：优先移除对安全容量超额贡献大的进程。
- `resource_critical_removal`：聚焦最紧张的机器—资源组合。
- `related_service_removal`：移除同一服务或依赖相连的服务进程。
- `high_move_gain_removal`：基于预计迁移收益选择进程。
- `machine_cluster_removal`：选择若干机器及其进程形成局部子问题。

### 8.4 Repair 算子

至少实现：

- `greedy_feasible_repair`：每次插入增量成本最低的可行位置。
- `regret_k_repair`：依据最佳和次佳插入成本差优先修复。
- `penalty_repair`：允许暂时违反部分软化约束，并动态调整罚系数。
- `restricted_cpsat_repair`：固定未移除进程，只精确优化当前大邻域。

硬约束是否允许暂时违反需要明确区分：

- `strict_feasible` 模式始终保持官方可行性。
- `penalty_search` 模式只允许配置中明确软化的约束暂时违反。
- 返回最终解前必须通过独立 validator；不通过则回退到历史最佳可行解。

### 8.5 接受准则

第一版实现：

- Hill Climbing；
- Simulated Annealing；
- Record-to-Record Travel 或 Late Acceptance 二选一。

ALNS 默认使用模拟退火，温度根据初始解成本和目标接受概率自动拟合。所有随机行为统一使用一个显式 seed。

### 8.6 自适应算子选择

每轮根据算子结果给予分数：

- 产生新的全局最优可行解；
- 改善当前解；
- 被接受但未改善；
- 被拒绝或修复失败。

采用分段反应权重更新：

\[
w_k\leftarrow(1-\rho)w_k+\rho\frac{score_k}{use_k}
\]

需要记录每个算子的调用次数、成功率、平均增益和耗时，最终进行算子消融。

### 8.7 Restricted MIP/CP-SAT Repair

流程：

1. destroy 算子选出一小部分进程 \(P'\)。
2. 固定 \(P\setminus P'\) 的分配。
3. 选取与 \(P'\) 相关的候选机器集合 \(M'\)。
4. 对 \(P'\times M'\) 建立局部精确模型。
5. 设置 0.1～2 秒局部时限。
6. 若得到可行改进则回写，否则恢复原状态。

必须限制变量数量并记录每次局部求解的成功率、耗时和贡献，避免精确求解器吞掉全部总时限。

---

## 9. 增量评估与正确性

### 9.1 为什么它是核心模块

B 组实例最多有 50,000 个进程。若每个候选移动都重新计算全部机器、服务和依赖，局部搜索无法获得足够的迭代速度。

增量评估只更新：

- 原机器和目标机器的资源使用；
- 被移动进程所属服务的机器、位置、邻域计数；
- 与该服务相连的依赖状态；
- 受影响的 load、balance 和 move cost；
- service move cost 的最大值维护结构。

### 9.2 必须满足的不变量

- 每个进程恰好属于一台机器。
- 缓存使用量等于按当前分配全量重算结果。
- 所有服务计数非负且总数正确。
- 应用 move 后的增量成本等于全量成本差。
- undo move 后状态逐项恢复。
- 相同实例、配置和 seed 输出完全一致。

### 9.3 验证策略

1. 手写 3～10 个进程的 toy instances，逐个覆盖每种约束。
2. 对 toy instances 使用穷举求得最优解，验证精确模型和目标函数。
3. 随机生成合法解和移动，比较 `delta_cost` 与全量重算。
4. 连续随机执行 move/undo，比较全部缓存和原始状态。
5. 对官方实例输出解，同时通过自研 validator 和官方 checker。
6. 将发现过的 bug 固化为回归测试。

---

## 10. 实验协议

### 10.1 实例集合

#### Track A：GAP

- OR-Library `gap1`～`gap12`。
- OR-Library `gapa`～`gapd`。
- 开发阶段选取小规模子集，完整报告运行全量公开实例。

#### Track B：GMRP

- A1/A2：功能验证、参数调试和小规模消融。
- B：正式的大规模性能与稳健性实验。

### 10.2 时间档

建议统一报告：

- 1 秒：响应速度。
- 10 秒：快速求解。
- 60 秒：工程常用时间档。
- 300 秒：对齐原竞赛最大时限。

开发和 CI 只运行 toy 与小实例；完整 B 组 300 秒实验由单独脚本执行，不进入普通 CI。

### 10.3 随机种子

- 调试固定 `seed=42`。
- 正式随机算法至少运行 5 个种子。
- 记录均值、标准差、最好值和最差值。
- 若计算预算允许，重点配置运行 10 个种子并报告 95% 置信区间。

### 10.4 指标

核心指标：

- 官方 `total_cost`。
- 相对初始解改善率：

\[
improvement=\frac{f_{initial}-f_{solver}}{\max(1,|f_{initial}|)}\times100\%
\]

- 相对已知最好解 gap（仅在参考值来源明确时报告）。
- 可行解率。
- Time to Best。
- 每秒候选移动评估数。
- 峰值内存。
- 被移动进程数量。
- 各目标分量的变化。
- 各算子使用次数、成功率、贡献和耗时。

### 10.5 基线比较

| 编号 | 方法 | 目的 |
|---|---|---|
| B0 | 初始分配 | 改善起点 |
| B1 | Relocate First Improvement | 最小自研局部搜索基线 |
| B2 | Relocate + Swap VND | 多邻域基线 |
| B3 | Random LNS + Greedy Repair | 非自适应 LNS 基线 |
| B4 | ALNS | 核心方法 |
| B5 | ALNS + Restricted Repair | 混合方法 |

可选地运行一到两个公开程序作为外部参考，但必须使用独立可执行程序、固定 commit 和清晰适配器，不混入自研代码统计。

### 10.6 消融实验

- 去掉增量计算，比较正确性与速度。
- random destroy 对比成本/约束引导 destroy。
- 固定算子概率对比自适应权重。
- Hill Climbing 对比 Simulated Annealing。
- 无 restart 对比 restart。
- Greedy Repair 对比 Regret Repair。
- ALNS 对比 ALNS + Restricted Repair。
- 不同 destroy size 和局部精确时限。

### 10.7 公平性要求

- 同一实例、同一总时限、同一硬件线程限制。
- 计时必须包含主要算法过程；预处理是否计时需要明确。
- 不用不同时间预算的最好结果进行不加说明的横向比较。
- 调参实例与最终测试实例尽量分离。
- 所有失败、超时和不可行结果都必须保留，不能只汇报成功案例。

---

## 11. 分阶段开发路线

### M0：立项与仓库初始化

任务：

- 创建仓库结构、`pyproject.toml`、README 骨架和许可证。
- 配置 pytest、Ruff、类型检查和 GitHub Actions。
- 将本计划书复制为 `docs/project_plan.md`。
- 建立 `THIRD_PARTY.md` 和数据来源清单。

验收：

- 全新环境可安装。
- `pytest` 和 `ruff check` 可运行。
- README 明确项目范围和未完成状态，不提前写虚假结果。

### M1：GMRP 解析器、全量目标函数和 Validator

任务：

- 实现官方模型、初始解和输出解解析。
- 实现五类硬约束检查。
- 实现各目标分量及总目标值。
- 创建覆盖全部约束的 toy instances。
- 接入官方 checker 进行交叉验证。

验收：

- 官方初始解全部被判定可行。
- 自研目标值与官方 checker 一致。
- 非法解能输出机器可读且可定位的错误原因。
- 单元测试覆盖全部约束与目标分量。

### M2：经典 GAP Track

任务：

- 实现 OR-Library 解析器。
- 实现 CP-SAT/HiGHS 精确模型。
- 实现 cost greedy、regret greedy、repair。
- 实现 relocate 和 swap 局部搜索。
- 对小实例与参考最优值比较。

验收：

- 小实例精确求解结果与参考值一致。
- 启发式解始终可行。
- CLI 可以统一运行单实例并输出 JSON 结果。

### M3：GMRP 状态缓存与增量邻域

任务：

- 实现 `SolutionState` 缓存。
- 实现 relocate 的检查、增量成本、apply 和 undo。
- 实现 swap。
- 增加候选机器预筛和 Top-K 列表。
- 建立全量与增量对拍测试。

验收：

- 至少 10,000 次随机合法移动中，增量值与全量值一致。
- move/undo 后所有数组和目标值完全恢复。
- 在 A 组实例上明显提高候选评估速度。

### M4：局部搜索与基础 LNS

任务：

- 实现 First/Best Improvement。
- 实现 Relocate + Swap VND。
- 实现 Random Removal + Greedy/Regret Repair。
- 实现统一 time limit 和 seed 控制。
- 记录收敛轨迹和 Time to Best。

验收：

- 所有最终解通过官方 checker。
- 在多数 A 组实例上改善初始解。
- 同一 seed 的结果可复现。

### M5：Adaptive ALNS

任务：

- 实现至少四种 destroy 和三种 repair。
- 实现模拟退火、算子评分、权重更新和 restart。
- 实现历史最佳可行解保护。
- 输出算子统计和目标分量变化。

验收：

- ALNS 相较 Random LNS 在预先指定的开发集上有稳定改善。
- 算子权重和调用统计可追溯。
- A/B 实例均无不可行输出。

### M6：Restricted MIP/CP-SAT Repair

任务：

- 构造进程—候选机器局部子问题。
- 设置局部求解时限和变量上限。
- 安全回写局部解并验证。
- 比较启用与关闭局部精确修复的效果。

验收：

- 局部修复失败不会破坏当前解。
- 局部精确求解耗时受配置严格控制。
- 完成对应消融实验。

### M7：完整实验与文档

任务：

- 运行预注册的 A/B 实验矩阵。
- 聚合多 seed 结果。
- 生成结果表、收敛图、性能剖析和消融图。
- 编写数学模型、算法、实验协议和复现说明。
- 记录硬件、依赖版本、commit 和配置文件。

验收：

- 一条命令可重现实验子集。
- 结果表能追溯到原始 JSON/CSV。
- README 中的全部数字由脚本生成或可定位到结果文件。

### M8：GitHub 发布与简历材料

任务：

- 完成中英文 README 摘要。
- 准备架构图、流程图和 2～3 分钟演示视频。
- 发布 v1.0 tag 和 release notes。
- 根据真实结果生成简历表述和面试问答。

验收：

- 陌生用户能在 10 分钟内跑通 toy demo。
- 仓库没有绝对本地路径、大文件、密钥或无法解释的二进制。
- 第三方来源和许可证记录完整。

---

## 12. 建议时间表

按每周约 15～20 小时规划：

| 周次 | 重点 | 对应里程碑 |
|---|---|---|
| 第1周 | 仓库、解析器、Validator、官方 checker | M0-M1 |
| 第2周 | GAP 精确模型、贪心、repair、基础实验 | M2 |
| 第3周 | GMRP 状态缓存、relocate、增量对拍 | M3 |
| 第4周 | swap、VND、候选集裁剪、性能剖析 | M3-M4 |
| 第5周 | Destroy/Repair、ALNS、模拟退火 | M5 |
| 第6周 | 自适应权重、restart、算子统计 | M5 |
| 第7周 | Restricted CP-SAT/MIP Repair | M6 |
| 第8周 | B 组实验、消融、报告与发布 | M7-M8 |

若时间不足，优先级为：

```text
Validator > 增量 Relocate > VND > 基础 ALNS > 完整实验
          > Restricted Repair > 学习型扩展 > 前端
```

没有 Restricted Repair 仍可以发布 v1.0；没有正确 Validator 和可复现实验则不能视为完成。

---

## 13. CLI 与输出协议

### 13.1 建议命令

```bash
# 下载数据
gmrp-alns data download --dataset roadef-a

# 验证一个解
gmrp-alns validate \
  --model data/raw/roadef/model_a1_1.txt \
  --initial data/raw/roadef/assignment_a1_1.txt \
  --solution results/example.sol

# 求解
gmrp-alns solve \
  --problem gmrp \
  --model data/raw/roadef/model_a1_1.txt \
  --initial data/raw/roadef/assignment_a1_1.txt \
  --algorithm alns \
  --time-limit 60 \
  --seed 42 \
  --output results/a1_1_seed42.sol

# 运行实验矩阵
gmrp-alns experiment run --config configs/experiments/a_set.yaml

# 聚合并绘图
gmrp-alns experiment report --input results/runs --output results/report
```

实际 CLI 名称可以调整，但参数语义必须稳定。

### 13.2 每次运行必须记录

```json
{
  "instance": "a1_1",
  "algorithm": "alns",
  "seed": 42,
  "time_limit_seconds": 60,
  "feasible": true,
  "initial_cost": 0,
  "best_cost": 0,
  "time_to_best_seconds": 0.0,
  "iterations": 0,
  "candidate_evaluations": 0,
  "moved_processes": 0,
  "objective_components": {},
  "operator_stats": {},
  "wall_time_seconds": 0.0,
  "peak_memory_mb": 0.0,
  "git_commit": "",
  "config": {}
}
```

示例中的零值仅表示字段，不得作为真实结果提交。

---

## 14. 测试计划

### 14.1 单元测试

- 每个输入字段和边界值。
- 容量、冲突、spread、依赖、瞬时资源约束。
- load、balance、三类 move cost。
- relocate、swap、chain move。
- 算子选择与接受准则。

### 14.2 性质测试

- `full_cost(new_state) - full_cost(old_state) == delta(move)`。
- `undo(apply(state, move)) == state`。
- validator 判定可行时所有缓存约束违反量为零。
- 相同 seed 和时限控制模式下结果可复现。

### 14.3 集成测试

- 解析官方实例和初始解。
- 运行短时局部搜索。
- 写出解文件。
- 自研 validator 验证。
- 官方 checker 再验证。

### 14.4 回归测试

- 保存 toy 和少量官方小实例的已知成本。
- 每个被修复的 bug 都增加最小复现测试。
- 性能回归只设置宽松阈值，避免 CI 硬件波动导致误报。

---

## 15. 风险与应对

### 风险 1：复杂约束导致增量更新错误

应对：先实现全量 oracle，再实现增量版本；所有 move 都必须长期对拍。

### 风险 2：始终保持可行导致搜索受限

应对：先完成 strict feasible 版本，再增加受控罚函数搜索；始终保存历史最佳可行解。

### 风险 3：Python 在 B 组实例过慢

应对：使用数组化状态、候选裁剪和性能剖析；确认热点后再使用 Numba/C++/Rust，不做无依据重写。

### 风险 4：精确模型无法处理中大实例

应对：精确模型只用于 toy/A 组小实例和 Restricted Repair；大实例主方法为局部搜索/ALNS。

### 风险 5：算法很多但没有可信实验

应对：每增加一个算子必须同时增加测试、配置、日志和消融位置；无实验价值的算子不进入主分支。

### 风险 6：开源使用边界不清

应对：数据用下载脚本；第三方代码固定 commit 并登记许可证；若不确定是否可复制，只阅读论文和接口思想后独立实现。

### 风险 7：为了简历提前写结果

应对：README 使用 `TBD` 或明确标注计划值；简历中的百分比只能来自冻结实验协议和保存的原始结果。

---

## 16. Definition of Done

项目 v1.0 只有同时满足以下条件才算完成：

- [x] 官方 A/B 实例能够自动下载或按文档准备。
- [x] 官方模型和解文件能够正确解析。
- [x] 自研 validator 覆盖全部硬约束。
- [x] 自研目标值与官方 checker 一致。
- [x] GAP 小实例精确模型能复现参考值。
- [x] GMRP relocate 与 swap 支持增量成本、apply、undo。
- [x] 增量值经过大规模随机对拍。
- [x] 至少完成 VND、基础 LNS 和 Adaptive ALNS。
- [x] 所有最终输出都通过官方 checker。
- [x] 完成固定时限、固定种子、多次重复实验。
- [x] 完成至少四项消融实验。
- [x] README 中有问题、模型、算法、快速开始、结果和限制。
- [x] 一条命令能运行 toy demo 和小规模回归实验。
- [x] 仓库有测试、CI、许可证、第三方声明和引用信息。
- [x] 简历描述中的全部量化数字能够从仓库结果复现。

v1.0.0 的对应证据入口为 `README.md`、`README_zh.md`、`docs/architecture.md`、
`docs/m7_verification.md`、`docs/portfolio_zh.md`、`scripts/demo.py` 与 `results/m7/`。

---

## 17. 最终 README 建议结构

```text
1. 一句话项目定位
2. 为什么这个问题重要
3. GAP 到 GMRP 的关系
4. 官方问题与数据来源
5. 数学模型
6. 算法架构图
7. 快速开始
8. Validator 使用方法
9. Benchmark 协议
10. 主结果表
11. 收敛图与消融实验
12. 可复现性
13. 项目限制
14. Roadmap
15. 第三方资源、许可证和引用
```

README 首页不堆叠所有类图。优先展示：业务问题、算法结构、可复现命令、核心结果和一张高质量图。

---

## 18. 简历表述模板

只有项目完成并冻结实验后才能填写数字：

### 版本 A：偏运筹算法

> 独立开发面向云计算集群的多资源机器重分配求解器，建模容量、服务冲突、分散部署、依赖及瞬时资源约束；实现增量 relocate/swap/chain-move、违反引导 ALNS 与 Restricted CP-SAT Repair。在 ROADEF/EURO 2012 公开实例上，相较初始方案平均降低目标值 XX%，60 秒内最佳解平均 gap 为 XX%。

### 版本 B：偏算法工程

> 构建可复现的大规模组合优化框架，实现官方格式解析、独立 solution validator、增量目标评估和多 seed benchmark；在最高 XX 个进程、XX 台机器的实例上达到每秒 XX 次候选评估，增量评估相较全量重算加速 XX 倍，所有输出通过官方 checker。

### 面试时必须能回答

- 为什么该问题不是调度问题？
- GAP 与 GMRP 的数学关系是什么？
- 五类硬约束如何检查？
- 为什么原始分配是重要信息？
- relocate 的增量目标值涉及哪些缓存？
- spread 和 dependency 为什么会让局部移动变复杂？
- 如何确保暂时不可行搜索最终返回可行解？
- ALNS 为什么比固定邻域搜索更适合该问题？
- Restricted MIP Repair 的变量规模如何控制？
- 多 seed、时限和硬件不一致时如何公平比较？

---

## 19. 新 Codex 项目独立启动提示词

将下面整段复制到新的 Codex 项目中。新项目应保存本计划书，后续所有实现以本计划书为事实来源。

```text
我要从零实现一个可以公开到 GitHub 的运筹优化项目：

GMRP-ALNS——面向云计算集群的多资源机器重分配与自适应大邻域搜索。

主问题是 Google ROADEF/EURO Challenge 2012 Machine Reassignment Problem，
同时保留 OR-Library 经典 GAP 作为基础验证轨。

请先完整阅读项目中的《GMRP-ALNS_项目计划书与AI启动提示词.md》或
docs/project_plan.md，并严格按其中的范围、阶段、实验协议、测试要求和
开源规范执行。不要把外部仓库复制改名，不要虚构实验结果，不要在核心
算法正确之前做复杂前端或强化学习。

工作原则：

1. 先检查当前仓库、AGENTS.md、已有代码和未提交修改，不覆盖用户工作。
2. 按 M0、M1、M2……顺序推进，每次只完成一个可验证里程碑。
3. 第一优先级是官方格式解析器、全量目标函数和独立 Validator。
4. 所有增量算法都必须与全量计算对拍；所有最终解都必须通过 Validator。
5. 默认使用 Python 3.11+、pytest、Ruff、NumPy、OR-Tools/HiGHS。
6. Gurobi 只能作为可选后端，默认安装不能依赖商业许可证。
7. 所有随机算法必须显式接受 seed，所有求解器必须尊重 time limit。
8. 数据优先通过下载脚本获得，并记录 URL、日期、哈希和引用。
9. README 中没有实测支持的结果必须写 TBD，不得填写估计数字。
10. 每完成一个里程碑，运行测试并更新 ROADMAP/CHANGELOG，然后说明：
   - 修改了什么；
   - 如何验证；
   - 当前限制；
   - 下一里程碑。

现在开始执行 M0 和 M1：

- 初始化清晰的 Python 包和测试结构；
- 创建 toy instances；
- 实现 GMRP 官方模型文件与分配文件解析；
- 实现全量硬约束 Validator；
- 实现完整目标函数及目标分量；
- 为每类约束和成本写单元测试；
- 预留调用官方 checker 的适配器；
- 提供最小 CLI：parse、validate、score；
- 运行全部测试并报告结果。

不要提前实现 ALNS。M1 验收通过后，再按照计划书进入下一阶段。
```

---

## 20. 第一阶段完成后的续接提示词

当 M0-M1 完成后，可在同一项目中发送：

```text
继续执行项目计划书的 M2：经典 GAP Track。

先检查 M0-M1 的代码、测试和当前 git diff，确认 Validator 与目标函数仍然
通过测试。然后实现 OR-Library GAP 解析器、CP-SAT 或 HiGHS 精确模型、
cost greedy、regret greedy、repair、relocate 和 swap。使用自建 toy instances
和有参考最优值的小型 OR-Library 实例验证。保持统一 CLI、结果 JSON、seed
和 time limit 协议。不要开始 GMRP ALNS，直到 M2 验收项全部通过。
```

当 M2 完成后，可发送：

```text
继续执行项目计划书的 M3-M4：GMRP 增量状态与局部搜索。

重点实现 SolutionState、relocate/swap 的合法性判断、delta、apply、undo 和
候选机器裁剪。全量 objective/validator 是正确性 oracle。建立随机移动对拍、
move/undo 性质测试和性能基准。完成后实现 First Improvement、VND 与基础
Random LNS。任何不一致都先修复，不得绕过断言或降低测试标准。
```

当 M3-M4 完成后，可发送：

```text
继续执行项目计划书的 M5-M6：Adaptive ALNS 与 Restricted Repair。

在已有且验证正确的增量状态上实现 destroy、repair、模拟退火、自适应权重、
restart 和历史最佳可行解保护。随后增加受变量规模和局部时限严格限制的
CP-SAT/HiGHS Repair。记录每个算子的调用、成功、增益和耗时，并完成对应
消融。所有输出必须再次通过全量 Validator 和官方 checker。
```

---

## 21. 最终决策记录

本项目选择 GMRP 而不是只做标准 GAP，原因如下：

1. 它由工业方提出，问题背景和约束结构更接近真实集群资源管理。
2. 官方公开问题定义、A/B 实例、初始解、输出格式和 checker，便于可信复现。
3. 规模达到 50,000 个进程，能够体现大规模启发式和增量算法能力。
4. 它仍以广义指派为核心，不会偏离项目的运筹优化主线。
5. 标准 GAP Track 可提供最优值验证，GMRP Track 可提供工业复杂度，两者互补。
6. ALNS、VND、动态罚函数和 Restricted Repair 与目标岗位常见的求解器开发能力高度相关。

项目成功的关键不是算法名称数量，而是：

```text
正确的 Validator
+ 正确且快速的增量状态
+ 有业务含义的邻域算子
+ 公平、完整、可复现的实验
```
