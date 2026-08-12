#!/usr/bin/env python3
"""Run the isolated, absolute-artifact V8 paired Skill-effect protocol."""

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable, Protocol, cast


DEFAULT_MODEL_ID = "gpt-5.6-terra"
DEFAULT_HARNESS_ID = "codex-cli-0.147.0-alpha.6.5;exec;workspace-write;ephemeral;skill-search-disabled;absolute-output;checkpointed-v8"
DEFAULT_CODEX = str(Path(__file__).with_name("codex_v8_isolated.py").resolve())
DEFAULT_AGENT_TIMEOUT_SECONDS = 420.0
DEFAULT_TEST_TIMEOUT_SECONDS = 30.0
CODEX_VERSION = "0.147.0-alpha.6.5"
VALUE_OPTIONS = frozenset({
    "--corpus", "--prompts", "--skill", "--preregistration", "--preregistration-commit",
    "--raw-output", "--output", "--seed", "--codex", "--model", "--harness",
    "--agent-timeout", "--test-timeout",
})
FLAG_OPTIONS = frozenset({"--preflight"})

class TaskReference(Protocol):
    hidden_root_path: str
    hidden_command: tuple[str, ...]


@dataclass(frozen=True)
class FrozenExecution:
    """Absolute staged paths consumed by the delegated paired runner."""

    arguments: list[str]
    script_root: Path


class RunnerRuntime(Protocol):
    DEFAULT_MODEL_ID: str
    DEFAULT_HARNESS_ID: str
    score_candidate: Callable[..., dict[str, object]]

    def environment(self) -> dict[str, str]: ...

    def main(self) -> int: ...


class IsolationRuntime(Protocol):
    def audit_collection(self, raw_root: Path, result_path: Path, skill_source: Path) -> dict[str, object]: ...


_runtime_protocol: RunnerRuntime | None = None
_runtime_isolation: IsolationRuntime | None = None
_runtime_script_root: Path | None = None


def load_module_from_path(module_name: str, path: Path) -> ModuleType:
    """Load one staged Python module without consulting the live worktree."""
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"could not load frozen V8 module: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def load_runtime_modules(script_root: Path | None = None) -> tuple[RunnerRuntime, IsolationRuntime]:
    """Load executable dependencies from the frozen archive after bootstrap validation."""
    global _runtime_isolation, _runtime_protocol, _runtime_script_root
    root = (script_root if script_root is not None else Path(__file__).resolve().parent).resolve()
    if _runtime_protocol is None:
        token = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
        prior_analyzer = sys.modules.get("analyze_skill_effect")
        try:
            analyzer = load_module_from_path(f"_adam_v8_analyzer_{token}", root / "analyze_skill_effect.py")
            sys.modules["analyze_skill_effect"] = analyzer
            _runtime_protocol = cast(
                RunnerRuntime,
                cast(object, load_module_from_path(f"_adam_v8_runner_{token}", root / "run_effect_experiment_v6.py")),
            )
            _runtime_isolation = cast(
                IsolationRuntime,
                cast(object, load_module_from_path(f"_adam_v8_isolation_{token}", root / "audit_effect_isolation_v8.py")),
            )
            _runtime_script_root = root
        finally:
            if prior_analyzer is None:
                _ = sys.modules.pop("analyze_skill_effect", None)
            else:
                sys.modules["analyze_skill_effect"] = prior_analyzer
    elif _runtime_script_root != root:
        raise RuntimeError("V8 runtime was already initialized from a different frozen source")
    if _runtime_isolation is None:
        raise RuntimeError("V8 runtime modules did not initialize")
    return _runtime_protocol, _runtime_isolation


def normalize_path_arguments(arguments: list[str]) -> list[str]:
    """Make every protocol path independent of the agent's temporary cwd."""
    path_flags = {"--codex", "--corpus", "--prompts", "--skill", "--preregistration", "--raw-output", "--output"}
    normalized: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        normalized.append(argument)
        if argument in path_flags:
            if index + 1 >= len(arguments):
                raise ValueError(f"{argument} requires a path")
            # Do not resolve here: the output gate must still be able to see a
            # caller-supplied symlink rather than only its destination.
            normalized.append(str(Path(arguments[index + 1]).expanduser().absolute()))
            index += 2
            continue
        index += 1
    return normalized


