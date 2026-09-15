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

- src/gmrp_alns/gmrp/：领域模型、解析、验证、目标函数和 checker 适配；
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

- M0 仓库工程基础完成；
- M1 官方格式 Parser、完整 Validator、完整 Objective、JSON CLI 和 checker adapter 完成；
- 19/19 测试通过，覆盖率 92%，Ruff 与严格 mypy 通过；
- 官方 A1/A2 十个初始解全部被自研 Validator 判定可行；
- 十个实例的自研目标值与官方 checker 完全一致；
- 尚未实现搜索求解器、经典 GAP Track、增量状态或 ALNS；
- 下一里程碑：M2 经典 GAP Track。

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
