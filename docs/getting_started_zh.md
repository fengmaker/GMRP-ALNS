# GMRP-ALNS 问题输入输出与快速上手指南

本文面向第一次接触本仓库的读者，目标是回答五个问题：

1. 这个项目究竟在求解什么问题？
2. 一次 GMRP 或 GAP 运行需要哪些输入文件？
3. 求解器、验证器和命令行分别输出什么？
4. 如何在几分钟内把项目运行起来？
5. 应该按什么顺序阅读代码，哪些代码最核心？

当前仓库已完成 M0～M4：除了 GMRP 的官方格式解析、完整验证器、完整目标函数和增量
`relocate`/`swap` 状态，现在还提供 First/Best Improvement、Relocate + Swap VND、Random
Removal + Greedy/Regret Repair 和统一的 GMRP `solve` 命令。M5 的 Adaptive ALNS 尚未实现。

---

## 1. 先建立整体认识

### 1.1 主问题：GMRP

GMRP 是 ROADEF/EURO Challenge 2012 Machine Reassignment Problem。可以把它理解为：

> 已知每个进程原来在哪台机器上，现在要为每个进程选择一台最终机器；新方案必须满足
> 容量与服务约束，同时尽量减少资源压力、不平衡和迁移成本。

它不是传统调度问题。输出只决定“进程最终放在哪台机器”，不决定开始时间、完成时间或
机器上的执行顺序。

主要对象如下：

| 对象 | 含义 | 典型字段 |
|---|---|---|
| Resource | CPU、RAM、磁盘等资源维度 | 是否为 transient、负载成本权重 |
| Machine | 可承载进程的机器 | neighborhood、location、容量、安全容量、迁移成本 |
| Service | 一组有共同部署约束的进程 | 最小 location 数、依赖服务 |
| Process | 被分配的基本单元 | 所属 service、资源需求、进程移动成本 |
| BalanceCost | 两类资源之间的平衡惩罚 | 两个资源、目标比例、权重 |
| Assignment | 每个进程选择的机器 | `assignment[p] = m` |

### 1.2 基础验证轨：经典 GAP

仓库还包含一个独立的经典 Generalized Assignment Problem（GAP）轨道：把每个 job
分配给一个 agent，每种分配有成本和资源消耗，每个 agent 有容量限制。

GAP 的作用是用更小、更标准的问题验证以下基础能力：

- OR-Library 数据解析；
- CP-SAT 精确建模；
- cost greedy、regret greedy 和 repair；
- relocate、swap 局部改进；
- 统一的 seed、time limit 和 JSON 结果格式。

GAP 与 GMRP 都以“选择一个承载对象”为核心，但二者的文件格式和约束并不相同，不能把
GAP 文件直接交给 GMRP parser，反之亦然。

---

## 2. GMRP 的约束和目标函数

### 2.1 五类硬约束

候选 assignment 只有同时满足以下约束才是合法解：

| 约束 | 含义 | 代码中的全量检查位置 |
|---|---|---|
| Capacity | 每台机器每种资源的使用量不超过最大容量 | `gmrp/validator.py` |
| Conflict | 同一 service 的两个进程不能在同一机器 | `gmrp/validator.py` |
| Spread | service 至少覆盖指定数量的不同 location | `gmrp/validator.py` |
| Dependency | 含 service `s` 的每个 neighborhood 也必须含其依赖 service | `gmrp/validator.py` |
| Transient capacity | 迁移过程中，transient 资源在原机器和目标机器上同时占用 | `gmrp/validator.py` |

两个容易混淆的容量概念：

- `capacity` 是硬上限，超过后解不可行；
- `safety_capacity` 不是硬上限，超过它但未超过 `capacity` 时解仍可行，只会产生
  load cost。

Transient 资源也需要特别注意。若进程从机器 0 移到机器 2，它的 transient 资源在容量
检查时同时计入机器 0 和机器 2；若进程不移动，只计一次。

### 2.2 五类目标成本

对合法解，官方总成本由以下五部分组成：