def v8_arguments(arguments: list[str]) -> list[str]:
    normalized = normalize_path_arguments(arguments)
    if "--codex" not in normalized:
        normalized[0:0] = ["--codex", DEFAULT_CODEX]
    if "--agent-timeout" not in normalized:
        normalized[0:0] = ["--agent-timeout", str(DEFAULT_AGENT_TIMEOUT_SECONDS)]
    if "--test-timeout" not in normalized:
        normalized[0:0] = ["--test-timeout", str(DEFAULT_TEST_TIMEOUT_SECONDS)]
    if "--model" not in normalized:
        normalized[0:0] = ["--model", DEFAULT_MODEL_ID]
    if "--harness" not in normalized:
        normalized[0:0] = ["--harness", DEFAULT_HARNESS_ID]
    return normalized


def validate_option_spelling(arguments: list[str]) -> None:
    """Ban argparse aliases so preflight and delegated execution see identical options."""
    seen: set[str] = set()
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in FLAG_OPTIONS:
            if argument in seen:
                raise ValueError(f"{argument} may appear at most once")
            seen.add(argument)
            index += 1
            continue
        if argument in VALUE_OPTIONS:
            if argument in seen:
                raise ValueError(f"{argument} must appear at most once")
            if index + 1 >= len(arguments):
                raise ValueError(f"{argument} requires a value")
            seen.add(argument)
            index += 2
            continue
        option = argument.split("=", 1)[0]
        if option.startswith("--") and any(expected.startswith(option) for expected in VALUE_OPTIONS | FLAG_OPTIONS):
            raise ValueError(f"{argument!r} is an abbreviated or equals-form V8 option; use its exact spelling")
        if argument.startswith("-"):
            raise ValueError(f"unknown V8 option {argument!r}")
        raise ValueError(f"unexpected V8 argument {argument!r}")


def required_option(arguments: list[str], name: str) -> str:
    """Read exactly one required option without accepting ambiguous overrides."""
    positions = [index for index, argument in enumerate(arguments) if argument == name]
    if len(positions) != 1:
        raise ValueError(f"{name} must appear exactly once")
    position = positions[0]
    if position + 1 >= len(arguments):
        raise ValueError(f"{name} requires a value")
    return arguments[position + 1]


def positive_number(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) <= 0:
        raise ValueError(f"{field} must be a positive number")
    return float(value)


def required_true(value: object, field: str) -> None:
    if value is not True:
        raise ValueError(f"{field} must be true")


def required_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
        raise ValueError(f"{field} must be a SHA-256 digest")
    return value


def file_digest(path: Path, label: str) -> str:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symbolic link")
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, object]:
    try:
        value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path} is not a readable JSON object: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def immutable_envelope(preregistration: dict[str, object]) -> dict[str, object]:
    required = ("scope", "protocol", "analysis", "task_plan", "stopping_rule")
    envelope: dict[str, object] = {}
    for field in required:
        value = preregistration.get(field)
        if not isinstance(value, dict):
            raise ValueError(f"V8 preregistration.{field} must be an object")
        envelope[field] = value
    return envelope


