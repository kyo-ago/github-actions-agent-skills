"""Offline fixtures: no GitHub API calls, workflow execution, or fixture command execution."""

import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inspect_actions", SKILL / "scripts/inspect_actions.py")
inspector = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = inspector
SPEC.loader.exec_module(inspector)
CASES = json.loads((SKILL / "tests/fixtures/repositories.json").read_text())["cases"]
BY_NAME = {case["name"]: case for case in CASES}


def materialize(root, case):
    for name, text in case["files"].items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def inspect_case(case):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        materialize(root, case)
        return inspector.inspect_repository(root)


class RepositoryFixtures(unittest.TestCase):
    pass


def fixture_test(case):
    def test(self):
        result = inspect_case(case)
        errors = {finding["code"] for finding in result["findings"] if finding["severity"] == "error"}
        reviews = {finding["code"] for finding in result["findings"] if finding["severity"] == "review"}
        self.assertEqual(set(case["errors"]), errors, result)
        self.assertEqual(set(case["reviews"]), reviews, result)
        self.assertEqual(case["duplicates"], bool(result["duplicates"]), result)
        self.assertTrue(result["manual_checks"])
    return test


for fixture in CASES:
    setattr(RepositoryFixtures, "test_" + fixture["name"].replace("-", "_"), fixture_test(fixture))


