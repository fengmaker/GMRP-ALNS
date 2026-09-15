# GMRP-ALNS 项目知识与对话记录

> 本文件是本项目的长期上下文入口，同时承担“项目认知说明”和“项目对话日志”两项职责。
> 后续参与本仓库的开发者或 AI 在开始工作前应先阅读本文件和
> `docs/project_plan.md`。维护规则见仓库根目录的 `AGENTS.md`。

## 一、项目要解决什么问题

一句话概括：

> 已经有一批进程运行在一批机器上，现在允许重新搬迁进程；在保证系统满足全部
> 硬约束的前提下，寻找综合成本尽量低的新分配方案。

这是大规模、多资源、带服务约束的重新指派问题，不是传统调度问题。决策内容只有：

```text
每个进程最终放在哪台机器上？
```

传统调度通常还需要决定任务的开始时间、结束时间和执行顺序，而官方 GMRP 没有时间
维度，假设所有迁移同时发生。

### 1. 现实背景

云计算集群中，每台机器拥有 CPU、内存、磁盘等资源，每个进程会消耗这些资源。当前
分配可能存在机器过载、资源比例不平衡、服务副本过度集中等问题，因此希望移动一部分
进程改善集群资源使用情况。

移动不能随意进行，因为目标机器必须有足够资源，同一服务的副本需要隔离和分散，服务
之间可能存在依赖，而且迁移本身会产生代价。

### 2. 五类硬约束

1. **容量约束（capacity）**：机器上全部进程对每种资源的需求之和不能超过最大容量。
2. **服务冲突（conflict）**：同一服务的两个进程不能位于同一台机器。
3. **分散部署（spread）**：每个服务必须至少覆盖指定数量的不同 location。
4. **服务依赖（dependency）**：若服务 A 依赖 B，则每个存在 A 的 neighborhood 中都必须
   存在 B；依赖是有方向的。
5. **瞬时资源（transient usage）**：对磁盘等瞬时资源，迁移进程会在原机器和目标机器
   同时占用资源；原机器与目标机器相同时只计算一次。

### 3. 优化目标

一个方案首先必须合法，然后才比较成本。官方总成本为：

```text
总成本
= 加权负载成本
+ 加权资源平衡成本
+ 加权进程移动成本
+ 加权服务移动成本
+ 加权机器移动成本
```

- **load cost**：资源使用超过安全容量但尚未超过最大容量的部分。
- **balance cost**：机器上不同剩余资源的比例偏离目标。
- **process move cost**：移动某个进程本身的代价。
- **service move cost**：所有服务中，被移动进程数量的最大值。
- **machine move cost**：进程从原机器到目标机器的路径代价。

求解器必须权衡“移动带来的资源改善”和“移动产生的成本”。

## 二、输入与输出

### 1. 三类输入

| 输入 | 含义 | 来源 |
|---|---|---|
| Model | 机器、资源、服务、进程、约束和成本的完整定义 | 官方实例 |
| Initial assignment | 每个进程当前所在的机器 | 官方实例 |
| Candidate solution | 每个进程计划迁往的机器 | 求解器产生 |

#### Model 模型文件

模型是严格有序的整数流，依次描述：

1. 资源数量，每种资源是否瞬时、load cost 权重；
2. 机器数量，每台机器的 neighborhood、location、最大容量、安全容量和机器间移动成本；
3. 服务数量，每个服务的最小 spread 和依赖服务；
4. 进程数量，每个进程所属服务、资源需求和进程移动成本；
5. balance 目标及其权重；
6. process、service、machine 三类移动成本权重。

#### Initial assignment 初始分配

文件中按进程顺序给出机器编号，例如：

```text
0 3 0
```

表示进程 0、1、2 当前分别在机器 0、3、0。初始分配既是搜索起点，也参与瞬时资源和
三类移动成本的计算，因此不能省略。

#### Candidate solution 候选解

候选解与初始分配格式相同，例如：

```text
0 2 1
```

表示进程 0 → 机器 0，进程 1 → 机器 2，进程 2 → 机器 1。

### 2. 当前输出与最终输出

最终求解器的核心输出是候选解文件，即每个进程的目标机器编号。实验系统还需要输出
JSON 运行记录，包括可行性、成本分量、种子、时限、迭代次数和 time-to-best 等。

当前 M1 尚未实现搜索算法，已经支持三种 JSON CLI：

```text
gmrp-alns parse MODEL
gmrp-alns validate MODEL INITIAL SOLUTION
gmrp-alns score MODEL INITIAL SOLUTION
```

