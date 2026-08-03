# Adam's Development Habits

> 面向 AI 辅助开发的工程质量 Skill：要求每次改动都有唯一实现路径、清理证据、必要的稳定性保护和真实验证结果。

`Adam's Development Habits` 是一个适用于 Codex 的开发习惯 Skill。它不绑定语言、框架或云平台，目标是解决 AI 持续迭代代码时最常见的工程问题：新代码不断增加，旧实现、旧配置、旧路由和旧测试却没有被清理，最终导致重复逻辑、耦合增长和错误上下文。

## 它解决什么问题

AI 可以很快地完成局部需求，但在多轮修改后容易出现以下情况：

- 新旧业务实现并存，调用方分散在两套路径中；
- 修改组件或接口后，旧的路由、配置、Feature Flag、类型和测试仍然保留；
- 捕获异常后静默忽略，线上故障难以定位；
- 网络调用没有超时、重试或幂等设计，重复请求造成重复写入；
- AI 只说“应该能运行”，却没有真正执行测试、类型检查和构建；
- 日志缺少 `traceId`、版本和错误码，出了问题无法复盘。

这个 Skill 将这些风险变成每次开发都要经过的检查门槛。

## 核心能力

| 能力 | 作用 |
|---|---|
| 单一有效实现 | 先定位行为的唯一负责人，优先原地修改，避免新增平行实现。 |
| 替换即清理 | 新实现替换旧实现时，同一改动中迁移调用方并删除旧代码、引用、配置、测试和文档。 |
| 改动证据台账 | 在编辑前说明实现入口、受影响调用方、行为不变量、兼容策略和验证计划。 |
| 企业级横切检查 | 根据场景检查 `traceId`、结构化日志、超时、重试、幂等、限流、鉴权、审计和健康检查。 |
| 清理审计 | 在完成前检查未使用文件、导入、导出、类型、路由、任务、队列、配置和 Feature Flag。 |
| 验证门槛 | 要求实际运行相关的格式化、lint、类型检查、测试、构建和静态分析。 |
| 真实完成报告 | 以已运行命令及结果作为证据，不允许用“应该可以”代替验证。 |

## 工作方式

Skill 不是自动修改代码的脚本，而是一份会在 AI 执行开发任务时加载的严格工作流。它会引导 AI 按以下顺序工作：

```text
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

对于非简单改动，Skill 会要求维护一份证据台账：

```text
Canonical owner: <实际入口文件与符号 / 路由>
Affected callers/contracts: <受影响调用方或公开契约>
Invariant: <必须保持为真的行为>
Replaced paths: <需要删除的旧路径，或 none>
Retained compatibility: <保留原因、消费者、删除条件与测试，或 none>
Safeguards: <适用的稳定性与可观测性措施>
Verification: <已执行命令及实际结果>
```

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
| 所有请求 | 结构化日志，包括服务、环境、版本、操作名、`traceId`、耗时和结果。 |
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

Skill 明确禁止在缺少下列证据时声称任务完成：

1. 已定位唯一有效实现及受影响调用方。
2. 已删除所有被替换的路径，或说明保留旧路径的消费者、删除条件和测试。
3. 已实现相关保障措施，或明确解释为什么不适用。
4. 已执行验证命令并阅读结果。
5. 已报告修改文件、删除内容、验证证据和剩余风险。

对于 Git 仓库，至少应运行：

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
└── agents/
    └── openai.yaml      # Codex 界面显示与默认调用提示
```

## 贡献

欢迎提交能提高执行确定性、减少 AI 代码冗余或增强验证证据的改进。通用规则应保持框架无关、短小且可执行；技术栈特定的强制检查更适合放在项目自身的 `AGENTS.md`、脚本或 CI 中。

## 许可证

本项目采用 [MIT License](./LICENSE) 开源。
