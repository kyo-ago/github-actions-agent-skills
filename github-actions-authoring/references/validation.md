# Validation procedure and limits

Validate from the target repository, not from the skill's fixtures. Never execute repository
scripts or workflows just because they appear in YAML. Use authorized isolated runtime tests
only after reviewing trust and side effects. Keep a before/after behavior record for extractions.

## Layers

1. **Parse:** run `python /path/to/skill/scripts/inspect_actions.py . --format json`.
   Requires Python 3.10+ and the pinned PyYAML requirement in `scripts/requirements.txt`.
   The safe loader preserves `on` as a string, rejects duplicate keys, merge keys, recursive
   aliases, non-string mapping keys and custom tags instead of silently changing semantics.
   YAML anchors without recursive/merge construction are supported. GitHub-specific syntax
   validation remains a separate layer; this is not a complete YAML 1.2 implementation.
2. **Workflow syntax:** run installed `actionlint` over the actual workflow files (or from the
   root with normal discovery). Confirm its version recognizes required current features and
   runner labels. Do not remove valid new syntax merely to satisfy an old linter; report the
   version gap. Do not disable all runner/syntax checks to silence one new feature.
3. **Shell:** actionlint uses ShellCheck for workflow inline shells when installed. Additionally
   run `shellcheck` on referenced Bash/sh files and **composite inline run steps**. The helper
   does not run ShellCheck. Extract inline Bash into temporary files for static analysis only,
   supply shell/env declarations as appropriate and replace Actions expressions with inert
   placeholders solely in the lint copy. This shell check does not validate expressions or
   execute scripts. Inspect non-Bash shells with appropriate tooling or mark unavailable.
4. **GitHub schema/context:** check current workflow and metadata documentation, event syntax,
   expression-context availability, action `inputs`/`outputs`, output-producing IDs, and
   reusable workflow call contracts. actionlint primarily checks workflows; parsing composite
   YAML and checking `runs.using` alone does not fully validate action metadata.
5. **Dependencies:** follow [dependencies](dependencies.md) for authoritative SHA/repository
   verification or supported lockfile generation/verification. The helper intentionally does
   not trust a lockfile's presence and reports mutable refs/identity checks for review.
6. **Semantics/runtime:** review the matrix below, then run safe representative tests on the
   chosen actual runner where authorized. A local emulator is not proof of hosted/slim behavior.

If a tool is unavailable, use safe parsing, the helper, official schema inspection, and static
shell review as partial substitutes. Report the missing check; never label a substitute as
actionlint or ShellCheck success. Do not install tools globally as an incidental authoring step.

## Required review matrix

| Area | Verify beyond static parse |
| --- | --- |
| Trigger | Intended events/activity/filters, forks, required checks, merge queue |
| Permissions/secrets | Minimum effective scopes; external code cannot reach privileged credentials; redaction on failure |
| Runner | Current README tools, CPU/RAM/disk/architecture, duration, containers/privileges, nested action runtime |
| Timeout | Every executable job bounded; reusable callee inspected; slim cap respected |
| Concurrency | Safe interruption only; deployment order/pending runs preserved; group collisions avoided |
| Dependencies | Existing upstream commits/digests, lock coverage/identity, transitive/reusable boundaries |
| Composite metadata | Required fields, composite mode, declared inputs/outputs, run shells, allowed contexts/keys |
| Local references | Existence, checkout timing/ref/path for `./`, correct product support for `$/` |
| Composite graph | Exact depth, downward edges, no cycle, <=5, all callers updated |
| Input use | No operation toggles, including aliases/shell branches; five-part data-condition exception recorded |
| Extraction | Order, conditions, defaults, env, with, outputs, outcomes, failure and credential scope preserved |
| Artifacts/cache | Provenance and data validation; no secret storage or untrusted executable promotion |

## Helper report

`findings` have severity (`error` or `review`), code, file, location and message. `duplicates`
list candidates with file/owner and 1-based **step indexes** (not source line numbers), match
kind and length. Each sequence's `context` contains a fingerprint and field names for comparison;
environment/secret/input values are not printed. Inspect source locally to understand differences.
Only longest noncontained pairwise matches are emitted; overlapping self-matches are excluded.
Shell-text runner checks are heuristic review findings, not proof that an operation is executed.
The scanner is read-only and does not rewrite input values, move actions, or execute anything.
Large inventories may produce many candidates: reduce review scope by disposition, not by
silently skipping unchanged actions/workflows.

Default exit 1 means structural errors; `--strict-review` additionally fails on unresolved review
findings or duplicates. Exit 0 only means the enabled static checks found no blocking condition.
`manual_checks` always lists unverified aspects, including arbitrary input dataflow, remote
action internals, permissions policy, live runner compatibility and behavioral equivalence.
Review findings are not automatically waived by comments or similarly named input allowlists.

Development tests are under `tests/`; run `python -m unittest discover -s /path/to/skill/tests -v`.
They materialize fixture repositories under temporary directories and never run their commands.
They cover detection plus a staged refactor/re-scan, not an autonomous semantic refactoring engine.
