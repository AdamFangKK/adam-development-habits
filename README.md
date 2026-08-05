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

### 机器可读证据模式

默认情况下，证据台账保留在 AI 的任务记录和完成报告中，适合个人项目和轻量改动。需要硬约束时，仓库可显式启用 `.adam/` 目录；此时每个 Level 1 或 Level 2 逻辑改动都要新增唯一的 `.adam/evidence/<change-id>.json`。只有在同一分支或 PR 延续该改动时才能更新它。

证据文件记录唯一实现路径、验收条件、旧路径处理、保障措施、验证命令、兼容或回滚策略和独立复查结果。随附的标准库脚本会验证字段完整性，并可在 CI 中要求“代码改动必须同时包含证据工件”。

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
| API 或公开入口 | 参数、范围、权限、资源归属与载荷大小校验；稳定错误码。 |
| 数据库、缓存、HTTP 或 SDK 调用 | 明确超时；支持时透传 deadline；记录依赖和耗时。 |
| 可重试的远程操作 | 仅对幂等的短暂故障重试，限制次数并使用退避和抖动。 |
| 创建、更新、扣费、发送或入队 | 幂等键、唯一约束或同等保证；事务或明确一致性设计。 |
| 高消耗或暴露接口 | 分页、请求体上限、限流、并发控制与背压。 |
| 敏感或特权操作 | 服务端认证与授权、审计日志，以及敏感信息脱敏。 |
| 可部署服务 | 健康检查、就绪检查、请求/错误/延迟指标和环境化配置。 |
| 数据库或 API 演进 | 版本化迁移、向后兼容和上线前回滚方案。 |

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
