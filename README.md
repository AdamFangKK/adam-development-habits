# Adam's Development Habits

> 面向 AI 辅助开发的工程质量 Skill：要求每次改动都有唯一实现路径、清理证据、必要的稳定性保护和真实验证结果。

`SKILL.md` 是唯一的规范来源；本文是中文使用说明和概览。规则、模板或脚本发生变化时，以 `SKILL.md` 和实际校验结果为准。

`Adam's Development Habits` 是适用于 Codex 的通用开发习惯 Skill。它不绑定语言、框架或云平台，也不试图替代项目本身的架构、测试或 CI。它的核心是让 AI 的每次改动具备可定位的唯一实现、可审计的替换清理、按风险匹配的保障，以及真实运行过的验证证据。

## 核心能力

| 能力 | 作用 |
|---|---|
| 唯一有效实现 | 先定位行为的唯一负责人，优先原地修改，避免新增平行实现。 |
| 替换即清理 | 新实现替换旧实现时，同一改动中迁移调用方并删除旧代码、引用、配置、测试和文档。 |
| 风险分级 | 将改动分为轻量、常规和高风险三级，避免简单改动流程过重，也避免高风险改动证据不足。 |
| 原则与验收条件 | 在复杂改动前明确项目约束、成功条件、失败条件和兼容性要求。 |
| 证据台账 | 在编辑前说明实现入口、受影响调用方、行为不变量、兼容策略和验证计划。 |
| 因果执行纪律 | 对根因不明的故障先区分症状与假设，用可证伪检查避免修补下游表象。 |
| 可维护边界与原子设计 | 明确模块责任、契约、依赖方向与状态转换，避免耦合和过度抽象。 |
| 失败语义与数据所有权 | 明确权威状态、生命周期、稳定错误结果、重试和未知结果的处理方式。 |
| 契约演进与测试质量 | 用消费者、兼容策略、迁移/回滚与契约/不变量测试保护长期演进。 |
| 运行就绪、性能与安全 | 用预算、可操作告警、资源限制和威胁边界控制线上风险。 |
| 交付生命周期与仓库卫生 | 用原子 Git 提交、PR、发布回滚、迁移、配置/Secret、依赖、运行手册与可复现环境约束交付质量。 |
| 机器可读证据模式 | 仓库显式启用后，用 JSON 工件记录改动事实，并由本地脚本和 CI 校验。 |
| 企业级横切保障 | 按场景检查 `traceId`、结构化日志、超时、重试、幂等、限流、鉴权、审计和健康检查。 |
| 清理审计 | 在完成前检查未使用文件、导入、导出、类型、路由、任务、队列、配置和 Feature Flag。 |
| 验证门槛 | 要求实际运行相关的格式化、lint、类型检查、测试、构建和静态分析。 |
| 真实完成报告 | 以已运行命令及结果作为证据，不允许用“应该可以”代替验证。 |

## 它能解决什么问题

这些能力不是额外的流程负担，而是针对 AI 多轮开发最容易积累的失控点：

- **两套实现并存**：新功能写了一套，旧入口和旧调用方还在，导致行为不一致、修改范围无法判断。
- **替换不彻底**：组件、接口或配置更新后，旧路由、Feature Flag、类型、测试和文档继续误导后续 AI。
- **缺少边界保障**：网络调用没有超时或幂等设计，重试造成重复写入；敏感操作缺少鉴权或审计。
- **问题无法追踪**：日志没有 `traceId`、操作上下文、耗时和结果，跨服务或异步问题难以复盘。
- **错误被伪装成成功**：用空值或吞异常代替稳定的错误语义，调用方无法判断重试、降级还是终止。
- **数据多头与契约漂移**：多个模块维护同一事实，或 API、事件、Schema 没有消费者、兼容和迁移策略。
- **无法运营的上线风险**：没有性能预算、可行动告警、资源上限和威胁边界，问题只能靠事故暴露。
- **未验证即完成**：AI 用“应该可以”结束任务，却没有实际运行测试、类型检查、构建或静态分析。
- **上下文持续劣化**：废弃代码、旧配置和过时说明留在仓库里，使后续 AI 基于错误信息继续开发。