def tree_digest(root: Path) -> str:
    """Digest a regular-file tree while refusing source substitutions by symlink."""
    if root.is_symlink():
        raise ValueError(f"V8 corpus tree must not be a symbolic link: {root}")
    if not root.is_dir():
        raise ValueError(f"V8 corpus tree is missing: {root}")
    digest = hashlib.sha256()
    paths: list[Path] = []
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_symlink():
            raise ValueError(f"V8 corpus tree must not contain symbolic links: {path}")
        if path.is_file():
            paths.append(path)
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def validate_frozen_budget(preregistration: dict[str, object], arguments: list[str]) -> None:
    """Reject randomization or deadline drift before a paired condition starts."""
    protocol_value = preregistration.get("protocol")
    analysis_value = preregistration.get("analysis")
    if not isinstance(protocol_value, dict) or not isinstance(analysis_value, dict):
        raise ValueError("V8 preregistration must contain protocol and analysis objects")
    protocol = cast(dict[str, object], protocol_value)
    analysis = cast(dict[str, object], analysis_value)

    expected_seed = analysis.get("random_seed")
    if not isinstance(expected_seed, int) or isinstance(expected_seed, bool):
        raise ValueError("analysis.random_seed must be an integer")
    try:
        requested_seed = int(required_option(arguments, "--seed"))
    except ValueError as error:
        raise ValueError("--seed must be an integer") from error
    if requested_seed != expected_seed:
        raise ValueError("--seed differs from preregistration.analysis.random_seed")

    for option, field in (
        ("--agent-timeout", "agent_timeout_seconds"),
        ("--test-timeout", "test_timeout_seconds"),
    ):
        expected = positive_number(protocol.get(field), f"protocol.{field}")
        try:
            requested = float(required_option(arguments, option))
        except ValueError as error:
            raise ValueError(f"{option} must be a positive number") from error
        if requested <= 0:
            raise ValueError(f"{option} must be a positive number")
        if requested != expected:
            raise ValueError(f"{option} differs from preregistration.protocol.{field}")


def validate_bound_inputs(preregistration: dict[str, object], arguments: list[str]) -> None:
    """Verify every runtime-selectable V8 input against the frozen envelope."""
    protocol_value = preregistration.get("protocol")
    scope_value = preregistration.get("scope")
    if not isinstance(protocol_value, dict) or not isinstance(scope_value, dict):
        raise ValueError("V8 preregistration must contain protocol and scope objects")
    protocol = cast(dict[str, object], protocol_value)
    scope = cast(dict[str, object], scope_value)
    corpus = Path(required_option(arguments, "--corpus")) / "manifest.json"
    prompts = Path(required_option(arguments, "--prompts"))
    skill_source = Path(required_option(arguments, "--skill"))
    skill = skill_source / "SKILL.md" if skill_source.is_dir() else skill_source
    wrapper = Path(required_option(arguments, "--codex"))
    expected_inputs = (
        (corpus, required_digest(protocol.get("corpus_manifest_sha256"), "protocol.corpus_manifest_sha256"), "corpus manifest"),
        (prompts / "baseline.txt", required_digest(protocol.get("baseline_prompt_sha256"), "protocol.baseline_prompt_sha256"), "baseline prompt"),
        (prompts / "skill.txt", required_digest(protocol.get("skill_prompt_sha256"), "protocol.skill_prompt_sha256"), "Skill prompt"),
        (skill, required_digest(scope.get("skill_revision_sha256"), "scope.skill_revision_sha256"), "Skill source"),
        (wrapper, required_digest(protocol.get("codex_wrapper_sha256"), "protocol.codex_wrapper_sha256"), "Codex isolation wrapper"),
    )
    for path, expected, label in expected_inputs:
        if file_digest(path, label) != expected:
            raise ValueError(f"{label} differs from the frozen V8 preregistration")
    validate_corpus_trees(Path(required_option(arguments, "--corpus")), preregistration)


def safe_child(root: Path, relative: str, label: str) -> Path:
    if root.is_symlink():
        raise ValueError(f"V8 corpus root must not be a symbolic link: {root}")
    relative_path = Path(relative)
    if relative_path.is_absolute() or any(part in {"", ".", ".."} for part in relative_path.parts):
        raise ValueError(f"{label} must be a normal relative corpus path")
    root_resolved = root.resolve()
    lexical_candidate = root / relative_path
    candidate = lexical_candidate.resolve()
    try:
        _ = candidate.relative_to(root_resolved)
    except ValueError as error:
        raise ValueError(f"{label} escapes the V8 corpus root") from error
    if lexical_candidate.is_symlink():
        raise ValueError(f"{label} must not be a symbolic link")
    return candidate