```text
total_cost
  = weighted_load_cost
  + weighted_balance_cost
  + weighted_process_move_cost
  + weighted_service_move_cost
  + weighted_machine_move_cost
```

- `load_cost`：最终资源使用量超过机器安全容量的部分；
- `balance_cost`：机器上两类资源剩余容量比例偏离目标的惩罚；
- `process_move_cost`：所有已移动进程自身的移动成本之和；
- `service_move_cost`：各 service 的已移动进程数中的最大值，不是所有 service 之和；
- `machine_move_cost`：每个进程从原机器到最终机器的机器间迁移成本之和。

Transient 的“双端占用”用于硬约束检查；load 和 balance 目标使用最终 assignment 的普通
资源使用量。完整目标函数实现位于 `src/gmrp_alns/gmrp/objective.py`。

---

## 3. GMRP 的输入文件

一次完整的 GMRP 验证或计分需要三个文件：

| 参数角色 | 官方常见文件名 | 内容 |
|---|---|---|
| Model | `model_a1_1.txt` | 资源、机器、服务、进程、平衡项和权重 |
| Initial assignment | `assignment_a1_1.txt` | 每个进程的原始机器 |
| Candidate solution | 自己生成的 `.sol` 或 `.txt` | 每个进程的最终机器 |

Model 只描述问题本身，initial assignment 提供迁移的起点，candidate solution 是待验证和
计分的答案。原始 assignment 不能省略，因为 transient capacity 和三类迁移成本都依赖
“原机器 → 最终机器”的变化。

### 3.1 Model 文件的整数流格式

官方格式是一个以空白字符分隔的整数流。换行主要用于可读性，parser 实际按空白切分，
因此不能依赖“某个字段一定在某一行”。读取顺序如下：

```text
resource_count = R
for r in 0..R-1:
    transient[r]
    load_cost_weight[r]

machine_count = M
for m in 0..M-1:
    neighborhood[m]
    location[m]
    capacity[m, 0..R-1]
    safety_capacity[m, 0..R-1]
    machine_move_cost[m, 0..M-1]

service_count = S
for s in 0..S-1:
    spread_min[s]
    dependency_count[s]
    dependency_service_ids[s]

process_count = P
for p in 0..P-1:
    service_of_process[p]
    requirement[p, 0..R-1]
    process_move_cost[p]

balance_cost_count = B
for b in 0..B-1:
    first_resource[b]
    second_resource[b]
    target[b]
    weight[b]

process_move_cost_weight
service_move_cost_weight
machine_move_cost_weight
```

所有 resource、machine、service 和 process ID 都是从 0 开始的整数索引。Parser 会检查
数量、索引范围、非负字段、重复依赖、安全容量是否超过最大容量，以及是否有多余整数。

仓库中的最小示例是 `data/toy/model_toy.txt`，它包含：

- 2 种资源，其中资源 0 是 transient；
- 4 台机器；
- 2 个 service，其中 service 1 依赖 service 0；
- 3 个进程；
- 1 个 balance cost。

### 3.2 Initial assignment 文件

Assignment 文件没有数量头，也没有进程 ID。它只包含恰好 `P` 个机器编号：

```text
m_0 m_1 m_2 ... m_(P-1)
```

第 `p` 个整数就是进程 `p` 所在的机器，即：

```text
assignment[p] = machine_id
```

Toy 原始 assignment 是：

```text
0 3 0
```

含义是进程 0 在机器 0、进程 1 在机器 3、进程 2 在机器 0。

### 3.3 Candidate solution 文件

Candidate solution 与 initial assignment 使用完全相同的格式，但表示最终机器。Toy 候选
解是：

```text
0 2 1
```

这表示进程 0 不动，进程 1 从机器 3 移到机器 2，进程 2 从机器 0 移到机器 1。

输出官方解文件时必须只写这 `P` 个机器编号，不能把 JSON、成本或日志混入 `.sol` 文件。
`write_assignment()` 会生成正确的一行格式。

---

## 4. GMRP 的输出

