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

## Structured Evidence Mode

Enable this mode only when the repository owner wants CI-verifiable AI development evidence. Copy these resources from the skill package into the target repository:

```text
.adam/evidence/<change-id>.json
.adam/scripts/validate_evidence.py
.adam/scripts/check_change_evidence.py
.github/workflows/adam-evidence-gate.yml
```

Use `assets/evidence-ledger.example.json` as the artifact template and `assets/github-actions/adam-evidence-gate.yml` as the workflow template. New artifacts authored under the current policy record applicable boundary, data, error, contract, operational, threat, delivery lifecycle, release/recovery, migration, configuration/secret, dependency, operational-knowledge, and reproducibility decisions in `quality_decisions`; attach a hash-verified `supporting_artifacts` entry when a forward test or independent review supports a claim. Keep the scripts unmodified unless the repository has a documented reason to extend the schema. Create one unique artifact for each logical change; update it only while continuing that same change in the same branch or pull request.

The evidence gate validates artifacts changed in the pull request. With `--require-for-code-change`, it fails when source files or common behavior-defining configuration files change but no evidence artifact changes with them. This conservatively includes JSON, YAML, TOML, API contract files, dependency manifests, and CI configuration. Files under documentation, example, and fixture directories do not trigger it. The artifact filename must match its `change_id`, so use `.adam/evidence/<change-id>.json`.

When an artifact has a `causal` block, each hypothesis must reference a declared evidence artifact ID. Each declared artifact has a repository-relative file path, a SHA-256 digest, a kind, and a summary. The validator rejects undeclared IDs, path traversal, missing files, and digest mismatches. A `root_cause_fix` must cite a supported hypothesis with an execution artifact (`command_output`, `test_output`, or `trace_export`); a `test_source` alone is insufficient. For generated reports, run the producing command in CI and compare its output with the tracked report before accepting it as evidence. This makes evidence references auditable and detects stale local artifacts, but it still cannot prove that a human-written summary is true; retain tests, reviews, CI logs, and production telemetry as the source of factual proof.

## Technology Presets

Treat a preset as a decision aid, not an installation command. First run the project's existing commands.

| Stack | Baseline checks | Optional enforcement gap |
|---|---|---|
| JavaScript/TypeScript | formatter, lint, type check, unit tests, build | Use `Knip` for unused files, exports, and dependencies after reviewing dynamic loading. |
| Python | formatter, lint, type check, tests | Add a narrowly configured static rule or unused-code tool only when the existing toolchain misses a repeated issue. |
| Go | formatting, `go vet`, tests, existing static analysis | Prefer existing module and CI conventions before adding a linter bundle. |
| JVM/.NET/Rust | formatter, compiler/type checks, tests, existing analyzers | Use the ecosystem's established analyzer rather than importing a generic linter suite by default. |

## CI Conformance Checklist

For a repository that has the relevant capabilities, require these checks in CI:

```text
format check
lint
type check
unit and integration tests
build
static analysis or stale-code scan
existing secret/dependency scan when the change triggers it
```

Keep the command names identical or intentionally equivalent between local development and CI. Do not suppress failures with ignore flags, broad exclusions, lowered thresholds, or temporary bypasses without recording the reason, scope, expiry, and remediation task.

For repositories that deploy or migrate data, use existing release/migration controls to retain rollout, stop-condition, rollback, dry-run, and backup/restore evidence. Do not add a release platform, migration framework, scanner, or secret manager merely to satisfy this reference.

## Repository Instruction Template

```text
For every Level 1 or Level 2 code change, use $adam-development-habits.
Do not claim completion without acceptance criteria, an evidence ledger, cleanup evidence, and executed verification results.
Keep local hooks and CI quality gates aligned. Do not bypass failing checks.
```