`parse` 描述实例规模，`validate` 判断候选解是否合法，`score` 输出合法性和完整目标值。

仓库中的官方格式 toy 示例为：

- `data/toy/model_toy.txt`：模型；
- `data/toy/assignment_toy.txt`：初始分配；
- `data/toy/solution_toy.txt`：候选解。

官方示例的初始成本为 4200，候选解成本为 2411。

## 三、程序架构与执行链

### 1. 主执行链

```text
官方模型文件 ──→ Parser ──→ Instance
初始分配文件 ──→ Parser ──→ Original Assignment
                              │
                              ▼
                        Solver（未来实现）
                              │
                              ▼
                      Candidate Assignment
                         │             │
                         ▼             ▼
                     Validator     Objective
                      合法吗？       成本多少？
                         │             │
                         └──────┬──────┘
                                ▼
                       解文件 + JSON 结果
                                │
                                ▼
                       官方 Checker 复核
```

项目分为三个概念系统：

1. **描述问题**：领域模型和 Parser；
2. **判断答案**：Validator 和 Objective；
3. **寻找答案**：后续实现的局部搜索、ALNS 和精确修复。

必须先保证前两部分正确。否则搜索算法可能快速找到一个成本看起来很低、实际却非法的
错误答案。

### 2. 依赖方向

```text
CLI / Scripts
      ↓
Parser、Validator、Objective
      ↓
Model、Calculations
```

越接近问题本质的模块越底层，越接近用户操作的模块越上层。底层不应反向依赖上层，
例如 `model.py` 不应该导入 `cli.py`。

### 3. 五个架构问题

开发新功能时依次思考：

1. **我要表示什么？** 放到领域模型。
2. **外部数据怎样进入程序？** 放到 Parser。
3. **业务规则怎样判断？** 硬约束放 Validator，成本放 Objective。
4. **用户怎样调用？** 放到 CLI、API 或实验 Runner。
5. **怎样证明它正确？** 放到 tests、验证 scripts 和 docs。

## 四、每个文件和文件夹的职责

### 1. 仓库根目录

- `README.md`：面向使用者的项目首页，说明项目定位、状态、安装和快速开始。
- `pyproject.toml`：Python 工程总配置，包含包信息、安装方式、CLI 入口、pytest、Ruff、
  mypy 和开发依赖。
- `ROADMAP.md`：未来要完成的里程碑和顺序。
- `CHANGELOG.md`：已经发生的版本变化；Roadmap 面向未来，Changelog 面向过去。
- `QA.md`：本文件，保存项目认知和项目相关对话记录。
- `AGENTS.md`：为后续 AI/开发者规定仓库级工作方式，包括先读计划书和维护 QA。
- `THIRD_PARTY.md`：登记官方资料、外部数据、checker 和第三方代码的来源及许可证边界。
- `LICENSE`：项目原创代码的 MIT 许可证。
- `CITATION.cff`：研究人员和 GitHub 使用的引用信息。
- `.gitignore`：排除虚拟环境、缓存、下载数据和临时实验结果。
- `.gitattributes`：统一 Git 文本和换行符行为。
- `problem_definition_v1.pdf`：可选的本地官方问题定义参考资料，不属于项目原创代码，默认
  不提交；仓库文档保留官方链接。
- `GMRP-ALNS_项目计划书与AI启动提示词.md`：原始中文完整计划书。

### 2. `.github/`

- `.github/workflows/ci.yml`：GitHub Actions；每次 push/PR 自动安装项目并运行 pytest、
  Ruff 和 mypy，防止修改破坏已有功能。

### 3. `src/`：产品代码

项目采用 `src layout`，实际 Python 包位于 `src/gmrp_alns/`。

- `src/gmrp_alns/__init__.py`：包入口和版本号。
- `src/gmrp_alns/__main__.py`：支持 `python -m gmrp_alns`。
- `src/gmrp_alns/cli.py`：命令行接口，只组织参数、调用核心模块、输出 JSON 和退出码，
  不承载核心业务规则。
- `src/gmrp_alns/gmrp/__init__.py`：集中导出 GMRP 模块的公共接口。
- `src/gmrp_alns/gmrp/model.py`：定义 Resource、Machine、Service、Process、BalanceCost、
  Instance 和 Assignment 等领域数据结构。
- `src/gmrp_alns/gmrp/parser.py`：把官方整数文件转换为领域对象，并检查数量、索引、
  布尔值、容量关系和多余/缺失输入等结构错误。