def validate_corpus_trees(corpus: Path, preregistration: dict[str, object]) -> None:
    """Verify every registered public and scorer-only tree before the first pair."""
    if corpus.is_symlink():
        raise ValueError(f"V8 corpus root must not be a symbolic link: {corpus}")
    _ = tree_digest(corpus)
    manifest = load_object(corpus / "manifest.json")
    tasks_value = manifest.get("tasks")
    if not isinstance(tasks_value, list):
        raise ValueError("corpus manifest tasks must be a list")
    raw_tasks = cast(list[object], tasks_value)
    task_by_id: dict[str, dict[str, object]] = {}
    for raw_task in raw_tasks:
        if not isinstance(raw_task, dict):
            continue
        task_value = cast(dict[str, object], raw_task)
        task_id = task_value.get("task_id")
        if isinstance(task_id, str):
            task_by_id[task_id] = task_value
    plan_value = preregistration.get("task_plan")
    if not isinstance(plan_value, dict):
        raise ValueError("V8 preregistration.task_plan.tasks must be a list")
    plan = cast(dict[str, object], plan_value)
    if not isinstance(plan.get("tasks"), list):
        raise ValueError("V8 preregistration.task_plan.tasks must be a list")
    planned = cast(list[object], plan["tasks"])
    if len(planned) != len(task_by_id) or not planned:
        raise ValueError("V8 preregistration task plan must include every corpus task exactly once")
    planned_ids: set[str] = set()
    for raw_task in planned:
        if not isinstance(raw_task, dict):
            raise ValueError("V8 preregistration task plan entry must be an object")
        planned_task = cast(dict[str, object], raw_task)
        task_id = planned_task.get("task_id")
        stratum = planned_task.get("stratum")
        if not isinstance(task_id, str) or not isinstance(stratum, str) or task_id in planned_ids:
            raise ValueError("V8 preregistration task plan has invalid task_id or stratum")
        planned_ids.add(task_id)
        value = task_by_id.get(task_id)
        if value is None:
            raise ValueError(f"corpus manifest is missing task {task_id}")
        if value.get("stratum") != stratum:
            raise ValueError(f"corpus manifest task {task_id} differs from preregistration stratum")
        workspace_path = value.get("workspace_path")
        hidden_root_path = value.get("hidden_root_path")
        if not isinstance(workspace_path, str) or not isinstance(hidden_root_path, str):
            raise ValueError(f"corpus manifest task {task_id} has invalid workspace paths")
        workspace = safe_child(corpus, workspace_path, f"{task_id} workspace")
        hidden = safe_child(corpus, hidden_root_path, f"{task_id} hidden tree")
        if not workspace.is_dir():
            raise ValueError(f"{task_id} workspace is missing")
        if not hidden.is_dir():
            raise ValueError(f"{task_id} hidden tree is missing")
        expected_workspace = required_digest(value.get("workspace_tree_sha256"), f"{task_id}.workspace_tree_sha256")
        expected_hidden = required_digest(value.get("hidden_tree_sha256"), f"{task_id}.hidden_tree_sha256")
        if tree_digest(workspace) != expected_workspace:
            raise ValueError(f"{task_id} workspace tree differs from the frozen manifest")
        if tree_digest(hidden) != expected_hidden:
            raise ValueError(f"{task_id} hidden tree differs from the frozen manifest")
    if planned_ids != set(task_by_id):
        raise ValueError("V8 preregistration task plan must include every corpus task exactly once")


def validate_planned_envelope(preregistration: dict[str, object], arguments: list[str]) -> None:
    """Validate frozen planned-state invariants without importing executable dependencies."""
    if preregistration.get("status") != "planned" or preregistration.get("trials") != []:
        raise ValueError("V8 preregistration must be planned with an empty trials list")
    scope_value = preregistration.get("scope")
    if not isinstance(scope_value, dict):
        raise ValueError("V8 preregistration must contain a scope object")
    scope = cast(dict[str, object], scope_value)
    if required_option(arguments, "--model") != scope.get("model_id"):
        raise ValueError("--model differs from preregistration.scope.model_id")
    if required_option(arguments, "--harness") != scope.get("harness_id"):
        raise ValueError("--harness differs from preregistration.scope.harness_id")
    metadata_value = preregistration.get("preregistration")
    protocol_value = preregistration.get("protocol")
    if not isinstance(metadata_value, dict) or not isinstance(protocol_value, dict):
        raise ValueError("V8 preregistration must contain preregistration and protocol objects")
    metadata = cast(dict[str, object], metadata_value)
    protocol = cast(dict[str, object], protocol_value)
    if metadata.get("recorded_before_first_trial") is not True:
        raise ValueError("V8 preregistration must record itself before the first trial")
    if required_digest(metadata.get("protocol_sha256"), "preregistration.protocol_sha256") != canonical_sha256(protocol):
        raise ValueError("preregistration.protocol_sha256 differs from the frozen protocol")
    if required_digest(metadata.get("envelope_sha256"), "preregistration.envelope_sha256") != canonical_sha256(immutable_envelope(preregistration)):
        raise ValueError("preregistration.envelope_sha256 differs from the frozen envelope")