项目中有三种不同意义的“输出”，应当区分。

### 4.1 官方 candidate solution

这是要提交给验证器或官方 checker 的答案文件，格式就是上一节的 `P` 个目标机器编号。
它是优化算法最核心的产物。

### 4.2 CLI JSON 诊断输出

当前 GMRP CLI 提供三个命令：

```text
parse      解析 model，输出实例规模
validate   检查 candidate 是否满足全部硬约束
score      验证 candidate，并输出完整目标成本分量
```

`parse` 的主要输出字段：

```json
{
  "model": "data/toy/model_toy.txt",
  "resources": 2,
  "machines": 4,
  "services": 2,
  "processes": 3,
  "neighborhoods": 2,
  "locations": 3
}
```

`validate` 的主要输出字段：

```json
{
  "feasible": true,
  "violation_count": 0,
  "violations": []
}
```

非法解会在 `violations` 中给出机器可读的约束类别和定位信息，例如 machine、resource、
service、actual 和 limit。

`score` 在 validation report 之外增加：

```json
{
  "objective": {
    "load_costs": [0, 40],
    "balance_costs": [160],
    "process_move_cost": 101,
    "service_move_cost": 1,
    "machine_move_cost": 3,
    "weighted_load_cost": 400,
    "weighted_balance_cost": 1600,
    "weighted_process_move_cost": 101,
    "weighted_service_move_cost": 10,
    "weighted_machine_move_cost": 300,
    "total_cost": 2411
  }
}
```

命令退出码：

| 退出码 | 含义 |
|---:|---|
| 0 | 输入合法，candidate 可行 |
| 1 | 输入格式合法，但 candidate 不可行 |
| 2 | 文件无法读取、格式错误、索引越界或其他输入错误 |

### 4.3 GMRP 求解输出

`solve` 从 initial assignment 开始搜索；`--output` 写出可直接交给官方 checker 的一行
assignment，同时标准输出给出 JSON。可选算法如下：

- `relocate-first`、`relocate-best`：只使用 relocate 邻域；
- `vnd-first`、`vnd-best`：在 relocate 局部最优后尝试 swap，成功后回到 relocate；
- `random-lns-greedy`、`random-lns-regret`：随机移除进程，再以对应策略有界修复。

JSON 包含算法、seed、time limit、迭代次数、候选评估次数、time to best、目标分量、
算子统计、收敛轨迹和最终 assignment。搜索只接受严格可行的改善解；返回前还会调用完整
validator 和 objective 复核。生成的批量运行记录应放在
`results/runs/`，聚合报告放在 `results/report/`；两者默认不提交，冻结实验结果后再按实验
协议处理。

M4 的一秒 A 组记录是工程验收，不是完整的 GMRP 解质量 benchmark；详见
`docs/m4_verification.md`。

---

## 5. 经典 GAP 的输入输出

### 5.1 OR-Library 输入格式

一个 OR-Library GAP 文件可以连续包含多个问题：

```text
problem_count = K
for each problem:
    agent_count = m
    job_count = n
    cost[0..m-1, 0..n-1]
    resource[0..m-1, 0..n-1]
    capacity[0..m-1]
```

需要特别注意：目标方向不在文件整数流中。官方 `gap1`～`gap12` 是最大化问题，
`gapa`～`gapd` 是最小化问题，因此 CLI 强制要求显式提供 `--sense minimize` 或
`--sense maximize`。

仓库中的 `data/toy/gap_toy.txt` 含 1 个问题、2 个 agent、4 个 job，是最小化问题，已知
最优值为 8。

### 5.2 GAP 求解输出

GAP `solve` 命令输出 JSON，关键字段包括：

- `algorithm`：`cp-sat`、cost greedy 或 regret greedy；
- `status` 和 `optimal`；
- `assignment`：第 `j` 个值是 job `j` 的 agent；
- `objective` / `best_cost`；
- `best_bound`；
- `seed`、`time_limit_seconds`、`wall_time_seconds`；
- `iterations` 和 `candidate_evaluations`；
- `reference_value` 和 `matches_reference`。