- `src/gmrp_alns/gmrp/calculations.py`：Validator 与 Objective 共享的全量资源统计和
  assignment 形状检查。
- `src/gmrp_alns/gmrp/validator.py`：检查五类硬约束并返回结构化违规信息，只判断
  “是否合法”。
- `src/gmrp_alns/gmrp/objective.py`：全量计算五类成本和总成本，只判断“成本多少”。
- `src/gmrp_alns/gmrp/checker.py`：将官方 C++ checker 作为外部进程调用，不把官方代码
  冒充自研逻辑。

### 4. `tests/`：正确性证据

- `tests/conftest.py`：提供多个测试共享的 toy instance、初始分配等 fixture。
- `tests/unit/test_parser.py`：解析、错误输入和 assignment 写入回读测试。
- `tests/unit/test_validator.py`：五类硬约束和瞬时资源语义测试。
- `tests/unit/test_objective.py`：目标成本分量和官方 toy 总成本测试。
- `tests/integration/test_cli.py`：从命令参数到 JSON 输出和退出码的完整集成测试。

单元测试检查零件，集成测试检查零件组合后的执行链。

### 5. `data/`：数据与来源

- `data/README.md`：数据来源、目录规范和版权策略。
- `data/download_roadef.py`：下载官方 A1/A2/B 数据或 checker，并记录 URL、时间、大小
  和 SHA-256。
- `data/manifests/`：提交到 Git 的官方文件来源与哈希清单。
- `data/toy/`：可提交的小型测试数据。
- `data/raw/`：下载的官方原始数据，默认被 Git 忽略。

数据管理原则是“下载脚本和哈希清单提交，大型外部数据不盲目提交”。

### 6. `scripts/`：操作与交叉验证

- `scripts/verify_initial_assignments.py`：批量使用自研 Validator 检查官方初始解。
- `scripts/verify_with_official_checker.py`：针对一个实例调用官方 checker。
- `scripts/crosscheck_official_dataset.py`：批量比较自研目标值和官方 checker 目标值。

这些脚本负责操作核心代码，核心业务规则仍应位于 `src/`。

### 7. `docs/`：详细文档

- `docs/project_plan.md`：完整项目计划书副本。
- `docs/mathematical_model.md`：数学模型和实现解释。
- `docs/experiment_protocol.md`：公平实验所需的种子、时限、硬件和指标规则。
- `docs/reproducibility.md`：安装、测试、数据与官方 checker 复现方法。
- `docs/m1_verification.md`：M1 的真实测试及官方 A1/A2 交叉验证记录。

`README.md` 是概览，`docs/` 是深入说明。

### 8. `configs/`

后续保存 GAP、GMRP 和实验配置，把 seed、time limit、destroy size、temperature 等参数
从 Python 代码中分离出来，使实验可复现。

### 9. `results/`

后续保存每次实验的 JSON、聚合 CSV、收敛图、消融实验和报告。当前只有说明文件，因为
还没有求解器，不应提前制造结果。

### 10. 自动生成、不手工维护的内容

- `.venv/`：独立 Python 环境；
- `.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`：工具缓存；
- `.coverage`：测试覆盖率数据；
- `src/gmrp_alns.egg-info/`：editable install 生成的包元数据；
- `__pycache__/`：Python 字节码缓存。

## 五、当前进度

- M0 仓库工程基础已经完成。
- M1 Parser、完整 Validator、完整 Objective 和最小 CLI 已经完成。
- 19 项测试全部通过，覆盖率 92%，Ruff 和严格 mypy 通过。
- 官方 A1/A2 十个初始解全部被判定可行。
- 自研目标值与官方 checker 在十个实例上逐项一致。
- 当前还没有实现搜索求解器、GAP Track、增量状态或 ALNS。
- 下一里程碑是 M2：经典 GAP Track。

---

# 项目对话日志

## 记录规则

1. 日志按时间和编号追加，旧记录原则上不覆盖。
2. 每条记录包含用户请求、助手回应/决定、实际修改或验证、当前结论与下一步。
3. 对话很长时可以忠实概括，但不能省略会影响后续工作的约束、决定、结果或未完成事项。
4. 不记录密钥、令牌和无助于项目理解的大段临时工具输出。
5. 如果后续发现旧记录有误，追加“更正”记录，不静默改写历史。

## QA-001｜启动项目并初始化仓库

**日期：** 2026-09-15

**用户请求：**