def validate_frozen_implementation(preregistration: dict[str, object]) -> None:
    """Ensure the executable protocol pieces still match their preregistered bytes."""
    protocol_value = preregistration.get("protocol")
    if not isinstance(protocol_value, dict):
        raise ValueError("V8 preregistration must contain a protocol object")
    protocol = cast(dict[str, object], protocol_value)
    required_true(
        protocol.get("execution_inputs_archived_from_preregistration_commit"),
        "protocol.execution_inputs_archived_from_preregistration_commit",
    )
    script_root = Path(__file__).resolve().parent
    components = (
        (Path(__file__).resolve(), "runner_sha256", "V8 runner"),
        (script_root / "score_effect_workspace_v8.py", "hidden_scorer_sha256", "V8 hidden scorer"),
        (script_root / "audit_effect_isolation_v8.py", "isolation_auditor_sha256", "V8 isolation auditor"),
        (script_root / "materialize_effect_corpus_v8.py", "generator_sha256", "V8 corpus generator"),
        (script_root / "analyze_skill_effect.py", "analyzer_sha256", "V8 analyzer"),
        (script_root / "run_effect_experiment_v6.py", "base_runner_sha256", "delegated paired runner"),
        (script_root / "score_effect_workspace_v6.py", "base_hidden_scorer_sha256", "delegated hidden scorer"),
    )
    for path, field, label in components:
        expected = required_digest(protocol.get(field), f"protocol.{field}")
        if file_digest(path, label) != expected:
            raise ValueError(f"{label} differs from the frozen V8 preregistration")


def validate_preregistration_commit(preregistration_path: Path, commit: str) -> None:
    """Ensure the supplied commit contains exactly the bytes about to be collected."""
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit.lower()):
        raise ValueError("--preregistration-commit must be a 40-character Git SHA")
    root_result = subprocess.run(
        ["git", "-C", str(preregistration_path.parent), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
    )
    if root_result.returncode != 0:
        raise ValueError("--preregistration must be inside a Git worktree")
    root = Path(root_result.stdout.decode("utf-8").strip())
    try:
        relative = preregistration_path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("--preregistration must be inside its Git worktree") from error
    stored_result = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{relative.as_posix()}"],
        capture_output=True,
        check=False,
    )
    if stored_result.returncode != 0:
        raise ValueError("--preregistration-commit does not contain the preregistration")
    if stored_result.stdout != preregistration_path.read_bytes():
        raise ValueError("--preregistration differs from the committed frozen V8 input")