## 工作方式

Skill 不是自动修改代码的脚本，而是一份会在 AI 执行开发任务时加载的严格工作流。它会引导 AI 按以下顺序工作：

```text
识别改动风险，并读取项目原则与约束
        ↓
定义验收条件、失败行为与兼容要求
        ↓
根因不明时，记录假设与区分性检查
        ↓
定位现有实现与调用关系
        ↓
记录不变量、替换范围与兼容需求
        ↓
在唯一有效路径中实现改动
        ↓
按场景补齐稳定性、可观测性与安全保护
        ↓
删除被替换的实现及其残留引用
        ↓
运行验证并审查最终 diff
        ↓
输出可追溯的完成报告
```

设计吸收了 [Spec Kit](https://github.com/github/spec-kit) 的原则与规格思路、[Superpowers](https://github.com/obra/superpowers) 的测试和复查节奏、[AGENTS.md](https://github.com/agentsmd/agents.md) 的仓库级规则分发方式，以及 `Knip`、`pre-commit`、`Semgrep` 等工具的自动化质量门理念。

对于非简单改动，Skill 会要求维护一份证据台账：

```text
Canonical owner: <实际入口文件与符号 / 路由>
Affected callers/contracts: <受影响调用方或公开契约>
Invariant: <必须保持为真的行为>
Replaced paths: <需要删除的旧路径，或 none>
Retained compatibility: <保留原因、消费者、删除条件与测试，或 none>
Safeguards: <适用的稳定性与可观测性措施>
Verification: <已执行命令及实际结果>
Causal diagnosis: <启用时记录症状、假设、区分性证据与结论>
Design boundary: <owner、契约、错误结果和状态转换，或 not applicable>
Dependency audit: <变更依赖、允许方向和循环/私有状态检查，或 not applicable>
Extension decision: <真实消费者/稳定契约与测试，或保留直接实现的原因>
Data ownership: <权威 owner、生命周期/隐私边界，或 not applicable>
Error model: <稳定结果分类、重试/未知策略，或 not applicable>
Contract evolution: <兼容、迁移/回滚、消费者测试，或 not applicable>
Operational budget: <SLO/性能/资源/安全信号与响应，或 not applicable>
```

### 风险分级

风险等级、升级条件和每级的完整证据要求以 [`SKILL.md` 的 Operating Model](./SKILL.md#operating-model) 为准：Level 0 用于无行为变化的小改动，Level 1 用于常规行为改动，Level 2 用于公开契约、迁移、安全、金额、并发和架构风险。不确定时必须选择较高等级。

### 因果执行纪律

这不是要求 AI 对每个任务进行长篇“推理”，而是防止它在根因不明时直接修改最靠近报错的代码。对于不明确的 Bug、回归、性能或可靠性下降、偶发故障，以及跨服务、配置、发布、依赖或并发边界的问题，先记录：

- 已观察到的症状，以及至少一个替代解释；
- 能够区分这些解释的最低风险检查；
- 实际检查结果和证据强度；
- 结论属于根因修复、缓解、仅增加观测，还是未知。

在 Causal Full 模式中，还要记录从症状回溯到调用方、数据、配置或依赖的上游路径，以及相关的变更、发布或运行时间线。

提交结论前先做权限前置检查：明确写出 `Execution authority`（只读或已授权的代码变更 worktree）和 `Counterfactual status`（未运行、仅内存、提议、阻塞或已执行）。仅在授权 worktree 中实际产生候选 diff，并有该 worktree 的前后命令/测试输出时，才能使用 `Causal conclusion: root-cause fix`；只读观察、内存探针、伪代码和预期结果一律保持 `unknown`。

Git 历史和时间接近性只能提供候选线索。只有复现或隔离干预支持时，才可以把改动称为根因修复。证据不足时，优先增加可观测性、构建最小复现或采取可回滚的保护措施。在机器可读证据模式中，因果假设只能引用已声明的本地证据工件；校验器会检查其仓库相对路径和 SHA-256，防止悬空或被静默修改的引用。根因修复还必须引用测试、命令或 trace 的执行工件，不能只引用测试源码；CI 会重新生成并比对报告。

[`examples/causal-execution-experiment.py`](./examples/causal-execution-experiment.py) 是一个可运行的支付重试案例：它先证明重复扣款存在于支付网关记录而非 UI，再通过稳定幂等键的隔离干预验证上游修复点。配套的 [证据工件](./examples/causal-execution-experiment.json) 展示了机器可读的结论格式。

[`examples/causal-notification-experiment.py`](./examples/causal-notification-experiment.py) 是更严格的通知发送案例：它组合了“远端已接受但本地超时或进程崩溃”、可重试与终态的预接受拒绝、重试、队列重复投递、重启、跨实例并发、ack 失败和供应商幂等键过期。案例证明传输消息或重试次数生成的幂等键会产生三次外部发送；安全路径持久化完整操作身份，在对账结果为未知时不重发或作为成功 ack，只在确认历史结果、确认不存在或确认可重试拒绝后继续；每次确认、ack/DLQ 和恢复交接都会重新绑定该身份，终态拒绝连同安全原因持久化后不可复活或改写，恢复任务以唯一键去重，并产出不含收件人和内容的重试决策审计记录。

#### 运行通知恢复实验

在仓库根目录执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 examples/causal-notification-experiment.py --report
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_evidence.py \
  .adam/evidence/causal-notification-recovery.json \
  examples/causal-notification-experiment.json
```

实验包含 13 个确定性场景：超时、崩溃、供应商幂等键过期、对账未知、重启、跨实例并发、ack 失败、恢复任务去重、可重试与终态拒绝，以及在确认、终态 ack 和恢复交接边界的操作身份冲突。通过只说明这个隔离模型满足其状态机不变量；它不能证明生产队列、供应商查询语义、分布式数据库故障或死信策略已经安全。

### 可维护性、去耦与原子化

这套 Skill 不用“函数必须很短”或“每个模块都要接口化”衡量质量。它要求的是：读者能够在局部识别模块责任、输入输出契约、错误结果、状态转换和副作用；域规则保持在最窄的责任边界，并且除非既有架构明确要求，否则不引入 HTTP、ORM 或 UI 等外层耦合；依赖方向清晰，避免循环依赖、共享可变全局状态、跨模块窥探私有实现和无归属的万能工具模块。

原子化也不是把代码机械切碎。一个单元可以组合多个相邻步骤，但应只负责一个决策或一个可恢复的状态转换。跨数据库、消息队列或外部服务的写入不能伪装成原子操作：应优先使用事务；无法使用时，明确顺序、幂等、恢复归属和补偿或 Outbox 策略。

扩展点只在已有两个独立消费者、稳定的外部契约或明确测试边界时引入。否则保留直接实现，避免抽象层成为耦合和理解成本。适用的 Level 1/2 改动会在证据台账中记录 `Design boundary`、`Dependency audit` 和 `Extension decision`，并针对公开扩展点或多适配器补充契约或集成测试。

### 失败、数据、契约与测试

每一份可变业务或个人数据都必须有权威 owner、有效状态转换、访问边界与保留/删除策略。边界错误应区分验证或前置条件、鉴权/所有权、领域冲突、可重试依赖、终态依赖和未知结果，并以稳定安全的错误码或类型表达；不能用 `null`、空对象或吞异常伪装成功。

公开 API、事件、Schema、配置和共享库都是契约。优先兼容性新增，识别消费者后再删除、收紧或改默认值；破坏性变更应有版本、迁移、回滚和消费者测试。测试要验证业务结果和不变量，覆盖失败、权限、兼容、边界值与并发，而不是只断言内部方法或 mock 调用次数。时间、随机数、并发与外部 I/O 必须受控，flaky 测试本身视为缺陷。

### 运行、性能与安全

对可部署、暴露或昂贵的流程，先定义可观察的结果和预算，例如 p95 延迟、错误率、队列年龄、外部调用数、内存或成本；优化前后都要测量。日志和指标必须脱敏且控制标签基数；告警需要明确 owner、阈值和处置方式，而不是对每个异常报警。

安全审查按风险比例覆盖信任边界、服务端认证和授权、租户/资源所有权、输入验证、Secret、敏感数据、滥用路径和审计。AI 在证据不足时要保留 `unknown`，通过监控、最小复现或可回滚保护继续推进，而不是把猜测写成事实。对标记为根因修复的复杂故障，还要写明第一个偏离不变量的责任决策点，并以只改变该候选、保持相邻输入和依赖不变的反事实实验记录预期与实际结果；只隐藏 UI、日志或告警症状的修改只能称为缓解，不能称为根因修复。

### 交付、迁移与仓库卫生

这部分只在触发时执行：Level 0 不触发；Level 1 记录决定并运行最窄的已有检查；Level 2 才要求完整计划、独立审查和可复核证据。它不指定 Git 平台、CI、部署系统、迁移框架或 Secret 服务，只要求复用项目已有能力并证明结果。

- Git 改动按一个可验证的逻辑行为形成一个原子 commit，不把无关编辑、密钥或凭据混入；共享仓库的 PR 要写范围、验收、风险、回滚和验证，CI 是最低合并门槛。
- 发布、Feature Flag 和操作配置变更要有 owner、观察指标、停止条件、回滚与恢复路径；高影响改动应有回滚演练或测试。
- Schema、回填和数据格式演进采用 Expand-Migrate-Contract：兼容新增、迁移/回填、切换读写、最后清理旧状态；破坏性工作验证备份/恢复。
- 配置和 Secret 明确 owner、默认值、优先级、环境范围、校验和访问/轮换策略；依赖变更记录必要性、替代方案、lockfile/传递影响、维护/许可/安全信号与移除条件。
- 非显然决策保留 ADR，公开行为更新变更说明，高风险操作提供 runbook；环境敏感或新人常用流程要能用既有工具在最小非敏感配置下重现。

每项都以实际的 diff、提交 ID、CI、迁移演练、配置校验、扫描、文档审查或运行指标作为证据。不要为了满足规范虚构分支、PR、发布或演练；外部执行权不在当前任务时，应交付完整计划和证据而非擅自执行。

当一个 Level 2 请求把原因不明的故障与三类以上交付动作混在一起时，Skill 会启用“复合门槛”：逐项标记立即缓解、拆分后续或等待证据，不能让紧急修复把 API、迁移、Secret、依赖和发布塞进同一个 PR。它要求支付未知结果保留 pending 并对账、迁移分阶段、Flag 先关闭再灰度、CI 不可绕过、Secret/供应链/运行手册/最小非敏感夹具都有明确证据。迁移计划还必须给出实际的停止指标与阈值（或明确阻塞），本地复现必须落到夹具、干净环境及已发现的启动/检查/测试工具，且必须明确拒绝红 CI 的 force-merge；账本中必须单列运行知识和可复现性决策。

当 Skill 本身的 Level 2 更新同时跨越三类以上治理边界时，包内自测还会执行复合陷阱前向测试：测试 Agent 被明确限制为只读取原始场景和 Skill，评分规则与危险变异测试独立保存，避免“看答案作答”。提示词、允许输入、Skill/评分器哈希和运行限制都会存证；没有外部沙箱时，这只能称为“协议隔离”，不能夸大为文件系统级隔离。

### 外部缺陷基准验证

包内还保留了一次真实 GitHub 基准的可审计运行：[QuixBugs `shortest_paths` 固定提交清单](./examples/external-quixbugs-run-manifest.json)、[基线输出](./examples/external-quixbugs-baseline-output.md)、[Skill 复测输出](./examples/external-quixbugs-skill-output.md) 和[独立验证结果](./examples/external-quixbugs-evaluation.json)。两组都把公开 `3` 个失败和两个有效隐藏输入修复为通过，因此这个单一样本**不能**宣称 Skill 提升了修复成功率；可观察到的差异是 Skill 组留下了可证伪假设、区分性检查、不变量、输入不变性检查和结论等级，并以更小的改动范围完成同一修复。

修复 Agent 的夹具严格排除 `correct_python_programs`、上游 Git 元数据和评分工件；两个 Agent 结束后，独立验证器才读取固定参考实现来执行差分检查。`tests/test_external_quixbugs_replay.py` 还从提交的公开源、测试和两个候选快照重放 `3` 个失败、`3` 个公开通过和每个候选的 `2` 个隐藏差分用例，并校验它们的 SHA-256。原生子代理没有文件系统级隔离，所以这仍只称为协议隔离。`BugsInPy`、`Defects4J`、`Bugs.jar`、`Codeflaws` 与 `BugSwarm` 的本轮阻塞原因同样记录在结果中；没有把缺少工具链或依赖的情况伪装成“失败样本”。QuixBugs 的缺陷刻意较小，不能作为跨服务、迁移、发布或生产因果能力的证明。

另有 Pallets Click 的真实符号链接回归 [#1921](https://github.com/pallets/click/issues/1921) 的离线回放协议。[固定清单](./examples/external-click-run-manifest.json) 分别锁定 `8.0.1` 的缺陷版本和官方修复提交；[回放器](./scripts/replay_external_click.py) 不联网，只接受本地已 materialize 的两份源码并校验每个 `src/click` 树和 `types.py` 的 SHA-256。测试子进程从中立临时目录运行，只能导入验证后的 `click` 副本，并有十秒超时。它运行来自上游 `test_symlink_resolution` 的公开边界测试，并以独立隐藏契约验证 `os.access` 针对已解析目标而不是原始 symlink。评分包含原始缺陷、一个“只修路径解析”的近似补丁、仅改真正 owner 的官方补丁和官方补丁提交：近似补丁通过公开测试却被隐藏测试拒绝，官方两种修复都通过。运行记录在 [external-click-replay.json](./examples/external-click-replay.json)。

准备两个精确版本的本地源码后，可复跑：

```bash
git clone https://github.com/pallets/click.git /tmp/click-8.0.1
git -C /tmp/click-8.0.1 checkout baea6233ea2f5b6c40f40edde6e297e25e3d2b94
git clone https://github.com/pallets/click.git /tmp/click-official-patch
git -C /tmp/click-official-patch checkout 986f322e435fac5e1fb8505d3683c8a224c18b06
PYTHONDONTWRITEBYTECODE=1 python3 scripts/replay_external_click.py \
  --bug-root /tmp/click-8.0.1 \
  --patch-root /tmp/click-official-patch
```

该协议证明的是“这个测试结构能抓住这一类浅层修复”，不是模型修复成功率、一般因果能力、Windows 行为或生产安全的统计证明。

### Skill 效果的统计检验

前述案例是机制和回归保障，不是“模型整体提升”的证据。要测量 Skill 是否实际提升修复成功率，本仓库提供了可预注册的成对实验分析器：[模板](./examples/skill-effect-preregistration.json)、[分析器](./scripts/analyze_skill_effect.py) 和[完整协议](./references/effect-evaluation.md)。它固定模型、Harness、Skill 修订、任务语料和隐藏评分器；每个任务分别运行无 Skill 与有 Skill 的条件，随机化先后顺序，隐藏评分器不看条件标签。

当任务给出超时、延迟、内存、调用次数或成本预算时，公开用例通过仍不是完成证据。Skill 要求检查可见最大输入、估算最坏资源复杂度，并运行一个不越过声明契约的确定性边界探针；如果契约没有安全上界，只能记录预算未验证和剩余风险，不能把隐藏规模当作已知事实。

主指标是隐藏修复契约的通过率，重复运行按任务聚类，不能把同一个任务的多次尝试伪装成多个样本。分析器用分层 task-cluster bootstrap 给出 95% 区间，用配对 sign-flip 随机化检验判断提升；只有预注册任务数达标、下界高于实际收益门槛且随机化检验通过时，才报告 `improved`。否则只报告 `inconclusive` 或 `no_demonstrated_improvement`。

v4 是首个 metadata 有效、完整采样的 20-task QuixBugs paired run：40/40 trial 完整且未越权，baseline 与 Skill 都通过 18/20 个隐藏修复契约，效应为 `0.0`，95% 区间 `[0.0, 0.0]`，配对随机化 p 值为 `1.0`，结论为 `no_demonstrated_improvement`。这个结果不能支持修复成功率或整体因果能力提升的说法；`longest_common_subsequence` 的“任一最长子序列均有效”与固定字符串 scorer 不一致，也作为 v4 的 scorer 限制保留。

为避免针对 v4 hidden cases 调参，后续 v5 使用独立的 22-task synthetic resource-trap corpus：每个 fixture 都有公开可见的故障，隐藏 scorer 保留不在 repair workspace 中的大规模或边界契约；多解输出不进入这一轮。v5 在 trial 前固定 Skill、generator、manifest、scorer、prompt、seed、随机化顺序和统计门槛。它仍只会给出固定 model/Harness/Skill/corpus/scorer 范围内的结论，不能证明任意模型或生产系统的整体因果能力。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/analyze_skill_effect.py \
  examples/skill-effect-preregistration.json
```

原生 Codex 子代理共享文件系统时仅能称为协议隔离；要让该结论更强，需要独立 worktree 或容器、独立保存的 prompt/output 和与条件标签隔离的评分器。即使满足这些条件，结论也只适用于预注册范围，不能外推到所有模型、仓库或生产系统。

### 多模块因果探针

[`causal-probe-fixture`](./examples/causal-probe-fixture) 用发送超时、队列确认、持久化 ledger、供应商对账、租户身份和下游仪表盘组成一个可重放的多模块回归。评分器只允许改动 dispatcher，并拒绝测试篡改；隐藏契约要求“对账未知时保持 pending、完整操作身份包含租户、仅在明确不存在时重发”。基线与 Skill 组都通过 `4` 个公开和 `3` 个隐藏测试，因此它**不能**证明修复成功率提升。可观察差异仅在过程证据：Skill 组记录了替代假设、发布时间线、首个偏离不变量的 causal owner、反事实干预与明确结论；这一项由 [`tests/test_causal_probe_forward.py`](./tests/test_causal_probe_forward.py) 固化。该本地夹具仍不是实际队列、供应商、数据库或生产发布的证明。

### 机器可读证据模式

默认情况下，证据台账保留在 AI 的任务记录和完成报告中，适合个人项目和轻量改动。需要硬约束时，仓库可显式启用 `.adam/` 目录；此时每个 Level 1 或 Level 2 逻辑改动都要新增唯一的 `.adam/evidence/<change-id>.json`。只有在同一分支或 PR 延续该改动时才能更新它。

证据文件记录唯一实现路径、验收条件、旧路径处理、保障措施、验证命令、兼容或回滚策略和独立复查结果。随附的标准库脚本会验证字段完整性，并可在 CI 中要求“代码改动必须同时包含证据工件”。

按当前规范新建的工件，还应在 `quality_decisions` 中记录适用的设计边界、依赖与扩展决策、数据所有权、错误模型、契约演进、运行预算、威胁边界，以及 Git/PR、发布恢复、迁移、配置/Secret、依赖供应链、运行知识和可复现环境决策；每项都要说明已采用或不适用的理由。旧工件保持兼容，但不能据此跳过新改动的适用决策。前测或独立复查若支撑结论，应用 `supporting_artifacts` 记录本地报告或命令输出的相对路径与 SHA-256，避免“已测试”只有文字断言。

这不是用 JSON 替代测试。JSON 只说明应该验证什么和已经运行了什么；测试、静态检查、审查和 CI 仍然负责证明结论。

## 安装

### 方式一：安装到 Codex 全局 Skill 目录

```bash
cd ~/.codex/skills
git clone https://github.com/AdamFangKK/adam-development-habits.git
```

重启或新建 Codex 任务后，Skill 会出现在可用 Skill 列表中。

### 方式二：作为项目约定使用

将本仓库中的 `SKILL.md` 复制到团队约定的 Skill 目录，并在项目的 `AGENTS.md` 中要求所有代码改动使用该 Skill。这样可让项目规则与个人开发习惯同时生效。

## 使用方式

在开发任务中显式调用最可靠：

```text
Use $adam-development-habits to add order cancellation.
```

也可以直接用自然语言提出开发、修复、重构、集成或代码审查任务；Skill 的描述覆盖这些场景，Codex 会在匹配时加载它。

显式调用适合重要功能、跨模块改动、重构和上线前修复。它能避免任务描述过短时没有命中 Skill。

## 内置工程保障

Skill 不会对所有项目强行堆基础设施，而是根据行为类型选择需要的保障：

| 场景 | 默认要求 |
|---|---|
| 服务入口请求 | 结构化日志，包括服务、环境、版本、操作名、`traceId`、耗时和结果。 |
| 跨服务或异步流程 | 透传 `traceId`；按需使用 `spanId` 和 `correlationId`。 |
| 可变业务或个人数据 | 权威 owner、状态转换、访问/保留/删除边界和脱敏要求。 |
| API、事件、共享库或配置入口 | 参数、范围、权限、资源归属与载荷大小校验；稳定错误码、消费者、兼容、迁移和回滚策略。 |
| 数据库、缓存、HTTP 或 SDK 调用 | 明确超时、取消和 deadline；分类可重试、终态和未知结果；记录脱敏的依赖和耗时。 |
| 可重试的远程操作 | 仅对幂等的短暂故障重试，限制次数并使用退避和抖动。 |
| 创建、更新、扣费、发送或入队 | 幂等键、唯一约束或同等保证；事务或明确一致性设计。 |
| 关键规则或广输入空间 | 业务不变量、失败/兼容/边界值和性质或表驱动测试；控制时间、随机数、并发和外部 I/O。 |
| 高消耗或暴露接口 | 延迟/资源/成本预算和基线；分页、请求体上限、限流、取消、并发控制与背压。 |
| 敏感或特权操作 | 信任边界、服务端认证/授权、资源归属、输入验证、Secret、审计、滥用路径和脱敏。 |
| 可部署服务 | 健康/就绪检查、低基数请求/错误/延迟指标、可行动告警与环境化配置。 |
| 数据库或 API 演进 | 消费者识别、版本化迁移、向后兼容、回滚和迁移/契约测试。 |

### `traceId`、`spanId` 与 `correlationId`

- `traceId`：标识一次请求的完整生命周期，用于把网关、服务、数据库和异步任务的日志串联起来。
- `spanId`：标识这条调用链中的一个具体步骤，例如一次数据库查询或 RPC 调用。
- `correlationId`：关联跨请求的业务流程，例如下单、支付、发货的异步消息链路。

这些标识不应携带用户隐私、密码、Token 或业务敏感内容。

## 完成门槛

完整完成门槛以 [`SKILL.md` 的 Non-Negotiable Completion Gate](./SKILL.md#non-negotiable-completion-gate) 为准。对于 Git 仓库，至少应运行：

```bash
git diff --check
```

再运行项目已有的 formatter、lint、类型检查、测试、构建和静态分析命令。检查失败或无法执行时，必须说明原因与残余风险，不能标记为“已完全验证”。

## 让规则真正生效

Skill 能提高 AI 的执行一致性，但它不是 CI，也不能从技术上阻止模型跳过命令。要达到接近强制的效果，请使用三层保障：

```text
Skill：规定 AI 的开发、清理和验证流程
AGENTS.md：让该项目的每次代码任务都必须遵守流程
CI：对 lint、类型检查、测试和构建实施真实阻断
```

可在项目 `AGENTS.md` 中加入类似约束：

```text
For every non-trivial code change, use $adam-development-habits.
Do not claim completion without the evidence ledger and executed verification results.
```

CI 应至少覆盖项目已有的格式化、静态检查、类型检查、测试和构建命令。不要在 CI 中用临时跳过、忽略错误或降低阈值的方式绕开失败。

当用户明确要求把规范变成自动化约束时，Skill 会读取 [执行适配参考](./references/enforcement.md)，先识别项目现有工具，再按需选择：JavaScript/TypeScript 的 `Knip`、多语言规则检查的 `Semgrep`、本地 Hook 的 `pre-commit`，或团队级质量门。它不会擅自安装任何依赖或接入外部服务。

仓库启用机器可读证据模式时，可使用 [证据示例](./assets/evidence-ledger.example.json)、[字段校验器](./scripts/validate_evidence.py)、[行为改动门禁](./scripts/check_change_evidence.py) 和 [GitHub Actions 模板](./assets/github-actions/adam-evidence-gate.yml)。门禁同时覆盖源码与常见运行时配置（JSON、YAML、TOML、依赖清单、CI、API 合约），避免只改配置就绕过验证；文档、示例和测试夹具目录不会触发。证据文件须命名为 `.adam/evidence/<change-id>.json`，并与内容中的 `change_id` 一致。

## 自我维护与当前状态

这个 Skill 自身已经启用 `.adam/` 证据模式，并运行仓库内的质量工作流。它也遵守同一套规则：修改策略、脚本、模板、参考资料或本 README 时，必须同步更新相关内容、删除旧路径并留下验证证据。

不维护会过期的“最新日期”或手写版本号。发布状态以 GitHub 默认分支的最新提交和通过的工作流为准；本地可用以下命令核对：

```bash
git fetch origin main
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

仓库内工作流会验证每个 PR 和对 `main` 的推送。若要阻止未通过验证的改动合并，还必须在 GitHub 的 `main` 分支保护中将 `Verify Adam Development Habits` 设为必需检查；这是平台设置，不能由仓库文件自行强制。

## 个性化你的规范

编辑 [`SKILL.md`](./SKILL.md) 中的 `Adam's Project Overrides` 部分，可以加入个人或团队特有的、可验证的规则。例如：

```text
Require a feature flag and rollback path for changes that alter a core user workflow.
Do not write user conversation content to ordinary logs.
Require a migration and rollback plan for production schema changes.
```

通用规则正文保持英文，有助于技术术语、代码模式和工具指令保持稳定；项目专属约束可按团队语言维护。

## 目录结构

```text
adam-development-habits/
├── SKILL.md             # Codex 实际执行的开发习惯规则
├── README.md            # 本说明文档
├── LICENSE              # MIT License
├── assets/
│   ├── evidence-ledger.example.json
│   └── github-actions/adam-evidence-gate.yml
├── .adam/
│   └── evidence/
│       └── self-application-maintenance.json
├── .github/
│   └── workflows/
│       └── skill-quality.yml
├── scripts/
│   ├── check_change_evidence.py
│   └── validate_evidence.py
├── references/
│   └── enforcement.md    # Hook、CI 与静态检查的选择和接入原则
└── agents/
    └── openai.yaml      # Codex 界面显示与默认调用提示
```

## 贡献

欢迎提交能提高执行确定性、减少 AI 代码冗余或增强验证证据的改进。通用规则应保持框架无关、短小且可执行；技术栈特定的强制检查更适合放在项目自身的 `AGENTS.md`、脚本或 CI 中。

## 许可证

本项目采用 [MIT License](./LICENSE) 开源。
