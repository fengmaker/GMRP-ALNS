# GMRP-ALNS 项目知识与对话记录

> 本文件只保存继续开发所需的长期上下文和阶段性对话摘要。详细范围与验收标准见
> docs/project_plan.md，进度见 ROADMAP.md，已完成变更见 CHANGELOG.md。

## 1. 项目目标

研究并实现 ROADEF/EURO Challenge 2012 Machine Reassignment Problem（GMRP）的可复现
求解器，核心决策是：为每个进程选择最终机器。

候选解必须同时满足五类硬约束：

1. machine capacity；
2. 同一 service 的进程不能位于同一 machine；
3. service 至少覆盖规定数量的 location；
4. service dependency 在 neighborhood 层面成立；
5. transient resource 同时计入迁出机器和迁入机器。

合法解的总成本由五部分组成：

- load cost；
- balance cost；
- process move cost；
- service move cost；
- machine move cost。

## 2. 输入、输出与正确性边界

输入：

- Model：资源、机器、服务、进程、约束和成本；
- Initial assignment：每个进程的原始机器；
- Candidate solution：每个进程的目标机器。

核心输出是候选 assignment；实验阶段还需输出包含成本分量、随机种子、时限、迭代次数和
time-to-best 的 JSON。

主执行链：

~~~text
files -> parser -> instance/assignment -> solver
                                      -> candidate
                                      -> validator + objective
                                      -> solution/JSON -> official checker
~~~

依赖方向必须保持：

~~~text
CLI / scripts
    -> parser / validator / objective / solver
    -> domain model / shared calculations
~~~

Validator 和完整 Objective 是后续增量状态、局部搜索与 ALNS 的正确性基准。

## 3. 仓库结构速查

- src/gmrp_alns/gap/：经典 GAP 模型、OR-Library 解析、CP-SAT 和启发式基线；
- src/gmrp_alns/gmrp/：领域模型、解析、验证、目标函数、增量状态和 checker 适配；
- src/gmrp_alns/search/：局部搜索、基础 LNS、Adaptive ALNS、destroy/repair、接受与权重；
- src/gmrp_alns/exact/：受候选域、assignment 变量数和局部时限约束的 CP-SAT Repair；
- tests/：单元测试与 CLI 集成测试；
- data/toy/：可提交的小型官方格式实例；
- data/raw/：下载的官方数据，默认不提交；
- scripts/：官方数据验证和 checker 交叉验证；
- docs/：数学模型、实验协议、复现说明和项目计划；
- configs/：后续实验参数；
- results/：后续实验输出；
- .venv/：本地 Python 环境，已由 .gitignore 排除。

详细文件职责见 README.md 和 docs/project_plan.md，不在本文件重复展开。

## 4. 当前已验证状态

- M0～M6 已完成；
- M1 官方格式 Parser、完整 Validator、完整 Objective、JSON CLI 和 checker adapter 完成；
- M2 已实现 OR-Library Parser、CP-SAT、cost/regret greedy、repair、relocate/swap 和 GAP CLI；
- M3 已实现 `SolutionState`、relocate/swap 增量合法性与成本、apply/undo、预筛和 Top-K；
- M4 已实现 First/Best Relocate、Relocate/Swap VND、Random Removal、Greedy/Regret Repair、
  统一 seed/time limit、收敛轨迹、time-to-best、算子统计和 GMRP `solve` CLI；
- M5 已实现五种 destroy、三种 strict-feasible repair、模拟退火、分段自适应权重、时限内
  relocate warm start、restart、历史最佳保护、权重历史和目标分量轨迹；
- M6 已实现固定邻域外进程的 Restricted CP-SAT Repair，完整建模五类硬约束和五类目标，
  限制候选机器、assignment 变量数、单次局部时限及单线程，并仅回写经全量 oracle 复核的
  严格改善解；ALNS 支持周期调用和逐次求解遥测；
- 55/55 测试通过，覆盖率 88%，Ruff 与严格 mypy 通过；
- 官方 A1/A2 十个初始解全部被自研 Validator 判定可行；
- 十个实例的自研目标值与官方 checker 完全一致；
- 官方 OR-Library `gap1` 五个实例的 CP-SAT 最优值全部匹配参考值；
- 10,000 次随机合法 move 的增量值、apply/undo 和全量 oracle 对拍通过；
- A1_2 的 10,000 次 relocate 开发机复测全部一致，增量评估相对全量重算实测
  111.9389x；该数字仅是有环境和边界说明的本机微基准；