CLI 的 `--instance-index` 从 1 开始，便于对应 OR-Library 文件中的第几个问题；Python 内部
agent 和 job 索引仍从 0 开始。

---

## 6. 五分钟快速上手

以下命令以 Windows PowerShell 和仓库路径 `D:\GAP` 为例。使用 Python 模块入口可以避免
未激活虚拟环境时找不到 `gmrp-alns` 可执行文件。

### 6.1 创建环境并安装

如果 `.venv` 已存在，可以跳过第一条：

```powershell
cd D:\GAP
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### 6.2 运行质量检查

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
```

当前 M4 基线是 38 项测试通过；测试数量以后可能增加，因此应以命令是否全部通过为准，而不是
把固定数量写进自动化判断。

### 6.3 跑通 GMRP toy

```powershell
.\.venv\Scripts\python.exe -m gmrp_alns parse data/toy/model_toy.txt

.\.venv\Scripts\python.exe -m gmrp_alns validate `
  data/toy/model_toy.txt `
  data/toy/assignment_toy.txt `
  data/toy/solution_toy.txt

.\.venv\Scripts\python.exe -m gmrp_alns score `
  data/toy/model_toy.txt `
  data/toy/assignment_toy.txt `
  data/toy/solution_toy.txt
```

预期：validation 为 feasible，score 的 `total_cost` 为 `2411`。

再从 initial assignment 搜索并写出候选解：

```powershell
.\.venv\Scripts\python.exe -m gmrp_alns solve `
  data/toy/model_toy.txt `
  data/toy/assignment_toy.txt `
  --algorithm vnd-best `
  --time-limit 2 `
  --seed 42 `
  --output candidate.sol
```

预期：`best_cost` 为 `2411`，`candidate.sol` 内容为 `0 2 1`。需要跨机器稳定复现实验
路径时，同时固定 `--seed` 和 `--max-iterations`；单靠墙钟时限可能因机器速度产生不同的
截止迭代，耗时字段本身也不要求逐字节相同。

### 6.4 跑通 GAP toy

```powershell
.\.venv\Scripts\python.exe -m gmrp_alns gap parse `
  data/toy/gap_toy.txt --sense minimize

.\.venv\Scripts\python.exe -m gmrp_alns gap solve `
  data/toy/gap_toy.txt `
  --sense minimize `
  --algorithm exact `
  --reference-value 8 `
  --seed 42
```

预期：`feasible=true`、`optimal=true`、`best_cost=8`、`matches_reference=true`。

### 6.5 准备外部公开数据

外部实例默认下载到被 Git 忽略的 `data/raw/`，来源和哈希写入可提交的 manifest：

```powershell
.\.venv\Scripts\python.exe data/download_roadef.py a1
.\.venv\Scripts\python.exe data/download_roadef.py a2
.\.venv\Scripts\python.exe data/download_orlib.py gap1
```

不要直接把 `data/raw/` 中的第三方数据加入 Git。

---

## 7. 从文件到结果的完整数据流

### 7.1 当前 GMRP 验证/计分路径

```text
model file -----------------> parse_instance() -----> Instance
initial assignment file ----> parse_assignment() ---> original Assignment
candidate solution file ----> parse_assignment() ---> candidate Assignment
                                                       |
                           +---------------------------+------------------+
                           |                                              |
                        validate()                              evaluate_objective()
                           |                                              |
                   ValidationReport                              ObjectiveBreakdown
                           +---------------------------+------------------+
                                                       |
                                                    CLI JSON
```

### 7.2 当前 GMRP 求解路径

```text
Instance + original Assignment
              |
        SolutionState
              |
   relocate / swap candidate
              |
 feasibility + delta + apply/undo
              |
      best candidate Assignment
              |
 full validate() + evaluate_objective()     <- 最终正确性 oracle
              |
 write_assignment() + run JSON
              |
      official checker cross-check
```

重要设计原则是：增量状态负责速度，全量 validator 和 objective 负责正确性。不能为了让
增量实现“看起来通过”而削弱全量 oracle。

