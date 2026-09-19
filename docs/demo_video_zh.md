# GMRP-ALNS 2～3 分钟演示录屏脚本

目标时长约 2 分 40 秒。录制前使用 1080p 终端、20pt 左右等宽字体，并把仓库定位到根目录。
视频只使用仓库内 toy 数据，不展示 Token、凭据、`data/raw/` 或个人目录。

## 录制前准备

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

开始录制前清空终端。不要把安装过程计入成片；它受网络和 pip cache 影响。

## 分镜与旁白

### 0:00–0:20｜问题与可信边界

画面：README 顶部与架构图。

旁白：

> GMRP-ALNS 求解 ROADEF 2012 机器重分配问题。输入是模型和初始分配，输出是每个进程的
> 最终机器。项目的关键不是只产生一个更低成本，而是让每个候选解都能通过独立的完整
> Validator、Objective 和官方 checker。

### 0:20–0:45｜一条命令演示

画面：终端执行：

```powershell
.\.venv\Scripts\python.exe scripts/demo.py
```

旁白：

> 这一条命令运行完全离线的发布烟测：解析 GMRP toy，验证参考解，计算官方五项成本，
> 运行固定 seed 和迭代数的 Adaptive ALNS 加 Restricted Repair，再验证写出的解；最后用
> CP-SAT 复现 GAP toy 的精确最优值。

### 0:45–1:05｜解释输出

画面：停在 demo 的 JSON 末尾，指出 `status`、两个 cost 和 `candidate_revalidated`。

旁白：

> `status` 为 ok，GMRP 参考成本和搜索成本都是 2411，候选解复核为 true；GAP 最优值为 8。
> 中间文件写入临时目录并自动清理，所以演示不会污染仓库。

### 1:05–1:35｜算法架构

画面：`docs/architecture.md` 的 Candidate-solution flow。

旁白：

> Parser 只负责解释官方整数流；完整 Validator 和 Objective 定义正确性。局部搜索使用经过
> 10,000 次随机对拍的增量状态。ALNS 组合五种 destroy、三种严格可行 repair、模拟退火和
> 自适应权重。Restricted CP-SAT Repair 只优化一个固定补集的有界邻域，失败或无改善时安全
> 回退，任何结果输出前仍要经过全量 oracle。

### 1:35–2:10｜冻结实验与负面结果

画面：`results/m7/quality_runtime.png`，随后 `results/m7/ablations.png`。

旁白：

> M7 在冻结源码、配置、输入、checker 和环境哈希后，串行运行了 660 次 A/B 观测。所有解
> 都通过官方 checker。结果并没有偏向复杂算法：一秒请求预算下 Relocate 和 VND 平均改善
> 约 12%，ALNS 为 9.13%，Restricted 为 8.99%。因此项目明确报告复杂方法在这个预算内没有
> 胜出，而不是只展示正结果。

### 2:10–2:30｜时限限制与复现

画面：`docs/m7_verification.md` 的 Main matrix 和 Limits。

旁白：

> 一秒是请求预算而非硬截止，660 次中有 208 次完整 solver 调用超过 1.1 秒容差；held-out
> B3 到 B10 没有严格及时的 ALNS/Restricted 配对。原始 JSONL、实际耗时、内存、失败分母、
> 图表和校验和全部保留，报告可从归档离线重建。

### 2:30–2:40｜结束

画面：README 的文档导航与测试命令。

旁白：

> 仓库还提供数学模型、代码阅读路线、复现实验协议和 61 项自动测试。这个 v1.0 发布强调
> 三件事：先证明正确，再做增量优化，最后让实验结论可审计。

## 录制后检查

- 成片在 2～3 分钟内，文字在手机尺寸仍可读；
- 没有个人用户名、绝对本机路径、通知、凭据或外部数据文件；
- 画面中的数字与 `docs/m7_verification.md` 一致；
- 不使用“最优”“SOTA”“严格一秒”等未被证据支持的措辞；
- 视频描述附仓库、release notes、M7 verification 和数据来源链接。