> 提供 ROADEF/EURO Challenge 2012 地址和
> `GMRP-ALNS_项目计划书与AI启动提示词.md`，要求根据提示词开始项目，先初始化整个仓库
> 并完成最开始的准备工作。

**助手回应与执行：**

- 区分了用户当前授权与计划书中的长期规划，仅执行 M0–M1，没有提前实现 ALNS。
- 核对官方题目、文件格式、瞬时资源语义、目标函数和官方 checker 接口。
- 初始化 Git `main` 分支、Python 包、开发环境、CI、许可证、文档和数据目录。
- 实现官方 model/assignment Parser、五类硬约束 Validator、完整 Objective、JSON CLI、
  官方 checker 适配器、toy instance、下载及交叉验证脚本。
- 下载被忽略的官方 A1/A2 数据和 checker 源码，提交相对路径和 SHA-256 清单。

**验证结论：**

- 19/19 测试通过，覆盖率 92%。
- Ruff 与严格 mypy 通过。
- 官方 A1/A2 十个初始解全部可行。
- 十个自研目标值与官方 checker 完全一致。
- Git 已初始化但没有擅自创建首个 commit。

## QA-002｜解释问题、输入输出与代码架构

**日期：** 2026-09-15

**用户请求：**

> 先讲一讲这个问题是什么、要解决什么、输入输出分别是什么，以及代码架构和每个
> 文件/文件夹的作用；用户希望培养架构思维。

**助手回应：**

- 解释了 GMRP 是在初始可行分配基础上的多资源机器重新指派，不是带时间维度的调度。
- 解释了 Model、Initial assignment、Candidate solution 三类输入，以及最终 assignment
  和实验 JSON 两类输出。
- 解释了容量、冲突、spread、dependency、transient usage 五类硬约束。
- 解释了 load、balance、process move、service move、machine move 五类成本。
- 用“Parser → Instance → Solver → Candidate → Validator/Objective → 官方 checker”说明
  程序执行链。
- 逐层说明根目录、`src/`、`tests/`、`data/`、`scripts/`、`docs/`、`configs/`、
  `results/` 和自动生成文件的职责。
- 总结架构思考方式：表示什么、如何输入、如何判断、如何调用、如何证明正确。

**沉淀结果：** 本次解释已经整理为本文件前五章，作为长期项目认知入口。

## QA-003｜建立长期 QA 与对话记录机制

**日期：** 2026-09-15

**用户请求：**

> 将此前内容整理到当前目录下的 QA 中，并让这个文件记录用户与助手关于本项目的每次
> 对话，方便以后再次进入仓库时理解项目背景。

**助手回应与执行：**

- 在仓库根目录创建 `QA.md`，整理问题定义、输入输出、架构、文件职责和当前进度。
- 回填当前已有的三轮项目对话记录。
- 创建 `AGENTS.md`，要求以后进入仓库的 AI 先阅读计划书和 `QA.md`，并在每次项目相关
  对话后追加日志。
- 将 `QA.md` 加入 README 文档入口，并在 Changelog 中登记。

**当前结论：** `QA.md` 成为追加式项目上下文和问答记录，不替代正式计划书、Roadmap、
Changelog 或具体技术文档。

## QA-004｜首次 GitHub 发布与 VS Code 对话方式

**日期：** 2026-09-15

**用户请求：**

> 先把项目提交到 GitHub；桌面客户端对话不方便，希望知道怎样直接在 VS Code 中与
> Codex 对话。

**助手回应与执行：**

- 检查本地 Git：`main` 分支尚无提交、尚未配置 remote，Git 作者为
  `cjs <2556841710@qq.com>`，系统未安装 GitHub CLI。
- Git Credential Manager 在沙箱账户下无法读取用户凭据；通过浏览器打开 GitHub 新建
  仓库页面后确认当前需要登录。认证必须由用户亲自完成，助手不代填密码或验证码。
- 发布前将第三方官方 PDF 保留为本地参考并加入 `.gitignore`，避免直接再发布；官方
  来源链接和数据哈希清单仍保留在仓库中。
- 使用 OpenAI 官方文档核对 Codex IDE extension：在 VS Code 安装/启用 Codex 扩展并
  登录；点击 Codex 图标，若图标不可见则从命令面板运行 `Codex: Open Codex Sidebar`；
  打开 `D:\\GAP` 后即可在编辑器上下文中继续项目对话。
- 在本地运行质量检查并准备首个 Git 提交；远程仓库创建和 push 需要在 GitHub 登录后
  继续完成。