- M4 `vnd-first` 一秒开发验收在 A1/A2 十个实例上均改善初始成本；所有最终解通过
  自研 Validator 与官方 checker，十个成本逐一一致；这不是竞争性 benchmark；
- M5 冻结开发门在三实例、三 seed 的九组配对中相对 Random LNS 获得 6 胜 1 平 2 负，
  汇总目标低 416,047,975；18 个输出均通过官方 checker；该开发集参与过 warm-start 调整，
  不能作为最终泛化结论；
- Adaptive ALNS 一秒验收在 A1/A2 十个实例及 B1/B2 上均改善初始解并通过官方 checker；
  完整 B 数据的来源与 SHA-256 已记录，但其余 B 实例留待 M7 冻结实验；
- M6 冻结开发消融在三实例、三 seed 的九组配对中相对关闭精确修复获得 5 胜 3 平 1 负，
  汇总目标低 22,192,222；135 次局部求解全部满足 100 个 assignment 变量和 0.05 秒 solver
  上限，83 次改善当前解，18 个输出均通过官方 checker；该结果不是 M7 benchmark；
- B1 一秒安全烟测完成 11 次有界精确修复，最终成本 6,935,472,463 与官方 checker 一致；
- 下一里程碑：M7 预注册完整 A/B 多 seed benchmark、聚合、绘图与技术报告。
- M7 已开始：新增隔离实验运行器、冻结 manifest、哈希校验续跑、聚合和 Matplotlib 图表；
  `docs/m7_protocol.md` 预注册 20 个 A/B 实例 × 5 seed × 6 方法及固定子集四项消融，
  共 660 次一秒档观测。执行前 60 项测试、Ruff、mypy 通过；正式结果待运行。

不得伪造性能结果；外部数据和第三方材料默认不提交，只提交来源、脚本和哈希。

## 5. Git 与开发环境

- 本地仓库：D:\GAP；
- 当前主分支：main；
- 私有远程仓库：https://github.com/fengmaker/GMRP-ALNS；
- origin 使用 HTTPS，main 已跟踪 origin/main；
- GitHub 凭据由 Windows Git Credential Manager 保存，助手不记录密码或 Token；
- 用户与助手均已验证可以通过 HTTPS 推送；必要时 Codex 仍可能请求网络命令审批；
- 日常流程：status -> diff -> add -> commit -> push；
- .venv 约 98 MiB，只用于隔离 Python 依赖，不上传 GitHub；
- 曾为网络故障生成备用 SSH 密钥，但未加入 GitHub、未配置到 origin，当前无需 SSH。

## 6. 项目工作约定

- 开始开发前阅读本文件、docs/project_plan.md、ROADMAP.md 和 CHANGELOG.md；
- 解析、领域模型、验证、目标函数、求解器和接口保持分层；
- 先用全量实现证明正确，再实现增量优化；
- 实现变更后运行相应 pytest、Ruff 和 mypy；
- 每次项目相关对话追加简短记录，只保留决定、结果、阻塞和下一步；
- 当用户明确要求阶段性压缩时，可把已稳定的多条历史合并成范围摘要。

---

# 项目对话日志

## QA-001～010｜项目启动阶段摘要（已压缩）

**日期：** 2026-09-15

- 根据用户提供的计划书与官方挑战页面初始化仓库，仅完成 M0～M1，没有提前实现 ALNS。
- 建立 Python src layout、CI、测试、文档、数据来源记录和 MIT 许可证。
- 实现并验证 GMRP Parser、五类硬约束 Validator、完整 Objective、CLI 和官方 checker 适配。
- 通过 19 项测试、Ruff、mypy，以及官方 A1/A2 十个实例的 checker 交叉验证。
- 向用户解释问题、输入输出、架构分层、文件职责和常用 Git 工作流；这些稳定知识已归入
  本文件前六节或正式文档，不再保留逐轮重复内容。
- 建立 QA.md 与 AGENTS.md，要求后续 AI 读取项目上下文并维护简短对话日志。
- 创建 GitHub 私有仓库 fengmaker/GMRP-ALNS，配置 HTTPS origin，完成设备授权和首次推送。
- main 已跟踪 origin/main；用户和助手以后均可在本仓库提交并推送。
- .venv 是被忽略的本地 Python 隔离环境；SSH 只是 HTTPS 临时故障时讨论的备用方案，
  当前未启用。
- VS Code 可安装官方 Codex 扩展，在打开 D:\GAP 后继续项目对话。

## QA-011｜确认远程绑定并压缩早期上下文

**日期：** 2026-09-15

**用户请求：** 确认在 D:\GAP 中 origin 已绑定远程仓库、助手以后可以帮助提交和推送；
将 QA-001～010 浓缩，因为相关概念已经掌握。

