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

Use `assets/evidence-ledger.example.json` as the schema-version-2 artifact template and `assets/github-actions/adam-evidence-gate.yml` as the workflow template. Version 2 requires the full `quality_decisions` set; hash-linked output bound to the same command, successful exit code, UTC execution timestamp, and repository revision for every passed verification; and a hash-linked report from a reviewer independent of the implementer for Level 2 approval. Keep version 1 only for pre-existing historical evidence: it may validate on its own but cannot satisfy the changed-evidence gate for new behavioral work. A historical supporting artifact may name the full Git commit whose file bytes match its recorded digest; current evidence stays bound to the worktree. Keep the scripts unmodified unless the repository has a documented reason to extend the schema. Create one unique artifact for each logical change; update it only while continuing that same change in the same branch or pull request.

The evidence gate validates artifacts changed in the pull request. With `--require-for-code-change`, it fails when source files or common behavior-defining configuration files change but no evidence artifact changes with them. This conservatively includes application code, HTML/CSS/preprocessor/template files, JSON, YAML, TOML, API contract files, dependency manifests, and CI configuration. Files under documentation, example, and fixture directories do not trigger it. Add `--require-level-two-for-high-risk` so obvious authentication, authorization, payment, migration, schema, secret, deployment, infrastructure, queue, and worker paths require at least one valid changed Level 2 artifact. This filename classifier is a lower bound, not a semantic risk proof. The artifact filename must match its `change_id`, so use `.adam/evidence/<change-id>.json`.

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
Author new machine evidence with schema_version 2 and keep passed verification and Level 2 review outputs hash-linked.
```