**当前限制与下一步：** 用户完成 GitHub 登录后，创建目标仓库、配置 `origin` 并推送
`main`。若仓库公开，现有 Git 作者邮箱会出现在提交元数据中；如需隐藏，应在发布前改用
GitHub noreply 邮箱并重建首个提交。

## QA-005｜配置可持续的 GitHub 推送权限

**日期：** 2026-09-15

**用户请求：**

> 询问“尚未配置 remote、没有 GitHub CLI、需要登录”具体是什么意思，以及怎样授权，
> 使助手以后能够代为推送。

**助手回应与执行：**

- 说明 GitHub 身份授权和 Codex 命令审批是两层独立权限：前者证明本机 Git 可以代表用户，
  后者决定 Codex 何时可以执行带网络访问的 `git push`。
- 在用户 Windows 账户的 Git Credential Manager 中发现 GitHub 账户 `fengmaker`，但现有
  凭据已失效，使用 HTTPS 访问 GitHub 时返回认证失败。
- 启动 Git Credential Manager 的 GitHub device OAuth 重新授权流程；一次性设备代码只
  在对话中临时展示，不写入仓库。用户需要亲自在 GitHub 页面确认授权，助手不接触密码、
  Token 或验证码。
- 授权完成后应验证凭据、创建或确认 `fengmaker/GMRP-ALNS` 远程仓库、配置 `origin`、
  推送 `main`，并为低风险的 `git push` 命令使用窄范围持久审批，而不是关闭全部安全保护。

**当前限制与下一步：** GitHub device flow 正在等待用户确认。远程仓库仍未创建，当前只有
本地提交 `bffd990`；本次 QA 追加也将在授权成功后提交并一起推送。

## QA-006｜完成 GitHub 授权与首次推送

**日期：** 2026-09-15

**用户请求：**

> 已授权。

**助手回应与执行：**

- 确认 Git Credential Manager 已保存 GitHub 账户 `fengmaker` 的有效 OAuth 凭据；助手
  未读取或保存密码、Token、验证码等认证秘密。
- 检查到 `fengmaker/GMRP-ALNS` 尚不存在，按此前约定在 GitHub 创建同名**私有**空仓库，
  未生成远端 README、`.gitignore` 或许可证，避免与本地提交历史冲突。
- 将远程仓库配置为本地 `origin`，并提交 QA-005 和本条对话记录。
- 多次尝试通过 HTTPS 推送，但本机连接 `github.com:443` 持续超时或被重置；DNS 与 OAuth
  凭据均正常，因此问题位于网络传输层，不是授权失败。
- 验证 GitHub 官方备用入口 `ssh.github.com:443` 可以连接。改用该通道需要生成专用 SSH
  密钥并把公钥加入 GitHub 账户；因为这会新增持久访问凭据，必须先获得用户明确确认。

**当前限制与下一步：** 私有远程仓库 `https://github.com/fengmaker/GMRP-ALNS` 已创建，
本地 `origin` 也已配置，但代码尚未上传。用户确认新增专用 SSH 密钥后，改走 GitHub 官方
SSH 443 通道推送，并通过远端分支查询与本地状态检查验证结果。

## QA-007｜将首次推送操作交还用户

**日期：** 2026-09-15

**用户请求：**

> 用户在 PowerShell 中运行 `git push`，看到当前 `main` 没有 upstream；决定自行操作，
> 希望助手只提供需要运行的命令。

**助手回应与交接：**

- 停止代为操作 GitHub 页面或 API，不再替用户添加 SSH 公钥或执行推送。
- 确认本地工作区干净，`origin` 当前为
  `https://github.com/fengmaker/GMRP-ALNS.git`，`main` 尚未设置 upstream。
- 说明可先运行 `git push -u origin main`；`-u` 会在首次推送时建立本地 `main` 对
  `origin/main` 的跟踪关系，以后直接运行 `git push` 即可。
- 因本机此前直连 `github.com:443` 超时，提供 SSH 443 备用步骤：项目专用密钥已经生成在
  `C:\Users\86183\.ssh\id_ed25519_gmrp_alns`，用户应只复制 `.pub` 公钥到 GitHub，
  然后测试连接、把 `origin` 改为 `ssh://git@ssh.github.com:443/fengmaker/GMRP-ALNS.git`
  并首次推送。

**当前限制与下一步：** 远程仓库仍为空，首次 push 由用户亲自完成。成功标志是命令显示
`main -> main` 且 `git status -sb` 显示 `main...origin/main`；用户可把终端输出发回以便核验。

