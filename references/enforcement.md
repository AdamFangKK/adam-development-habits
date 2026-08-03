# Enforcement Reference

Read this reference only when asked to add, configure, or review automated quality enforcement for a repository. Keep the policy framework-neutral; choose tools from the project's existing stack before proposing new ones.

## Enforcement Layers

| Layer | Purpose | Rule |
|---|---|---|
| Skill | Require reasoning, evidence, cleanup, and risk-aware decisions. | Never treat it as mechanical enforcement. |
| Repository instructions | Make the workflow mandatory for that repository. | Reference `$adam-development-habits` from `AGENTS.md` or its equivalent. |
| Local hooks | Give fast feedback before a commit. | Keep hooks focused and fast enough for daily use. |
| CI | Block unverified changes from merging or releasing. | Mirror the required local checks and do not allow bypasses. |

## Select the Smallest Compatible Toolchain

| Need | Candidate | Use when | Constraint |
|---|---|---|---|
| Formatting, lint, type check, tests | Existing project commands | Always prefer these first. | Do not replace working tooling without a reason. |
| Pre-commit orchestration | `pre-commit` | The repository needs multi-language local hooks. | Hooks can be bypassed; retain CI gates. |
| Unused JS/TS code | `Knip` | The project is JavaScript or TypeScript and needs unused-file/export/dependency detection. | Review dynamic imports and convention-based loading before deletion. |
| Custom multi-language patterns | `Semgrep` | A repeated unsafe pattern should become a machine rule. | Start with a few high-confidence rules to avoid alert fatigue. |
| Organization-wide quality gates | SonarQube or an existing platform equivalent | A team needs dashboards, historical trends, and merge gates. | Assess infrastructure and maintenance cost first. |

Do not install any candidate automatically. First identify the project's language, package manager, existing scripts, CI provider, and current quality checks. Obtain explicit approval before adding a new dependency or external service.

## CI Conformance Checklist

For a repository that has the relevant capabilities, require these checks in CI:

```text
format check
lint
type check
unit and integration tests
build
static analysis or stale-code scan
```

Keep the command names identical or intentionally equivalent between local development and CI. Do not suppress failures with ignore flags, broad exclusions, lowered thresholds, or temporary bypasses without recording the reason, scope, expiry, and remediation task.

## Repository Instruction Template

```text
For every Level 1 or Level 2 code change, use $adam-development-habits.
Do not claim completion without acceptance criteria, an evidence ledger, cleanup evidence, and executed verification results.
Keep local hooks and CI quality gates aligned. Do not bypass failing checks.
```