class ContractTests(unittest.TestCase):
    def test_yaml_on_key_and_boolean(self):
        parsed = inspector.load_yaml("on: push\nflag: false\nword: off\n")
        self.assertEqual(parsed, {"on": "push", "flag": False, "word": "off"})
        # Modifying the loader must not mutate global PyYAML behavior.
        self.assertIn(True, inspector.yaml.safe_load("on: push"))

    def test_nonrecursive_anchor(self):
        parsed = inspector.load_yaml("one: &step {run: test}\ntwo: *step\n")
        self.assertEqual(parsed["one"], parsed["two"])

    def test_custom_tag_rejected(self):
        with self.assertRaises(inspector.yaml.YAMLError):
            inspector.load_yaml("data: !!python/object/apply:os.system ['false']")

    def test_non_json_yaml_values_rejected(self):
        for value in ("!!binary aGVsbG8=", "!!timestamp 2026-10-24", ".nan", ".inf"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                inspector.load_yaml("value: " + value)

    def test_duplicate_ranges(self):
        result = inspect_case(BY_NAME["within-workflow"])
        self.assertEqual(len(result["duplicates"]), 1)
        match = result["duplicates"][0]
        self.assertEqual((match["left"]["step"], match["right"]["step"], match["length"]), (1, 3, 2))
        self.assertEqual(match["kind"], "exact")

    def test_values_only_candidate_is_never_a_proof(self):
        matches = inspect_case(BY_NAME["data-value-candidates"])["duplicates"]
        self.assertTrue(matches)
        self.assertEqual({match["kind"] for match in matches}, {"data-values-only-candidate"})
        self.assertTrue(all(match["requires_semantic_review"] for match in matches))

    def test_job_context_kept_for_identical_steps(self):
        case = copy.deepcopy(BY_NAME["between-workflows"])
        text = case["files"][".github/workflows/b.yml"]
        case["files"][".github/workflows/b.yml"] = text.replace("permissions: {}", "permissions:\n  contents: read")
        result = inspect_case(case)
        self.assertTrue(result["duplicates"])
        self.assertNotEqual(result["sequences"][0]["context"], result["sequences"][1]["context"])

    def test_recursive_refactoring_and_fixed_point(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = BY_NAME["recursive-before"]
            materialize(root, initial)
            before = inspector.inspect_repository(root)
            self.assertTrue(before["duplicates"])
            # Apply explicit reviewed fixture stages, not an inferred automatic transformation.
            previous = initial
            for stage in ("recursive-middle", "recursive-after"):
                case = BY_NAME[stage]
                for removed in set(previous["files"]) - set(case["files"]):
                    (root / removed).unlink()
                    if (root / removed).parent != root / ".github/workflows":
                        (root / removed).parent.rmdir()
                materialize(root, case)
                result = inspector.inspect_repository(root)
                self.assertFalse([f for f in result["findings"] if f["severity"] == "error"], result)
                self.assertEqual(bool(result["duplicates"]), stage == "recursive-middle", result)
                previous = case
            final = inspector.inspect_repository(root)
            self.assertEqual(result, final)
            self.assertEqual(final["graph"][".github/actions/molecules/pipeline"], [".github/actions/atoms/prepare"])

    def test_self_repository_reference_no_checkout_assumption(self):
        report = inspect_case(BY_NAME["recursive-after"])
        self.assertEqual(report["graph"][".github/actions/molecules/pipeline"], [".github/actions/atoms/prepare"])
        self.assertTrue(any("$/ product support" in item for item in report["manual_checks"]))

    def test_output_contract_and_consumer(self):
        case = BY_NAME["step-outputs"]
        action = inspector.load_yaml(case["files"][".github/actions/atoms/digest/action.yml"])
        workflow = inspector.load_yaml(case["files"][".github/workflows/ci.yml"])
        self.assertEqual(action["outputs"]["digest"]["value"], "${{ steps.producer.outputs.digest }}")
        steps = workflow["jobs"]["check"]["steps"]
        self.assertEqual(steps[0]["id"], "shared")
        self.assertEqual(steps[1]["env"]["DIGEST"], "${{ steps.shared.outputs.digest }}")
        self.assertEqual(action["runs"]["steps"][0]["id"], "producer")

    def test_input_exception_does_not_suppress_review(self):
        case = copy.deepcopy(BY_NAME["data-condition-exception"])
        name = next(iter(case["files"]))
        case["files"][name] = "# Reviewed exception: " + case["note"] + "\n" + case["files"][name]
        report = inspect_case(case)
        self.assertIn("INPUT_CONDITION_REVIEW", {f["code"] for f in report["findings"]})

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            materialize(root, BY_NAME["no-duplicates"])
            external = Path(outside) / "action.yml"
            external.write_text("DO NOT READ: [invalid")
            alias = root / ".github/actions/atoms/external"
            alias.parent.mkdir(parents=True)
            alias.symlink_to(Path(outside), target_is_directory=True)
            workflow = root / ".github/workflows/ci.yml"
            workflow.write_text(workflow.read_text() + "      - uses: ./.github/actions/atoms/external\n")
            result = inspector.inspect_repository(root)
            self.assertIn("LOCAL_PATH_ESCAPE", {f["code"] for f in result["findings"]})

    def test_no_files_modified_by_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = BY_NAME["recursive-before"]
            materialize(root, case)
            before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            inspector.inspect_repository(root)
            after = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)

    def test_report_does_not_echo_environment_values_or_yaml_error_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            materialize(root, BY_NAME["no-duplicates"])
            path = root / ".github/workflows/ci.yml"
            original = path.read_text()
            path.write_text(original + "env:\n  TOKEN: fixture-sensitive-literal\n")
            report = inspector.inspect_repository(root)
            self.assertNotIn("fixture-sensitive-literal", json.dumps(report))
            path.write_text(original + "env: [fixture-sensitive-literal\n")
            report = inspector.inspect_repository(root)
            self.assertNotIn("fixture-sensitive-literal", json.dumps(report))
            self.assertIn("YAML_INVALID", {item["code"] for item in report["findings"]})

    def test_cli_exit_codes_and_json(self):
        script = SKILL / "scripts/inspect_actions.py"
        for name, strict, expected in (
            ("no-duplicates", False, 0), ("cycle", False, 1),
            ("behavior-toggle", False, 0), ("behavior-toggle", True, 1),
            ("within-workflow", True, 1), ("slim-suitable", False, 0),
        ):
            with self.subTest(name=name, strict=strict), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                materialize(root, BY_NAME[name])
                args = [sys.executable, str(script), str(root), "--format", "json"]
                if strict:
                    args.append("--strict-review")
                completed = subprocess.run(args, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, expected, completed.stderr)
                self.assertTrue(json.loads(completed.stdout)["manual_checks"])
        completed = subprocess.run([sys.executable, str(script), "/this/path/does/not/exist"],
                                   capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 2)

    def test_installed_skill_spec_and_local_document_links(self):
        source = (SKILL / "SKILL.md").read_text()
        frontmatter = inspector.load_yaml(source.split("---", 2)[1])
        self.assertEqual(frontmatter["name"], "github-actions-agent-skills")
        self.assertRegex(frontmatter["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(frontmatter["name"]), 64)
        self.assertTrue(0 < len(frontmatter["description"]) <= 1024)
        self.assertLess(len(source.splitlines()), 150)
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / frontmatter["name"]
            shutil.copytree(SKILL, installed, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            self.assertEqual(installed.name, frontmatter["name"])
            self.assertTrue((installed / "scripts/inspect_actions.py").is_file())
        expected_refs = {"security", "dependencies", "runners", "reliability", "efficiency", "maintainability", "composite-actions", "validation"}
        self.assertEqual({p.stem for p in (SKILL / "references").glob("*.md")}, expected_refs)
        for doc in SKILL.rglob("*.md"):
            for link in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
                if not re.match(r"[a-z]+://|#", link):
                    self.assertTrue((doc.parent / link.split("#")[0]).exists(), (doc, link))


class OptionalLinters(unittest.TestCase):
    @unittest.skipUnless(shutil.which("actionlint"), "actionlint unavailable")
    def test_self_repository_syntax_tool_compatibility(self):
        unsupported = []
        for case in CASES:
            if not case.get("self_reference_lint"):
                continue
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                materialize(root, case)
                files = sorted((root / ".github/workflows").glob("*.yml"))
                completed = subprocess.run(["actionlint", *map(str, files)], cwd=root,
                                           capture_output=True, text=True, check=False)
                if completed.returncode:
                    output = completed.stdout + completed.stderr
                    diagnostics = [line for line in output.splitlines() if re.search(r"\[[a-z-]+\]$", line)]
                    self.assertTrue(diagnostics, output)
                    self.assertTrue(all('specifying action "$/' in line
                                        and 'invalid format because ref is missing' in line
                                        for line in diagnostics), output)
                    unsupported.extend(files)
        if unsupported:
            self.skipTest(f"Installed actionlint lacks official $/ syntax support ({len(unsupported)} workflow files); helper graph checks passed, hosted validation unverified")

    @unittest.skipUnless(shutil.which("actionlint"), "actionlint unavailable")
    def test_valid_workflow_fixtures_with_actionlint(self):
        count = 0
        for case in CASES:
            if not case["lint"]:
                continue
            with self.subTest(case=case["name"]), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                materialize(root, case)
                files = sorted((root / ".github/workflows").glob("*.yml"))
                if not files:
                    continue
                completed = subprocess.run(["actionlint", "-color", *map(str, files)],
                                           cwd=root, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                count += len(files)
        self.assertGreater(count, 0)

    @unittest.skipUnless(shutil.which("shellcheck"), "ShellCheck unavailable")
    def test_valid_inline_shells_including_composites(self):
        count = 0
        for case in CASES:
            if not case["lint"] and not case.get("self_reference_lint"):
                continue
            for filename, text in case["files"].items():
                if not filename.endswith((".yml", ".yaml")):
                    continue
                doc = inspector.load_yaml(text)
                if "runs" in doc:
                    step_lists = [doc["runs"]["steps"]]
                else:
                    step_lists = [job["steps"] for job in doc.get("jobs", {}).values() if "steps" in job]
                for steps in step_lists:
                    for index, step in enumerate(steps):
                        if "run" not in step or step.get("shell", "bash") != "bash":
                            continue
                        # Static lint copy only; never execute fixture commands.
                        script = re.sub(r"\$\{\{.*?\}\}", "ACTIONS_EXPRESSION", step["run"], flags=re.S)
                        with self.subTest(case=case["name"], file=filename, step=index):
                            completed = subprocess.run(["shellcheck", "--shell=bash", "-"], input=script,
                                                       capture_output=True, text=True, check=False)
                            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                            count += 1
        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()