**执行结果：**

- 确认 Git remote 是仓库级配置：在 D:\GAP 及其子目录中运行 Git，会定位到同一个
  .git 仓库和 origin；离开该仓库后不会自动使用这个远端。
- 将原 397 行 QA 压缩为短版长期上下文，并把 QA-001～010 合并为阶段摘要。
- 保留问题边界、架构、验证证据、GitHub 状态、下一里程碑和必要安全说明。
- 旧版内容仍存在于 Git 历史中，可在需要时恢复。

**下一步：** 按 ROADMAP 进入 M2 经典 GAP Track。

## QA-012｜明确 Git 推送分工

**日期：** 2026-09-15

**用户决定：** 今后由助手完成本地修改、验证和 commit；用户亲自执行 push。

**执行约定：** 助手不得在未获得用户新的明确要求时运行 `git push`。每次本地提交后应告知
提交哈希、分支领先远端的提交数，以及用户需要运行的推送命令。

## QA-013｜定位 GitHub HTTPS 连接失败层级

**日期：** 2026-09-15

**用户问题：** 为什么有时连接不上 GitHub。

**只读诊断：** `github.com` 可解析为 `20.205.243.166`，Ping 成功（约 101 ms），但 TCP
443 连接失败，`git ls-remote` 随后在约 21 秒处超时。这表明故障发生在 HTTPS 网络连接层，
尚未进入 GitHub 身份认证或仓库权限检查；remote 和凭据不是本次错误的直接原因。

**结论：** 结合用户和助手此前都曾通过同一 HTTPS remote 成功推送，最可能是间歇性的
网络路由、出口或 GitHub CDN 端点连通问题。继续维持 HTTPS 配置，失败时稍后重试或切换
网络；不随意修改 hosts，也不把 SSH 设为当前必需项。助手只记录并本地 commit，不 push。

## QA-014｜完成 M2 经典 GAP 与 M3 GMRP 增量状态

**日期：** 2026-09-16

**用户请求：** 阅读 QA、README、AGENTS 等文档，继续完成 M2 和 M3。

**执行结果：**

- 完整复核项目计划与当前干净工作树，先确认 M1 的 19 项测试、Ruff 和 mypy 基线通过；
- 新增独立 GAP 分层：严格 OR-Library 多实例解析、显式最小化/最大化方向、CP-SAT 精确
  模型、cost/regret greedy、容量修复、relocate/swap 局部搜索及 JSON CLI；
- 下载被忽略的官方 `gap1`，提交来源/哈希清单；五个实例的精确结果分别为
  336、327、339、341、326，全部匹配 OR-Library 最大化参考值；
- 新增 GMRP `SolutionState`，缓存资源、瞬时资源、服务机器/位置/邻域稀疏计数、服务迁移
  计数和完整目标；实现 relocate/swap 的合法性、目标 delta、apply/undo、预筛与 Top-K；
- 10,000 次 seeded 合法移动逐次对拍全量 objective/validator，并验证完整快照恢复；A1_2
  另做 10,000 次 relocate 对拍，全部一致，本机测得 111.9389x 候选评估加速；
- 新增可复现下载、参考值验证和增量微基准脚本，更新 README、数据说明、第三方记录、
  复现说明、路线图、变更日志及 M2/M3 验证记录；
- 最终验证：29 项测试全部通过，覆盖率 86%，Ruff 与严格 mypy 通过。

**限制与下一步：** 性能数据仅覆盖一次本机 A1_2 微基准，不代表完整实验结论；GAP
外部参考验收目前覆盖 `gap1`。下一里程碑按计划进入 M4：基于已验证的增量状态实现
First/Best Improvement、Relocate+Swap VND 和基础 Random LNS，并保持最终解通过全量
Validator/官方 checker。

## QA-015｜补充输入输出与快速上手文档

**日期：** 2026-09-16

**用户请求：** 暂停算法开发，编写详细文档解释问题输入输出、如何快速上手、需要阅读和
重点理解哪些代码，以及哪些文件构成问题输入输出。

**执行结果：**

- 新增 `docs/getting_started_zh.md`，系统说明 GMRP/GAP 的关系、五类硬约束、五类成本、
  官方整数流 model 格式、initial/candidate assignment 语义、GAP 格式和两类 JSON 输出；
- 给出 Windows PowerShell 五分钟上手命令、外部数据准备方法、端到端数据流、增量状态
  Python 示例、代码阅读顺序、核心模块分级、测试映射、目录职责和常见误区；