---

## 8. 推荐的代码阅读顺序

如果只想快速理解，不建议从 600 多行的 `state.py` 开始。下面顺序能逐层建立上下文。

### 第一层：先看数据长什么样

1. `data/toy/model_toy.txt`
2. `data/toy/assignment_toy.txt`
3. `data/toy/solution_toy.txt`
4. `src/gmrp_alns/gmrp/model.py`

读完应能回答：一个进程、机器、service 和 assignment 在内存里分别如何表示。

### 第二层：理解输入边界

5. `src/gmrp_alns/gmrp/parser.py`
6. `tests/unit/test_parser.py`

Parser 只负责把文件转换为领域对象并做结构检查，不负责判断 assignment 是否满足所有业务
约束。

### 第三层：理解“正确解”的定义

7. `src/gmrp_alns/gmrp/calculations.py`
8. `src/gmrp_alns/gmrp/validator.py`
9. `tests/unit/test_validator.py`
10. `src/gmrp_alns/gmrp/objective.py`
11. `tests/unit/test_objective.py`

这是最重要的一层。Validator 定义可行性，Objective 定义解质量，二者是后续所有算法的
正确性基准。

### 第四层：理解增量移动

12. `src/gmrp_alns/gmrp/state.py`
13. `tests/unit/test_state.py`
14. `scripts/benchmark_incremental.py`

阅读 `state.py` 时建议按以下方法顺序：

```text
SolutionState.__init__
make_relocate / make_swap
evaluate_move
_build_plan
_constraint_failure
_objective_delta
_apply_plan
undo_move
prefilter_machines / candidate_machines
assert_consistent
```

`_build_plan` 把一个或两个进程的同时变化汇总成受影响的机器、资源和 service 计数；
`_constraint_failure` 检查硬约束；`_objective_delta` 只重算受影响部分；`_apply_plan` 更新缓存。

### 第五层：理解搜索

15. `src/gmrp_alns/search/local_search.py`
16. `src/gmrp_alns/search/lns.py`
17. `src/gmrp_alns/search/common.py`
18. `src/gmrp_alns/search/model.py`
19. `tests/unit/test_search.py`

`local_search.py` 负责 First/Best Improvement 和 VND；`lns.py` 负责随机移除及
greedy/regret 修复；`common.py` 是最终全量复核关口；`model.py` 定义轨迹、算子统计和统一
结果。M4 仍是 hill-climbing：只接受比当前解更好的严格可行解，还没有 M5 的模拟退火、
自适应权重或 restart。

### 第六层：理解外部接口

20. `src/gmrp_alns/cli.py`
21. `tests/integration/test_cli.py`
22. `src/gmrp_alns/gmrp/checker.py`

CLI 只负责编排 parser、validator、objective 或 GAP solver；官方 checker adapter 只把外部
可执行程序作为独立进程调用，不把第三方 checker 逻辑混入自研实现。

### 第七层：阅读经典 GAP 轨道

23. `src/gmrp_alns/gap/model.py`
24. `src/gmrp_alns/gap/parser.py`
25. `src/gmrp_alns/gap/checker.py`
26. `src/gmrp_alns/gap/exact.py`
27. `src/gmrp_alns/gap/heuristics.py`
28. `tests/unit/test_gap.py`

先看 `exact.py` 理解标准 0-1 指派模型，再看 `heuristics.py` 中如何构造、repair、relocate
和 swap，有助于对照理解 GMRP 搜索中多出的服务约束和迁移成本。

---

## 9. 哪些代码是核心

### 9.1 正确性核心

| 文件 | 责任 | 为什么核心 |
|---|---|---|
| `gmrp/model.py` | 定义不可变领域对象 | 所有模块共享的数据契约 |
| `gmrp/parser.py` | 严格读取官方整数流 | 决定输入是否被正确解释 |
| `gmrp/validator.py` | 全量检查五类硬约束 | 判断解能不能提交 |
| `gmrp/objective.py` | 全量计算官方成本 | 判断一个解是否更好 |
| `gmrp/calculations.py` | 共享全量资源计算 | 防止 validator/objective 语义漂移 |