## QA-008｜确认首次推送成功并解释虚拟环境提示

**日期：** 2026-09-15

**用户请求：**

> 用户执行 `git push --set-upstream origin main` 后看到 `main -> main` 和 upstream 提示，
> 询问是否已经成功，以及 PowerShell 提示符前面的 `(.venv)` 是什么意思。

**助手核验与说明：**

- 本地 `git status -sb` 显示 `main...origin/main`，分支没有领先、落后或未提交文件。
- 本地 `HEAD`、本地记录的 `origin/main` 和 GitHub 远端 `refs/heads/main` 均指向提交
  `9ced052f1b409a527f4e6e41fd29a9989be94801`，确认首次推送完整成功。
- `(.venv)` 表示当前 PowerShell 已激活项目的 Python 虚拟环境；运行 `python`、`pip`、
  `pytest` 等命令时会优先使用 `D:\GAP\.venv` 内的解释器和依赖，避免污染系统 Python。
- 虚拟环境与 Git 身份、远端和推送没有关系；可用 `deactivate` 退出，重新进入项目后用
  `.\.venv\Scripts\Activate.ps1` 再次激活。

**当前结论：** GitHub 私有仓库的 `main` 已建立并跟踪成功，今后在本地提交后通常只需
运行 `git push`。项目下一阶段仍为 Roadmap 中的 M2（经典 GAP 轨道）。

## QA-009｜解释虚拟环境体积、HTTPS 推送差异与 SSH 备用方案

**日期：** 2026-09-15

**用户请求：**

> 询问为什么需要虚拟环境、`.venv` 是否会很大；为什么用户可以推送而助手此前不行；
> GitHub 显示较早的时间是否代表早已推送成功，以及为什么还曾建议使用 SSH。

**助手核验与说明：**

- 当前 `.venv` 实际约为 97.99 MiB。它隔离本项目的 Python 解释器和依赖，以避免不同项目
  的包版本互相冲突；它是可由依赖清单重建的本地文件夹。
- `.gitignore` 第 9 行已忽略 `.venv/`，因此这约 98 MiB 不会进入 Git 提交或上传 GitHub。
- 当前 `origin` 的 fetch/push 地址仍为 HTTPS：
  `https://github.com/fengmaker/GMRP-ALNS.git`，没有切换到 SSH。
- 助手此前三次 HTTPS push 和一次只读 HTTPS 测试均在连接 `github.com:443` 时超时或重置；
  用户稍后在交互式 PowerShell 中推送成功，随后助手也通过 HTTPS 成功推送 QA-008。这说明
  当时是临时网络状态或受控命令与交互式终端的执行路径差异，不是 GitHub 身份授权缺失。
- GitHub 页面上的“若干分钟前”通常对应提交自身的作者/创建时间；提交可以先在本地生成，
  之后再一次性推送，因此该时间不能单独证明远端早已收到代码。首次 push 输出中的
  `[new branch] main -> main` 才是远端分支在该次操作中创建成功的直接证据。
- SSH 443 是在 HTTPS 连续失败时提出的 GitHub 官方备用通道，并非项目必需配置。既然 HTTPS
  已恢复并验证可推送，就应继续使用 HTTPS。专用 SSH 密钥只在本机生成，未完成 GitHub
  添加或 remote 切换，不参与当前仓库访问。

**当前结论：** 保留 `.venv` 用于稳定开发，但不纳入版本控制；继续使用现有 HTTPS remote。
SSH 仅作为未来 HTTPS 长期不可用时的备选，不再作为当前必做步骤。

## QA-010｜回顾日常 Git 基础命令

**日期：** 2026-09-15

**用户请求：**

> 希望回顾最常用的 Git 命令。

**助手讲解：**

- 以 `status → diff → add → commit → pull → push` 为日常主线，解释工作区、暂存区、
  本地仓库和远程仓库之间的关系。
- 补充 `log`、`restore`、`restore --staged`、`branch`、`switch`、`fetch` 和 `remote -v`
  等常用查看、撤销、分支及远程命令。
- 强调先用 `git status` 和 `git diff` 确认范围，再提交；不把 `.venv`、数据集、密钥等
  被忽略或敏感文件加入版本控制。
- 给出本项目最常见的最短流程：修改代码后运行检查，执行 `git add`、`git commit`，
  最后 `git push`；当前 `main` 已跟踪 `origin/main`，无需重复设置 upstream。

**当前结论：** 用户已具备从检查修改到提交、同步和安全撤销的日常 Git 命令速查入口。