- 明确当前能力边界：GMRP 已支持解析、验证、计分和增量移动，但完整 GMRP solve/局部
  搜索/LNS 尚属 M4；GAP 已支持精确及启发式求解；
- 在主 README 增加指南入口，修正 `results/README.md` 对 M3 微基准与解质量 benchmark
  的区分，并在 CHANGELOG 登记文档。

**验证与下一步：** 已实际复跑 GMRP parse/validate/score 与 GAP parse/exact solve，分别
得到 feasible、GMRP toy 总成本 2411 和 GAP toy 最优值 8；29 项测试、Ruff、严格 mypy
及 `git diff --check` 全部通过。算法里程碑仍停在 M3，用户恢复开发时进入 M4。

## QA-016｜完成 M4 局部搜索与基础 LNS

**日期：** 2026-09-17

**用户请求：** “继续 M4”。

**执行结果：**

- 新增独立 `search/` 层，实现 seeded First/Best Relocate、Relocate + Swap VND，以及
  Random Removal + Greedy/Regret Repair；所有搜索只接受严格可行的改善解，返回前由完整
  Validator 和 Objective 再次复核；
- 统一 time limit、iteration limit 和 seed，记录收敛轨迹、time-to-best、候选评估数、
  目标分量和算子统计；新增 `gmrp-alns solve`，可写官方一行 assignment 并输出 JSON；
- 增加局部搜索、swap 逃逸、两种 repair、两种 Random LNS 复现性、零迭代及 CLI 输出测试；
- 新增 `scripts/verify_m4_a_set.py` 和 `docs/m4_verification.md`。seed 42、每实例一秒的
  `vnd-first` 验收在 A1/A2 全部十个实例上改善初始解；十个最终解均通过自研 Validator
  和未修改的官方 checker，成本逐一一致；
- 同步 README、快速上手、复现说明、实验协议、结果边界、ROADMAP 和 CHANGELOG；清理
  临时候选文件，外部数据与 checker 仍未加入 Git；
- 完整验证为 38/38 tests、87% coverage、Ruff、严格 mypy（22 个源文件）和
  `git diff --check` 全部通过。

**限制与下一步：** M4 是 hill-climbing 基线，一秒 A 组运行只用于工程验收，不是竞争性
解质量结论。跨机器确定性回归应同时固定 seed 与 iteration limit，墙钟耗时字段不要求
逐字节相同。下一里程碑为 M5：多种 destroy/repair、模拟退火、自适应权重、restart 和
历史最佳可行解保护。

## QA-017｜完成 M5 Adaptive ALNS

**日期：** 2026-09-17

**用户请求：** “继续 M5”。

**执行结果：**

- 新增 `acceptance.py`、`operator_selection.py`、`destroy.py` 和 `alns.py`；实现 random、
  high-load、resource-critical、related-service、high-move-gain 五种 destroy，以及 greedy、
  regret、seeded randomized 三种严格可行 repair；
- 实现从初始成本拟合的模拟退火、分段反应权重、轮盘赌选择、无全局改善 restart、历史
  最佳可行解保护，以及总时限内 20% relocate warm start；Penalty Search 未以弱化版本冒充，
  当前明确输出 `strict_feasible=true`；
- 扩展 JSON 遥测：接受/失败/新最佳次数、候选数、算子耗时与贡献、最终权重、权重历史，
  以及每个接受状态的完整目标分量；CLI 新增 `adaptive-alns` 与相关参数；
- 冻结三 A 实例 × 三 seed × 每方法一秒的开发配置。初版无 warm start 仅 4/9 胜并被记录
  为未通过；revision 2 保持实例、seed、总时限和门槛不变，加入时限内 warm start 后达到
  6 胜 1 平 2 负，汇总目标比 Random LNS 低 416,047,975，18 个解均通过官方 checker；
- Adaptive ALNS 在 A1/A2 十个实例和 B1/B2 上各用 seed 42、一秒运行，12 个最终解全部
  改善初始解并与官方 checker 成本一致；下载完整 B 组到忽略目录并提交 20 个文件的来源、
  大小和 SHA-256 清单；下载器增加原子 `.part` 写入与 `--resume`；
- 新增 M5 单元/CLI 测试、两个验收脚本和 `docs/m5_verification.md`，并同步 README、快速
  上手、复现说明、实验协议、结果边界、ROADMAP 和 CHANGELOG；
- 完整验证为 49/49 tests、87% coverage、Ruff、严格 mypy（26 个源文件）和
  `git diff --check` 全部通过。