### 9.2 性能核心

| 文件 | 责任 | 为什么核心 |
|---|---|---|
| `gmrp/state.py` | 缓存、delta、apply/undo、候选裁剪 | 局部搜索和后续 ALNS 的内层循环 |
| `search/local_search.py` | First/Best 与 Relocate/Swap VND | M4 小邻域搜索主循环 |
| `search/lns.py` | Random Removal 与 Greedy/Regret Repair | M4 大邻域破坏—修复循环 |
| `search/common.py` | 最终全量复核 | 防止增量错误或修复错误流出求解器 |
| `tests/unit/test_state.py` | 增量与全量 oracle 对拍 | 防止“跑得快但算错” |
| `tests/unit/test_search.py` | 搜索可行性、改进性与复现性 | 固化 M4 行为边界 |

### 9.3 基线与接口核心

| 文件 | 责任 |
|---|---|
| `gap/exact.py` | CP-SAT 精确基线 |
| `gap/heuristics.py` | 构造、repair、relocate、swap 基线 |
| `cli.py` | 用户可调用的统一入口 |
| `gmrp/checker.py` | 与官方 checker 的外部交叉验证边界 |

下载脚本、manifest、报告文档同样重要，但它们主要承担可复现性和项目管理职责，不在候选
移动的性能热路径中。

---

## 10. 用 Python 直接运行搜索或操作增量状态

应用代码通常直接调用 M4 搜索函数：

```python
from pathlib import Path

from gmrp_alns.gmrp.parser import parse_assignment, parse_instance, write_assignment
from gmrp_alns.search.local_search import vnd_search

toy = Path("data/toy")
instance = parse_instance(toy / "model_toy.txt")
original = parse_assignment(toy / "assignment_toy.txt", instance)

result = vnd_search(
    instance,
    original,
    original,
    strategy="best",
    time_limit_seconds=2,
    seed=42,
    max_iterations=100,
)
assert result.objective.total_cost == 2411
write_assignment("candidate.sol", result.assignment)
```

调试 delta 或新增邻域时，再直接使用 M3 状态引擎：

```python
from pathlib import Path

from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance, write_assignment
from gmrp_alns.gmrp.state import SolutionState
from gmrp_alns.gmrp.validator import validate

toy = Path("data/toy")
instance = parse_instance(toy / "model_toy.txt")
original = parse_assignment(toy / "assignment_toy.txt", instance)

state = SolutionState(instance, original, original)

# 查看进程 1 最好的至多 3 个合法目标机器。
destinations = state.candidate_machines(1, top_k=3)
destination = destinations[0]

move = state.make_relocate(1, destination)
evaluation = state.evaluate_move(move)
assert evaluation.feasible
assert evaluation.delta is not None

before = state.total_cost
state.apply_move(move)
assert state.total_cost == before + evaluation.delta.total_cost

# 最终输出前仍使用全量 oracle。
assert validate(instance, original, state.assignment).feasible
assert evaluate_objective(instance, original, state.assignment) == state.objective
write_assignment("candidate.sol", state.assignment)

# 搜索中若拒绝该移动，可以无损恢复。
state.undo_move(move)
state.assert_consistent()
```

M4 搜索在 time limit 或 iteration limit 内反复生成候选、比较 delta、接受或拒绝移动，并
始终保留可行 incumbent。这个循环属于 `search/`，不应塞进 parser、validator 或 objective。

---

## 11. 测试与代码之间的对应关系

| 修改内容 | 至少应运行或补充的测试 |
|---|---|
| Model/Parser 字段 | `test_parser.py` |
| 任一硬约束 | `test_validator.py`，以及相应 state move 测试 |
| 任一成本分量 | `test_objective.py`，以及增量 delta 对拍 |
| Relocate/Swap 缓存 | `test_state.py` 的 full-vs-incremental 与 undo |
| First/Best、VND、LNS 或 repair | `test_search.py`，并以完整 oracle 复核 |
| GAP 模型或算法 | `test_gap.py` |
| CLI 参数或 JSON | `test_cli.py` |

