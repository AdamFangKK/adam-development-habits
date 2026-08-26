#!/usr/bin/env python3
"""Require validated evidence artifacts for behavior-changing Git files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from validate_evidence import load_json, validate_evidence


CODE_SUFFIXES = {
    ".c", ".cc", ".cjs", ".cpp", ".cs", ".cts", ".dart", ".ex", ".exs", ".fs", ".fsx",
    ".go", ".h", ".hpp", ".java", ".js", ".jsx", ".kt", ".kts", ".lua", ".mjs", ".mts",
    ".php", ".pl", ".ps1", ".py", ".r", ".rb", ".rs", ".scala", ".sh", ".sql", ".swift",
    ".css", ".gradle", ".hbs", ".html", ".less", ".mdx", ".scss", ".ts", ".tsx", ".vue", ".xml", ".zig",
}

# These formats commonly define runtime behavior, public contracts, dependencies, or CI.
# Treating them like source avoids a configuration-only route around the evidence gate.
BEHAVIORAL_CONFIG_SUFFIXES = {
    ".bicep", ".cfg", ".conf", ".gql", ".graphql", ".hcl", ".ini", ".json", ".nix",
    ".properties", ".proto", ".tf", ".tfvars", ".toml", ".yaml", ".yml",
}
BEHAVIORAL_CONFIG_NAMES = {
    "Brewfile", "BUILD", "CMakeLists.txt", "Cargo.lock", "Cargo.toml", "Dockerfile", "Gemfile",
    "Gemfile.lock", "Jenkinsfile", "Justfile", "Makefile", "Pipfile", "Pipfile.lock", "Procfile",
    "Vagrantfile", "WORKSPACE", "build.gradle", "build.gradle.kts", "composer.json", "composer.lock",
    "go.mod", "go.sum", "package.json", "poetry.lock", "pom.xml", "pyproject.toml", "requirements.txt",
}
BEHAVIORAL_SCRIPT_DIRECTORIES = {"bin", "deploy", "ops", "script", "scripts", "tool", "tools"}
HIGH_RISK_DIRECTORIES = {
    "auth", "authorization", "billing", "config", "deploy", "infra", "migration", "migrations",
    "money", "oauth", "payment", "payments", "permission", "permissions", "queue", "rbac",
    "release", "schema", "secret", "secrets", "security", "terraform", "worker", "workers",
}
HIGH_RISK_SUFFIXES = {".bicep", ".env", ".hcl", ".proto", ".tf", ".tfvars"}
HIGH_RISK_NAMES = {
    ".env", "dockerfile", "docker-compose.yml", "docker-compose.yaml", "openapi.yaml", "openapi.yml",
    "schema.graphql", "schema.gql", "secrets.yaml", "secrets.yml",
}
NON_RUNTIME_DIRECTORIES = {
    "doc", "docs", "documentation", "example", "examples", "fixture", "fixtures", "sample", "samples",
    "test-data", "testdata",
}


def changed_files(base: str) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMR", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line]


def is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_SUFFIXES


def is_extensionless_script(path: Path, base: str) -> bool:
    if path.suffix:
        return False
    if any(part.lower() in BEHAVIORAL_SCRIPT_DIRECTORIES for part in path.parts[:-1]):
        return True
    try:
        return path.read_bytes()[:2] == b"#!"
    except OSError:
        result = subprocess.run(
            ["git", "show", f"{base}:{path.as_posix()}"],
            check=False,
            capture_output=True,
        )
        return result.returncode == 0 and result.stdout[:2] == b"#!"


def is_documentation_or_fixture(path: Path) -> bool:
    return any(part.lower() in NON_RUNTIME_DIRECTORIES for part in path.parts[:-1])


def requires_evidence(path: Path, base: str) -> bool:
    if is_documentation_or_fixture(path):
        return False
    return (
        is_code_file(path)
        or is_extensionless_script(path, base)
        or path.suffix.lower() in BEHAVIORAL_CONFIG_SUFFIXES
        or path.name in BEHAVIORAL_CONFIG_NAMES
        or requires_level_two(path)
    )


def requires_level_two(path: Path) -> bool:
    """Conservatively upgrade paths whose names imply irreversible or privileged behavior."""
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return (
        bool(parts.intersection(HIGH_RISK_DIRECTORIES))
        or path.suffix.lower() in HIGH_RISK_SUFFIXES
        or name in HIGH_RISK_NAMES
        or name.startswith(".env.")
    )


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def normalize_evidence_dir(evidence_dir: Path, root: Path) -> Path:
    if not evidence_dir.is_absolute():
        return evidence_dir
    try:
        return evidence_dir.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError("--evidence-dir must be inside the current Git repository") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="Check behavior-changing files for validated evidence artifacts.")
    parser.add_argument("--base", required=True, help="Git base revision for comparison")
    parser.add_argument("--evidence-dir", type=Path, default=Path(".adam/evidence"))
    parser.add_argument("--require-for-code-change", action="store_true")
    parser.add_argument(
        "--require-level-two-for-high-risk",
        action="store_true",
        help="Require at least one changed evidence artifact at level 2 for high-risk paths.",
    )
    args = parser.parse_args()

    try:
        root = repository_root()
        evidence_dir = normalize_evidence_dir(args.evidence_dir, root)
        changed = changed_files(args.base)
    except subprocess.CalledProcessError as error:
        print(error.stderr.strip() or "could not determine Git paths", file=sys.stderr)
        return 2
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    evidence_prefix = evidence_dir.as_posix().rstrip("/") + "/"
    artifacts = [
        path
        for path in changed
        if path.as_posix().startswith(evidence_prefix) and path.suffix == ".json" and path.exists()
    ]
    behavior_changes = [path for path in changed if requires_evidence(path, args.base)]

    if args.require_for_code_change and behavior_changes and not artifacts:
        print("behavioral changes require a changed .adam/evidence JSON artifact", file=sys.stderr)
        return 1

    failed = False
    schema_v2_artifact_levels: list[int] = []
    for artifact in artifacts:
        try:
            payload = load_json(artifact)
            errors = validate_evidence(payload, expected_change_id=artifact.stem, artifact_root=root)
            if (
                not errors
                and isinstance(payload, dict)
                and payload.get("schema_version") == 2
                and isinstance(payload.get("level"), int)
            ):
                schema_v2_artifact_levels.append(payload["level"])
        except Exception as error:  # Report invalid artifacts without a stack trace in CI.
            errors = [str(error)]
        if errors:
            failed = True
            for error in errors:
                print(f"{artifact}: {error}", file=sys.stderr)
        else:
            print(f"valid changed evidence: {artifact}")

    if args.require_for_code_change and behavior_changes and not schema_v2_artifact_levels:
        failed = True
        print(
            "behavioral changes require at least one valid changed schema_version 2 evidence artifact",
            file=sys.stderr,
        )

    high_risk_changes = [path for path in behavior_changes if requires_level_two(path)]
    if args.require_level_two_for_high_risk and high_risk_changes and 2 not in schema_v2_artifact_levels:
        failed = True
        names = ", ".join(path.as_posix() for path in high_risk_changes)
        print(
            "high-risk behavioral changes require at least one schema_version 2 level 2 evidence artifact: " + names,
            file=sys.stderr,
        )

    if not behavior_changes:
        print("no behavior-changing files changed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