**限制与下一步：** M5 结果是参与过参数调整的工程开发门，不是 M7 benchmark；墙钟运行
存在机器调度波动，确定性回归使用固定 seed 和 iteration limit。B3～B10 未形成 M5 质量
结论。下一里程碑为 M6：受变量规模和局部时限严格限制的 Restricted CP-SAT Repair，失败时
必须安全回退并完成启用/关闭消融。

## QA-018｜讲解第一层四个文件与字段映射

**日期：** 2026-09-17

**用户请求：** 暂缓继续里程碑，先按快速上手指南理解第一层四个文件，要求把具体数字与
代码字段对应讲清楚。

**说明内容：** 逐项解码 `model_toy.txt` 的 2 个 Resource、4 个 Machine、2 个 Service、
3 个 Process、1 个 BalanceCost 和 3 个全局迁移权重；解释 `assignment_toy.txt=(0,3,0)`
与 `solution_toy.txt=(0,2,1)` 都按 process 下标保存 machine ID；将其映射到 `model.py` 的
不可变 dataclass 和 `Assignment` tuple，并用候选解说明 transient 双端容量、service
conflict/spread/dependency 及 2411 目标值如何使用这些字段。

**变更与下一步：** 本轮不修改算法或里程碑状态，仅追加本日志；未运行测试，因为没有代码
变更。用户理解第一层后，下一阅读层是 `parser.py` 与 `test_parser.py`，重点是整数流如何
构造成这些领域对象，以及 parser 负责和不负责哪些验证。

## QA-019｜完成 M6 Restricted CP-SAT Repair

**日期：** 2026-09-18

**用户请求：** “继续 M6，阅读 agent、README 等文件夹。”

**执行结果：**

- 按仓库约定完整恢复 `AGENTS.md`、`QA.md`、项目计划、ROADMAP、CHANGELOG、各级 README，
  并复核 M5 搜索、CLI、测试与外部 checker 接口后再确定接入设计；
- 新增 `exact/restricted_repair.py`：固定邻域外分配，保留每个移除进程的 incumbent 机器，
  有界选择候选机器并建立 CP-SAT；模型覆盖普通/瞬时容量、conflict、spread、dependency 和
  完整官方目标，使用单线程、显式 seed、局部截止时间、candidate 与 assignment 变量上限；
- 求解状态为 unknown/infeasible、超时、变量不足、无改善或全量 oracle 拒绝时返回空结果，
  不修改当前解；只有 Validator 与 Objective 复核后的严格改善才进入 ALNS；
- `adaptive-alns-restricted` 在第 1 轮及其后固定间隔调用精确修复，输出每次 status、变量数、
  branches、conflicts、bound、solver budget 和 wall time，并保留聚合算子统计；CLI 暴露四个
  M6 限制参数；
- 新增全部七个 toy 非空进程子集与穷举最优逐一对拍、失败回退、过期 deadline、ALNS 和 CLI
  测试；最终 55/55 tests、88% coverage、Ruff、严格 mypy（28 个源文件）和 diff check 通过；
- 新增冻结配置、A 组启用/关闭消融脚本及 `docs/m6_verification.md`。九组一秒配对为 5 胜
  3 平 1 负，混合方法汇总成本低 22,192,222；135 次精确调用中 83 次改善当前解，所有上限
  均满足，18 个最终解均通过官方 checker；
- B1 一秒安全烟测进行了 11 次受限调用，最终成本 6,935,472,463，经官方 checker 验证；
  同步 README、快速上手、复现/实验协议、结果边界、ROADMAP 和 CHANGELOG。

**限制与下一步：** M6 消融是参与过调用时机调整的开发门，墙钟一秒结果有调度波动，不能
证明 H4 的普遍收益；B1 也只是单次安全烟测。下一里程碑进入 M7：先冻结独立实例、至少五个
seed、时间档、硬件/依赖/commit 和统计方案，再运行完整 A/B 实验、聚合、绘图与技术报告。

## QA-020｜推进 M7 实验与技术报告

**日期：** 2026-09-18

**用户请求：** “继续 M7”，随后“继续”。

**执行中：** 已读取项目上下文，新增 `experiments/` 的协议校验、冻结、独立进程执行、
原始记录哈希校验续跑、按 seed 配对聚合、CSV/JSONL/PNG 报告生成。冻结 660 次完整 A/B
一秒档矩阵，B3～B10 单列 held-out；记录实际耗时与超预算，不以请求时限冒充硬截止。
增加统计/篡改/worker 测试，60 项测试、Ruff、严格 mypy（34 个文件）通过。下一步在源码
提交后冻结 manifest 并实际执行矩阵，完成正式报告。10/60/300 秒档留作后续扩展。
