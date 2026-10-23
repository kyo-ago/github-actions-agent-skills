#!/usr/bin/env python3
"""Read-only local policy checks and conservative duplicate candidates, not a security proof."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML is required; install scripts/requirements.txt in a virtual environment.\n")
    raise SystemExit(2)


TIERS = {name: level for level, name in enumerate(
    ("atoms", "molecules", "organisms", "templates", "pages"), 1)}
MANUAL_CHECKS = [
    "Verify current official runner tools/limits and remote action runtime compatibility.",
    "Verify upstream commit/digest identities or supported lockfile coverage and enforcement.",
    "Review trigger provenance, effective token/secret/cache/artifact trust boundaries.",
    "Review input dataflow through aliases, scripts and nested actions; no finding is not a proof.",
    "Verify ./ checkout timing/ref/path and $/ product support on the actual execution platform.",
    "Run actionlint, shell linting, metadata/context review and authorized behavioral tests.",
    "Review duplicate semantics and preserve outputs, outcomes, failure and cancellation behavior.",
]


class ActionsLoader(yaml.SafeLoader):
    """SafeLoader with on/off kept as strings; this is not a full YAML 1.2 schema."""


ActionsLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in resolvers
          if tag not in {"tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp"}]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
ActionsLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$"), list("tTfF"))


def unique_mapping(loader: ActionsLoader, node: yaml.MappingNode) -> dict:
    result = {}
    for key_node, value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise ValueError("YAML merge keys are unsupported; use explicit fields")
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise ValueError(f"Mapping keys must be strings at line {key_node.start_mark.line + 1}")
        if key in result:
            raise ValueError(f"Duplicate key {key!r} at line {key_node.start_mark.line + 1}")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


ActionsLoader.add_constructor("tag:yaml.org,2002:map", unique_mapping)


def load_yaml(text: str) -> dict:
    data = yaml.load(text, Loader=ActionsLoader)
    if not isinstance(data, dict):
        raise ValueError("Expected a YAML mapping")
    active: set[int] = set()
    visited: set[int] = set()

    def walk(value: Any) -> None:
        if not isinstance(value, (dict, list)):
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise ValueError("Unsupported YAML value type; use plain JSON-compatible values")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Non-finite numeric values are unsupported")
            return
        identity = id(value)
        if identity in active:
            raise ValueError("Recursive YAML aliases are unsupported")
        if identity in visited:
            return
        active.add(identity)
        for child in value.values() if isinstance(value, dict) else value:
            walk(child)
        active.remove(identity)
        visited.add(identity)

    walk(data)
    return data


@dataclass
class Finding:
    severity: str
    code: str
    file: str
    location: str
    message: str


@dataclass
class Sequence:
    file: str
    owner: str
    steps: list[dict]
    context: dict


def context_summary(context: dict) -> dict:
    """Compare execution context without printing env, secrets, inputs or inline source values."""
    return {
        "fingerprint": hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest(),
        "fields": {scope: sorted(values) for scope, values in context.items()},
    }


def local_prefix(reference: str) -> str | None:
    return next((prefix for prefix in ("./", "$/") if reference.startswith(prefix)), None)


def data_shape(step: dict) -> dict:
    """Only env/with scalar values may differ, never code, conditions, paths or other fields."""
    shaped = copy.deepcopy(step)
    for field in ("env", "with"):
        if isinstance(shaped.get(field), dict):
            shaped[field] = {
                key: {"scalar-type": type(value).__name__}
                if not isinstance(value, (dict, list)) else value
                for key, value in shaped[field].items()
            }
    return shaped


def duplicate_candidates(sequences: list[Sequence]) -> list[dict]:
    """Longest contiguous non-overlapping matches per start pair, with contained matches removed."""
    results = {}
    for shape_only in (False, True):
        tokens = [[json.dumps(data_shape(step) if shape_only else step,
                              sort_keys=True) for step in seq.steps] for seq in sequences]
        for left_index, left in enumerate(sequences):
            for right_index in range(left_index, len(sequences)):
                right = sequences[right_index]
                matches = []
                # Reverse dynamic programming: O(left steps * right steps), O(right steps) memory.
                next_row = [0] * (len(right.steps) + 1)
                for start in range(len(left.steps) - 1, -1, -1):
                    row = [0] * (len(right.steps) + 1)
                    for other in range(len(right.steps) - 1, -1, -1):
                        if tokens[left_index][start] == tokens[right_index][other]:
                            row[other] = 1 + next_row[other + 1]
                            length = row[other]
                            if left_index == right_index:
                                if other <= start:
                                    continue
                                length = min(length, other - start)
                            if length >= 2:
                                matches.append((start, other, length))
                    next_row = row
                maximal = []
                for start, other, length in sorted(matches, key=lambda item: (-item[2], item[:2])):
                    if any(a <= start and b <= other and start + length <= a + n
                           and other + length <= b + n for a, b, n in maximal):
                        continue
                    maximal.append((start, other, length))
                    exact = left.steps[start:start + length] == right.steps[other:other + length]
                    if shape_only and exact:
                        continue
                    key = (left_index, right_index, start, other, length)
                    results[key] = {
                        "kind": "exact" if exact else "data-values-only-candidate",
                        "length": length,
                        "left": {"file": left.file, "owner": left.owner, "step": start + 1},
                        "right": {"file": right.file, "owner": right.owner, "step": other + 1},
                        "requires_semantic_review": True,
                    }
    return [results[key] for key in sorted(results)]


class Inspector:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.findings: list[Finding] = []
        self.sequences: list[Sequence] = []
        self.documents: dict[Path, dict] = {}
        self.invalid_documents: set[Path] = set()
        self.graph: dict[str, set[str]] = {}

    def label(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def add(self, code: str, path: Path, location: str, message: str,
            severity: str = "error") -> None:
        self.findings.append(Finding(severity, code, self.label(path), location, message))

    def read(self, path: Path) -> dict:
        if path in self.documents:
            return self.documents[path]
        try:
            if not path.resolve().is_relative_to(self.root):
                raise ValueError("File resolves outside the repository")
            data = load_yaml(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, yaml.YAMLError, RecursionError) as exc:
            # PyYAML's default exception string includes raw YAML lines, possibly credentials.
            mark = getattr(exc, "problem_mark", None)
            location = f"line {mark.line + 1}" if mark else "document"
            message = "Invalid or unsupported YAML; inspect source locally" if isinstance(exc, yaml.YAMLError) else str(exc)
            self.add("YAML_INVALID", path, location, message)
            self.invalid_documents.add(path)
            data = {}
        self.documents[path] = data
        return data

    def local_metadata(self, reference: str, caller: Path, location: str) -> Path | None:
        prefix = local_prefix(reference)
        if prefix is None:
            return None
        relative = reference[len(prefix):]
        directory = self.root / relative
        if not relative or "@" in relative or "${{" in relative or ".." in Path(relative).parts:
            self.add("LOCAL_PATH_INVALID", caller, location, f"Invalid local action reference: {reference}")
            return None
        if not directory.resolve().is_relative_to(self.root):
            self.add("LOCAL_PATH_ESCAPE", caller, location, "Local action escapes repository")
            return None
        candidates = [directory / name for name in ("action.yml", "action.yaml")
                      if (directory / name).is_file()]
        if len(candidates) != 1:
            self.add("LOCAL_METADATA_MISSING", caller, location,
                     f"Expected exactly one action.yml/action.yaml at {reference}")
            return None
        return candidates[0]

    def inspect_uses(self, reference: Any, path: Path, location: str,
                     reusable: bool = False) -> Path | None:
        if not isinstance(reference, str):
            self.add("USES_INVALID", path, location, "uses must be a literal string")
            return None
        if local_prefix(reference):
            if reusable:
                if not reference.startswith("./.github/workflows/") or "@" in reference:
                    self.add("REUSABLE_PATH_INVALID", path, location, "Expected local workflow path without @ref")
                target = self.root / reference[2:]
                if not target.resolve().is_relative_to(self.root) or not target.is_file():
                    self.add("REUSABLE_PATH_MISSING", path, location, "Local reusable workflow does not exist")
            else:
                return self.local_metadata(reference, path, location)
        else:
            if reference.startswith("docker://"):
                fixed = re.search(r"@sha256:[a-fA-F0-9]{64}$", reference)
            else:
                fixed = re.fullmatch(r"[^\s@]+/[^\s@]+@[a-fA-F0-9]{40}", reference)
            self.add("DEPENDENCY_IDENTITY_REVIEW" if fixed else "DEPENDENCY_LOCK_REVIEW", path,
                     location, "Verify upstream identity/commit and transitive dependencies."
                     if fixed else "Verify supported lockfile coverage or use a verified full SHA/digest.",
                     "review")
        return None

    def steps(self, raw: Any, path: Path, owner: str, context: dict,
              composite: bool = False) -> list[Path]:
        if not isinstance(raw, list) or not raw:
            self.add("STEPS_INVALID", path, owner, "Expected a nonempty steps sequence")
            return []
        steps = []
        dependencies = []
        ids = set()
        for index, step in enumerate(raw, 1):
            location = f"{owner}.steps[{index}]"
            if not isinstance(step, dict):
                self.add("STEP_INVALID", path, location, "Expected a step mapping")
                continue
            steps.append(step)
            if ("run" in step) == ("uses" in step):
                self.add("STEP_COMMAND_INVALID", path, location, "Specify exactly one of run or uses")
            if "id" in step:
                identity = step["id"]
                if not isinstance(identity, str) or identity in ids:
                    self.add("STEP_ID_INVALID", path, location, "Step IDs must be unique strings")
                else:
                    ids.add(identity)
            for field in ("env", "with"):
                if field in step and not isinstance(step[field], dict):
                    self.add("STEP_MAPPING_INVALID", path, location, f"{field} must be a mapping")
            if "uses" in step:
                dependency = self.inspect_uses(step["uses"], path, location)
                if dependency:
                    dependencies.append(dependency)
            if "run" in step:
                if not isinstance(step["run"], str):
                    self.add("RUN_INVALID", path, location, "run must be a string")
                if composite and not isinstance(step.get("shell"), str):
                    self.add("COMPOSITE_SHELL_MISSING", path, location, "Composite run steps require explicit shell")
                if "${{" in str(step["run"]):
                    self.add("SCRIPT_EXPRESSION_REVIEW", path, location,
                             "Review expression injection; pass untrusted data via quoted env instead.", "review")
                if composite and re.search(r"\binputs(?:\s*\.|\s*\[)", str(step["run"])):
                    self.add("INPUT_SCRIPT_REVIEW", path, location,
                             "Inspect direct input use in code for injection and hidden operation selection.", "review")
                if "continue-on-error" in step and step["continue-on-error"] is not False:
                    self.add("FAILURE_IGNORED_REVIEW", path, location, "Justify failure suppression.", "review")
            if composite:
                condition = str(step.get("if", ""))
                if re.search(r"\binputs(?:\s*\.|\s*\[)", condition):
                    self.add("INPUT_CONDITION_REVIEW", path, location,
                             "Operation toggles are forbidden; data conditions need all five exception criteria.", "review")
                env = step.get("env", {})
                input_env = isinstance(env, dict) and any(
                    re.search(r"\binputs(?:\s*\.|\s*\[)", str(value)) for value in env.values())
                branch = re.search(r"\b(?:if|case)\b", str(step.get("run", "")))
                if input_env and (condition or branch):
                    self.add("INPUT_FLOW_REVIEW", path, location,
                             "Trace input/env aliases through conditions; validate exception or split operations.", "review")
        # Keep original indexes, including malformed steps; never join across invalid entries.
        if len(steps) == len(raw):
            self.sequences.append(Sequence(self.label(path), owner, steps, context))
        return dependencies

    def composite(self, path: Path, data: dict) -> None:
        key = self.label(path.parent)
        self.graph[key] = set()
        parts = Path(key).parts
        if (len(parts) != 4 or parts[:2] != (".github", "actions")
                or parts[2] not in TIERS or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", parts[3])):
            self.add("COMPOSITE_LAYOUT", path, "directory", "Use .github/actions/<tier>/<kebab-name>/action.yml")
        if path.name != "action.yml":
            self.add("COMPOSITE_FILENAME", path, "metadata", "This skill requires action.yml (GitHub also accepts action.yaml)")
        for field in ("name", "description"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                self.add("COMPOSITE_METADATA", path, field, f"A nonempty {field} is required")
        for field in ("inputs", "outputs"):
            mapping = data.get(field, {})
            if not isinstance(mapping, dict):
                self.add("COMPOSITE_CONTRACT", path, field, f"{field} must be a mapping")
                continue
            for name, metadata in mapping.items():
                if not isinstance(metadata, dict) or not isinstance(metadata.get("description"), str):
                    self.add("COMPOSITE_CONTRACT", path, f"{field}.{name}", "Contract entry needs description")
                if field == "outputs" and (not isinstance(metadata, dict) or not isinstance(metadata.get("value"), str)):
                    self.add("COMPOSITE_OUTPUT_VALUE", path, f"outputs.{name}", "Composite output needs value mapping")
                if (field == "inputs" and isinstance(metadata, dict)
                        and "required" in metadata and not isinstance(metadata["required"], bool)):
                    self.add("COMPOSITE_INPUT_REQUIRED", path, f"inputs.{name}", "required must be a boolean")
        deps = self.steps(data["runs"].get("steps"), path, "runs", {}, composite=True)
        for target in deps:
            target_data = self.read(target)
            if isinstance(target_data.get("runs"), dict) and target_data["runs"].get("using") == "composite":
                self.graph[key].add(self.label(target.parent))
        # Validate the resolvable subset of output references; arbitrary expressions need review.
        outputs = data.get("outputs", {})
        raw_steps = data["runs"].get("steps", [])
        step_ids = {step.get("id") for step in raw_steps if isinstance(step, dict)
                    and isinstance(step.get("id"), str)} if isinstance(raw_steps, list) else set()
        if isinstance(outputs, dict):
            for name, metadata in outputs.items():
                if isinstance(metadata, dict):
                    for producer in re.findall(r"\bsteps\.([A-Za-z_][A-Za-z0-9_-]*)\.outputs\.", str(metadata.get("value", ""))):
                        if producer not in step_ids:
                            self.add("OUTPUT_STEP_MISSING", path, f"outputs.{name}", f"Unknown producer step: {producer}")

    def workflow(self, path: Path) -> list[Path]:
        data = self.read(path)
        if path in self.invalid_documents:
            return []
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            self.add("WORKFLOW_NAME", path, "name", "Use a meaningful workflow name", "review")
        event = data.get("on")
        if not isinstance(event, (str, list, dict)) or not event:
            self.add("TRIGGER_MISSING", path, "on", "Specify intended event triggers")
        triggers = list(event) if isinstance(event, (list, dict)) else [event]
        if any(trigger in ("pull_request_target", "workflow_run", "issue_comment", "issues") for trigger in triggers):
            self.add("TRUST_BOUNDARY_REVIEW", path, "on", "Review privileged context and all externally controlled data/code.", "review")
        if "concurrency" not in data:
            self.add("CONCURRENCY_REVIEW", path, "concurrency", "Choose cancellation/serialization based on job side effects.", "review")
        jobs = data.get("jobs")
        if not isinstance(jobs, dict) or not jobs:
            self.add("JOBS_INVALID", path, "jobs", "Expected a nonempty job mapping")
            return []
        deps = []
        for name, job in jobs.items():
            location = f"jobs.{name}"
            if not isinstance(job, dict):
                self.add("JOB_INVALID", path, location, "Expected a job mapping")
                continue
            if "permissions" not in job and "permissions" not in data:
                self.add("PERMISSIONS_MISSING", path, location, "Explicit workflow or job permissions are required")
            permission = job.get("permissions", data.get("permissions"))
            if permission == "write-all":
                self.add("PERMISSIONS_BROAD", path, location, "Replace write-all with minimum explicit scopes")
            elif (("permissions" in job or "permissions" in data)
                  and not isinstance(permission, dict) and permission != "read-all"):
                self.add("PERMISSIONS_INVALID", path, location, "Expected permission map or valid scalar")
            if not job.get("name"):
                self.add("JOB_NAME", path, location, "Use a meaningful job name", "review")
            if "uses" in job:
                self.inspect_uses(job["uses"], path, location, reusable=True)
                if "timeout-minutes" in job:
                    self.add("CALLER_TIMEOUT_UNSUPPORTED", path, location, "Put timeout on executable jobs in the reusable callee")
                self.add("REUSABLE_REVIEW", path, location, "Inspect callee timeouts, permissions, contracts and dependency boundary.", "review")
                continue
            timeout = job.get("timeout-minutes")
            if timeout is None:
                self.add("TIMEOUT_MISSING", path, location, "Explicit executable-job timeout is required")
            elif isinstance(timeout, str) and "${{" in timeout:
                self.add("TIMEOUT_REVIEW", path, location, "Verify all dynamic timeout values.", "review")
            elif isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
                self.add("TIMEOUT_INVALID", path, location, "timeout-minutes must be a positive integer")
            runner = job.get("runs-on")
            if runner is None:
                self.add("RUNNER_MISSING", path, location, "Executable job needs runs-on")
            if runner == "ubuntu-slim":
                self.add("SLIM_EVIDENCE_REVIEW", path, location, "Verify current slim README, resources, cap, tools and nested action compatibility.", "review")
                scripts = json.dumps(job.get("steps", []))
                if "container" in job or "services" in job:
                    self.add("SLIM_INCOMPATIBLE", path, location, "Use a supported standard runner for job/service containers")
                if re.search(r"docker://|\bdocker\s+(?:build|run|compose|info|ps)\b|--privileged|\bmount\s", scripts):
                    self.add("SLIM_RUNTIME_REVIEW", path, location,
                             "Possible daemon/privileged operation; a CLI alone proves no runtime support.", "review")
                if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout > 15:
                    self.add("SLIM_TIMEOUT", path, location, "Exceeds checked slim 15-minute limit; reverify current official limits")
            elif "${{" in str(runner):
                self.add("RUNNER_DYNAMIC_REVIEW", path, location, "Expand and validate every runner selection.", "review")
            context = {"workflow": {key: value for key, value in data.items() if key != "jobs"},
                       "job": {key: value for key, value in job.items() if key != "steps"}}
            deps.extend(self.steps(job.get("steps"), path, location, context))
        return deps

    def check_graph(self) -> None:
        visiting: list[str] = []
        depths: dict[str, int | None] = {}

        def declared(node: str) -> int | None:
            parts = Path(node).parts
            return TIERS.get(parts[2]) if len(parts) == 4 else None

        def depth(node: str) -> int | None:
            if node in visiting:
                self.add("COMPOSITE_CYCLE", self.root / node / "action.yml", "dependencies",
                         " -> ".join(visiting[visiting.index(node):] + [node]))
                return None
            if node in depths:
                return depths[node]
            visiting.append(node)
            children = [depth(child) for child in sorted(self.graph.get(node, set()))]
            visiting.pop()
            value = None if any(child is None for child in children) else 1 + max(children, default=0)
            depths[node] = value
            if value is not None:
                path = self.root / node / "action.yml"
                if value > 5:
                    self.add("COMPOSITE_DEPTH", path, "dependencies", f"Actual depth {value} exceeds five; redesign composition")
                if declared(node) is not None and declared(node) != value:
                    self.add("COMPOSITE_LEVEL", path, "directory", f"Declared level {declared(node)} != dependency depth {value}")
            return value

        for node in sorted(self.graph):
            for child in sorted(self.graph[node]):
                source_level, target_level = declared(node), declared(child)
                if source_level is not None and target_level is not None and target_level >= source_level:
                    self.add("COMPOSITE_DIRECTION", self.root / node / "action.yml", "dependencies",
                             f"Same/upward reference to {child} is forbidden")
            depth(node)

    def inspect(self) -> dict:
        actions = self.root / ".github/actions"
        pending = set()
        if actions.exists():
            pending.update(actions.rglob("action.yml"))
            pending.update(actions.rglob("action.yaml"))
            for tier in TIERS:
                tier_path = actions / tier
                if tier_path.is_dir():
                    for directory in sorted(tier_path.iterdir()):
                        if directory.is_dir():
                            self.local_metadata("./" + self.label(directory), directory, "metadata")
        workflows = self.root / ".github/workflows"
        if workflows.exists():
            for path in sorted(list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml"))):
                pending.update(self.workflow(path))
        processed = set()
        while pending:
            path = min(pending)
            pending.remove(path)
            if path in processed:
                continue
            processed.add(path)
            data = self.read(path)
            runs = data.get("runs")
            if isinstance(runs, dict) and runs.get("using") == "composite":
                self.composite(path, data)
                for child in self.graph[self.label(path.parent)]:
                    for filename in ("action.yml", "action.yaml"):
                        target = self.root / child / filename
                        if target.is_file() and target not in processed:
                            pending.add(target)
            elif path not in self.invalid_documents:
                parts = path.relative_to(self.root).parts
                in_tier = len(parts) >= 3 and parts[:2] == (".github", "actions") and parts[2] in TIERS
                if (in_tier or not isinstance(runs, dict)
                        or not isinstance(runs.get("using"), str) or not runs["using"]):
                    self.add("ACTION_RUNS_INVALID", path, "runs.using",
                             "Tier directories require runs.using: composite; other actions need valid implementation metadata")
        self.check_graph()
        return {"findings": [asdict(finding) for finding in self.findings],
                "duplicates": duplicate_candidates(self.sequences),
                "sequences": [{"file": seq.file, "owner": seq.owner, "context": context_summary(seq.context)}
                              for seq in self.sequences],
                "graph": {node: sorted(children) for node, children in sorted(self.graph.items())},
                "manual_checks": MANUAL_CHECKS}


def inspect_repository(root: Path) -> dict:
    return Inspector(root).inspect()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict-review", action="store_true")
    args = parser.parse_args()
    if not args.repository.is_dir():
        parser.error("repository must be an existing directory")
    try:
        report = inspect_repository(args.repository)
    except RecursionError:
        sys.stderr.write("Repository dependency nesting is too deep to analyze; redesign or inspect manually.\n")
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        for finding in report["findings"]:
            print(f"{finding['severity']}: {finding['file']}:{finding['location']}: "
                  f"{finding['code']}: {finding['message']}")
        for candidate in report["duplicates"]:
            print(f"review: duplicate candidate {json.dumps(candidate, sort_keys=True)}")
        print("Unverified manual checks:")
        for check in report["manual_checks"]:
            print(f"- {check}")
    return int(any(finding["severity"] == "error" or args.strict_review
                   for finding in report["findings"]) or (args.strict_review and bool(report["duplicates"])))


if __name__ == "__main__":
    raise SystemExit(main())