推荐的完整验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=gmrp_alns --cov-report=term-missing
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy
```

性能微基准和外部 checker 不放进普通 CI，因为它们依赖外部数据、编译器或特定硬件。对应
命令与边界见 `docs/m1_verification.md`、`docs/m2_m3_verification.md` 和
`docs/m4_verification.md`。

---

## 12. 仓库目录应该如何理解

```text
src/gmrp_alns/gmrp/   GMRP 领域模型、解析、验证、目标和增量状态
src/gmrp_alns/search/ GMRP 局部搜索、基础 LNS、统一结果与最终复核
src/gmrp_alns/gap/    经典 GAP 解析、精确模型和启发式基线
tests/                 单元测试、性质测试和 CLI 集成测试
data/toy/              可提交、离线可运行的小实例
data/raw/              下载的第三方数据，Git 忽略
data/manifests/        外部数据的来源、时间、大小和 SHA-256
scripts/               checker 交叉验证、参考值验证、M4 验收和微基准
docs/                  数学模型、计划、协议、验证记录和本指南
configs/               后续实验配置
results/runs/          后续原始运行记录，Git 忽略
results/report/        后续聚合报告，Git 忽略
```

`.venv/` 是本机 Python 环境，不是项目源码；删除后可以重新安装，不应提交。

---

## 13. 常见误区

### “只给 model 就能计算迁移成本吗？”

不能。必须同时提供 initial assignment，因为移动与 transient 占用都以原机器为参照。

### “安全容量被超过就是不可行吗？”

不是。超过 safety capacity 会产生 load cost；超过最大 capacity 才违反硬约束。

### “service move cost 是所有移动进程数吗？”

不是。先统计每个 service 移动了多少进程，再取这些计数的最大值，最后乘全局权重。

### “assignment 文件里的数字前面是进程 ID 吗？”

不是。文件只存机器 ID；整数在序列中的位置隐式表示进程 ID。

### “`score` 返回了成本，所以非法解也能使用吗？”

不能。CLI 会同时输出 validation report；只有 `feasible=true` 的成本才是合法候选解成本。
非法解的命令退出码为 1。

### “为什么 GAP 必须传 `--sense`？”

因为 OR-Library 的整数文件本身不包含目标方向，方向来自数据集说明。默认猜测会导致参考
值被错误解释。

### “为什么已经有增量状态，还保留全量计算？”

全量 validator/objective 是简单、独立、可信的正确性 oracle；增量引擎优化速度，但每次
新增邻域或修改缓存逻辑都必须与全量实现对拍。

### “现在能直接跑 GMRP ALNS 吗？”

可以运行 M4 的基础 Random LNS，但还不能把它称为完整的 Adaptive ALNS。当前已有
First/Best Improvement、Relocate + Swap VND、Random Removal 和 Greedy/Regret Repair；
M5 才会增加多种 destroy/repair、模拟退火、算子评分与权重更新、restart 和历史最佳保护。

---

## 14. 继续开发时应守住的边界

实现 M5 及之后功能时，继续保持以下依赖方向：

```text
CLI / experiment scripts
        -> solver / search
        -> state / parser / validator / objective
        -> domain model / shared calculations
```

- Parser 不实现搜索；
- Validator 不为了某个算法修改约束语义；
- Objective 不依赖增量状态；
- State 可以依赖领域对象和官方成本定义，但必须长期与全量 oracle 对拍；
- Solver 只返回 assignment，最终结果必须再次经过全量 validator，必要时再交给官方
  checker。

读完本文后，最推荐的下一步是先运行 toy 的 validate、score 和 solve，再依次阅读
`model.py`、`parser.py`、`validator.py`、`objective.py` 和对应测试；确认理解完整正确性
边界后，再进入 `state.py`、`search/local_search.py` 和 `search/lns.py`。