def run_git_text(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "Git command failed"
        raise ValueError(f"V8 frozen-worktree validation failed: {detail}")
    return result.stdout.strip()


def validate_frozen_worktree(preregistration_path: Path, commit: str, arguments: list[str]) -> Path:
    """Require collection to run from the clean worktree containing its frozen commit."""
    root = Path(run_git_text(preregistration_path.parent, "rev-parse", "--show-toplevel"))
    if run_git_text(root, "rev-parse", "HEAD") != commit:
        raise ValueError("V8 collection must run from the preregistration commit's Git worktree")
    if run_git_text(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("V8 collection worktree must be clean and contain no untracked inputs")

    root_lexical = root.resolve()
    source_flags = ("--corpus", "--prompts", "--skill", "--codex", "--preregistration")
    for flag in source_flags:
        lexical_path = Path(required_option(arguments, flag)).absolute()
        path = lexical_path.resolve()
        link = symlink_component(lexical_path)
        if link is not None:
            raise ValueError(f"{flag} must not use a symbolic-link path component in a frozen V8 worktree: {link}")
        try:
            relative = path.relative_to(root_lexical)
        except ValueError as error:
            raise ValueError(f"{flag} must be inside the frozen V8 worktree") from error
        if path.is_file():
            stored = subprocess.run(
                ["git", "-C", str(root), "show", f"{commit}:{relative.as_posix()}"],
                capture_output=True,
                check=False,
            )
            if stored.returncode != 0 or stored.stdout != path.read_bytes():
                raise ValueError(f"{flag} differs from the frozen V8 worktree commit")
        else:
            tracked = run_git_text(root, "ls-tree", "-r", "--name-only", commit, "--", relative.as_posix())
            if not tracked:
                raise ValueError(f"{flag} must be a tracked path in the frozen V8 worktree")
    script = Path(__file__).resolve()
    try:
        script_relative = script.relative_to(root_lexical)
    except ValueError as error:
        raise ValueError("V8 runner must execute from the frozen V8 worktree") from error
    stored_runner = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{script_relative.as_posix()}"],
        capture_output=True,
        check=False,
    )
    if stored_runner.returncode != 0 or stored_runner.stdout != script.read_bytes():
        raise ValueError("V8 runner bytes differ from the frozen V8 worktree commit")
    return root


def frozen_archive_bytes(root: Path, commit: str) -> bytes:
    """Return the committed archive used for the V8 execution snapshot."""
    archive = subprocess.run(
        ["git", "-C", str(root), "archive", "--format=tar", commit],
        capture_output=True,
        check=False,
    )
    if archive.returncode != 0:
        raise ValueError("V8 could not archive the frozen worktree commit")
    return archive.stdout


def validate_archive_members(contents: tarfile.TarFile) -> list[tarfile.TarInfo]:
    """Reject archive entries whose extraction could escape or alter frozen inputs."""
    members = contents.getmembers()
    for member in members:
        name = Path(member.name)
        if (
            member.issym()
            or member.islnk()
            or not (member.isfile() or member.isdir())
            or name.is_absolute()
            or ".." in name.parts
        ):
            raise ValueError("V8 frozen commit archive must contain only regular files and directories without symbolic links")
    return members


def validate_frozen_archive(root: Path, commit: str) -> None:
    """Make preflight reject an archive the formal execution would not safely stage."""
    try:
        with tarfile.open(fileobj=io.BytesIO(frozen_archive_bytes(root, commit)), mode="r:") as contents:
            _ = validate_archive_members(contents)
    except tarfile.TarError as error:
        raise ValueError(f"V8 frozen worktree archive is invalid: {error}") from error


def copy_frozen_archive(root: Path, commit: str, destination: Path) -> None:
    """Materialize the exact committed tree used by a formal V8 collection."""
    try:
        with tarfile.open(fileobj=io.BytesIO(frozen_archive_bytes(root, commit)), mode="r:") as contents:
            members = validate_archive_members(contents)
            for member in members:
                contents.extract(member, destination)
    except (tarfile.TarError, OSError) as error:
        raise ValueError(f"V8 could not materialize the frozen worktree archive: {error}") from error


def frozen_worktree_relative_path(worktree_root: Path, live_path: Path, label: str) -> Path:
    """Capture a source location without following a live path after preflight."""
    lexical_root = worktree_root.expanduser().absolute()
    lexical_path = live_path.expanduser().absolute()
    link = symlink_component(lexical_path)
    if link is not None:
        raise ValueError(f"{label} must not use a symbolic-link path component in a frozen V8 worktree: {link}")
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as error:
        raise ValueError(f"{label} must be inside the frozen V8 worktree") from error
    if any(part == ".." for part in relative.parts):
        raise ValueError(f"{label} must be a normal path inside the frozen V8 worktree")
    return relative


def staged_path(staged_root: Path, relative: Path, label: str) -> Path:
    """Map a recorded source location to its immutable archive counterpart."""
    staged = staged_root / relative
    if not staged.exists() or staged.is_symlink():
        raise ValueError(f"V8 staged input is unavailable or unsafe: {label}")
    return staged


@contextmanager
def frozen_execution(arguments: list[str]) -> Iterator[FrozenExecution]:
    """Stage all agent-visible inputs from one committed archive to close TOCTOU gaps."""
    preregistration_path = Path(required_option(arguments, "--preregistration"))
    commit = required_option(arguments, "--preregistration-commit")
    worktree_root = validate_frozen_worktree(preregistration_path, commit, arguments)
    source_flags = ("--corpus", "--prompts", "--skill", "--codex", "--preregistration")
    source_relatives = {
        flag: frozen_worktree_relative_path(worktree_root, Path(required_option(arguments, flag)), flag)
        for flag in source_flags
    }
    with tempfile.TemporaryDirectory(prefix="adam-effect-v8-frozen-") as directory:
        staged_root = Path(directory) / "worktree"
        staged_root.mkdir()
        # 从提交对象而非实时工作区复制，避免校验通过后输入被替换导致实验条件漂移。
        copy_frozen_archive(worktree_root, commit, staged_root)
        staged_arguments = list(arguments)
        for flag in source_flags:
            index = staged_arguments.index(flag) + 1
            staged_arguments[index] = str(staged_path(staged_root, source_relatives[flag], flag))
        yield FrozenExecution(arguments=staged_arguments, script_root=staged_root / "scripts")


def validate_codex_version() -> None:
    """Verify the wrapper will execute the Codex release named by the Harness."""
    codex = shutil.which("codex")
    if codex is None:
        raise ValueError("codex is not available on PATH")
    result = subprocess.run([codex, "--version"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError("codex --version failed")
    version = result.stdout.strip()
    if version != f"codex-cli {CODEX_VERSION}":
        raise ValueError(f"codex version differs from frozen V8 Harness: {version!r}")


def symlink_component(path: Path) -> Path | None:
    """Return the first lexical symlink in an absolute path, if one exists."""
    absolute = path.expanduser().absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            return current
    return None


def validate_output_parent(path: Path, label: str) -> Path:
    """Keep result creation below an existing, non-symlinked directory tree."""
    absolute = path.expanduser().absolute()
    link = symlink_component(absolute)
    if link is not None:
        raise ValueError(f"{label} must not use a symbolic-link path component: {link}")
    parent = absolute.parent
    if not parent.is_dir():
        raise ValueError(f"{label} parent directory must already exist: {parent}")
    return absolute.resolve()


def validate_empty_collection_outputs(arguments: list[str]) -> None:
    """Prevent an old condition artifact or result record from being overwritten."""
    raw_output = Path(required_option(arguments, "--raw-output"))
    output = Path(required_option(arguments, "--output"))
    if output == raw_output or raw_output in output.parents:
        raise ValueError("--output must be outside --raw-output")
    resolved_raw_output = validate_output_parent(raw_output, "--raw-output")
    resolved_output = validate_output_parent(output, "--output")
    if resolved_output == resolved_raw_output or resolved_raw_output in resolved_output.parents:
        raise ValueError("--output must be outside --raw-output")
    for path, label in ((raw_output, "--raw-output"), (output, "--output")):
        if path.is_symlink():
            raise ValueError(f"{label} must not be a symbolic link")
    if raw_output.exists() and any(raw_output.iterdir()):
        raise ValueError("--raw-output must be a new or empty directory for a V8 collection")
    if output.exists():
        raise ValueError("--output must be a new result path for a V8 collection")


def validate_frozen_run_arguments(arguments: list[str]) -> None:
    """Reject all preflight drift before the shared runner can launch an Agent."""
    preregistration_path = Path(required_option(arguments, "--preregistration"))
    preregistration = load_object(preregistration_path)
    validate_planned_envelope(preregistration, arguments)
    validate_frozen_budget(preregistration, arguments)
    validate_bound_inputs(preregistration, arguments)
    validate_frozen_implementation(preregistration)
    commit = required_option(arguments, "--preregistration-commit")
    validate_preregistration_commit(preregistration_path, commit)
    _ = validate_frozen_worktree(preregistration_path, commit, arguments)
    validate_frozen_archive(Path(run_git_text(preregistration_path.parent, "rev-parse", "--show-toplevel")), commit)
    validate_codex_version()
    validate_empty_collection_outputs(arguments)


def record_isolation_failure(result_path: Path, report: dict[str, object]) -> None:
    result = load_object(result_path)
    collection_value = result.get("collection")
    collection = cast(dict[str, object], collection_value) if isinstance(collection_value, dict) else {}
    collection["ineligible_reason"] = "V8 isolation audit failed; no effect analysis or retry is allowed."
    collection["isolation_audit"] = report
    collection["isolation_audit_passed"] = False
    result["collection"] = collection
    result["status"] = "interrupted"
    _ = result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record_isolation_success(result_path: Path, report: dict[str, object]) -> None:
    """Attach the successful V8 audit before a result becomes analyzable."""
    result = load_object(result_path)
    collection_value = result.get("collection")
    collection = cast(dict[str, object], collection_value) if isinstance(collection_value, dict) else {}
    collection["isolation_audit"] = report
    collection["isolation_audit_passed"] = True
    result["collection"] = collection
    _ = result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def score_candidate(
    *,
    run_root: Path,
    task: TaskReference,
    corpus: Path,
    timeout: float,
) -> dict[str, object]:
    """Invoke the versioned V8 hidden scorer without exposing it to the agent."""
    protocol = _runtime_protocol
    script_root = _runtime_script_root
    if protocol is None:
        # 正式采集已从归档加载时，评分器必须复用同一来源，不能回退到实时工作区。
        protocol, _ = load_runtime_modules()
    if script_root is None:
        script_root = _runtime_script_root
    if script_root is None:
        raise RuntimeError("V8 hidden scorer has no initialized frozen runtime")
    command = [
        sys.executable,
        str(script_root / "score_effect_workspace_v8.py"),
        "--workspace",
        str(run_root),
        "--hidden-root",
        str(corpus / task.hidden_root_path),
        "--command-json",
        json.dumps(list(task.hidden_command)),
        "--timeout",
        str(timeout),
    ]
    try:
        result = subprocess.run(
            command,
            env=protocol.environment(),
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            check=False,
        )
        return cast(dict[str, object], json.loads(result.stdout))
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        return {"passed": False, "returncode": None, "stdout": "", "stderr": str(error), "timeout": True}


def main() -> int:
    original_argv = sys.argv[:]
    supplied = sys.argv[1:]
    validate_option_spelling(supplied)
    normalized = v8_arguments(supplied)
    preflight_count = normalized.count("--preflight")
    if preflight_count > 1:
        raise ValueError("--preflight may appear at most once")
    if preflight_count:
        normalized.remove("--preflight")
    validate_frozen_run_arguments(normalized)
    if preflight_count:
        print("V8 preflight passed")
        return 0
    with frozen_execution(normalized) as staged:
        protocol, isolation = load_runtime_modules(staged.script_root)
        original_score_candidate = protocol.score_candidate
        original_model_id = protocol.DEFAULT_MODEL_ID
        original_harness_id = protocol.DEFAULT_HARNESS_ID
        sys.argv[1:] = staged.arguments
        protocol.score_candidate = score_candidate
        protocol.DEFAULT_MODEL_ID = DEFAULT_MODEL_ID
        protocol.DEFAULT_HARNESS_ID = DEFAULT_HARNESS_ID
        try:
            exit_code = protocol.main()
            values = {
                normalized[index]: normalized[index + 1]
                for index in range(len(normalized) - 1)
                if normalized[index].startswith("--") and normalized[index] in {"--raw-output", "--output", "--skill"}
            }
            raw_root = Path(values["--raw-output"])
            result_path = Path(values["--output"])
            report = isolation.audit_collection(raw_root, result_path, Path(values["--skill"]))
            if not bool(report["passed"]):
                record_isolation_failure(result_path, report)
                return 2
            record_isolation_success(result_path, report)
            return exit_code
        finally:
            sys.argv[:] = original_argv
            protocol.score_candidate = original_score_candidate
            protocol.DEFAULT_MODEL_ID = original_model_id
            protocol.DEFAULT_HARNESS_ID = original_harness_id


if __name__ == "__main__":
    raise SystemExit(main())
