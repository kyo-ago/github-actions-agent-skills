---
name: github-actions-agent-skills
description: Create, modify, and validate GitHub Actions workflows and composite actions. Use for CI/CD authoring, workflow hardening, runner selection including ubuntu-slim, and behavior-preserving extraction of repeated steps into local composite actions.
---

# GitHub Actions authoring

Apply this priority: **Security > Correctness and Reliability > Maintainability > Execution Efficiency**.
Preserve the user's scope and repository conventions. This skill authorizes neither deployment,
publishing, nor executing untrusted repository code. Never trade a trust boundary or observable
behavior for deduplication or speed.

## Start with repository evidence

Before creating a workflow, inspect existing `.github/workflows/*.{yml,yaml}`, local actions
(especially `.github/actions/`), language/build manifests, package managers and lockfiles,
scripts, reusable workflows, CI conventions, and existing repeated step sequences. For edits,
inspect the affected callers and dependencies too. Create only necessary files and directories.
Do not execute project scripts merely to inspect them.

Load references progressively:

| Decision | Read |
| --- | --- |
| Triggers, credentials, permissions, or executable inputs | [security](references/security.md) |
| Any external action/workflow reference or lockfile | [dependencies](references/dependencies.md) |
| Selecting/changing a runner, especially slim | [runners](references/runners.md) |
| Timeouts, dependencies, failure behavior | [reliability](references/reliability.md) |
| Triggers, cancellation, caching, cost | [efficiency](references/efficiency.md) |
| Naming, updates, change scope | [maintainability](references/maintainability.md) |
| Duplicate review or composite creation/change | [composite actions](references/composite-actions.md) |
| Every generated/modified result | [validation](references/validation.md) |

Consult current official GitHub documentation for changing capabilities, runner tools, action
runtime requirements, and lockfile availability. References link the authoritative sources.
If unavailable, state precisely what is unverified; do not invent versions, SHAs, or capabilities.

## Author and refactor

1. Map event inputs, code provenance, artifacts/caches, credentials, and deployment boundaries.
   Explicitly minimize workflow/job token permissions; isolate privileged work from untrusted code.
2. Select a compatible runner. Prefer considering `ubuntu-slim` for short API/CLI automation,
   notifications, repository maintenance, and lightweight Bash/Python/Node jobs. Verify its
   official README tools and host limits first; use a standard runner if any requirement fails.
3. Set meaningful names, appropriate triggers, explicit job timeouts, correct failure propagation,
   and safe concurrency. A reusable-workflow caller cannot set a job timeout: inspect its callee.
4. For every new workflow, scan **all workflows and composite actions**, including unchanged
   files, for exact and input-value-only equivalent **contiguous** step sequences. Inspect
   same-workflow, cross-workflow, workflow/action, cross-action, and within-action duplicates.
   For edits, do this whenever shared processing is affected or duplication is introduced.
5. Follow the extraction order and compatibility checklist in the composite reference. Reuse an
   existing action first, then extract from existing composites, across workflows, and across
   composites. Re-scan after each change until no useful safe candidate remains. Never reorder
   steps to manufacture a match or create thin single-step wrappers merely to remove repetition.
6. Keep composites in `.github/actions/{atoms,molecules,organisms,templates,pages}/kebab-name/action.yml`.
   These names encode **dependency depth only**, not Atomic Design responsibilities. No local
   composite dependency means level 1; otherwise use `1 + max(dependency levels)`. Skip-level
   references are allowed; same/upward edges, cycles, and depth over five are forbidden. Update
   every caller when moving an action. Create only used levels.
7. **Never use composite inputs solely to select operations or toggle internal features.**
   Split operations into separate actions; compose fixed operations with lower-level actions.
   Data inputs for paths/versions/arguments are allowed. Even data-dependent internal conditions
   need the five-part exception assessment in the composite reference. Workflow-side conditions
   are allowed. Input names alone cannot prove compliance.
8. Preserve step order, conditions, shell, working directory, env, with, outputs, outcomes,
   credential scope, token permissions, and failure behavior. If extraction cannot preserve
   these, retain the duplication and explain why. Record all existing files affected.

## Validate and deliver

Run the read-only helper from the **target repository root** (script path is skill-relative):

```bash
python /path/to/skill/scripts/inspect_actions.py . --format json
```

It checks local structure and reports duplicate **candidates**, never rewrites YAML or certifies
semantic equivalence. Install its single Python dependency only if using the helper; see README.
Review `review` findings even when exit status is zero. `--strict-review` makes those findings fail
for review pipelines; it does not turn an empty report into proof of safety.

Follow the validation reference for actionlint, ShellCheck (including composite scripts), official
syntax/context checks, dependency verification, and runtime compatibility tests. Do not execute
adversarial fixtures. Report checks as passed, failed, unavailable, or unverified, with evidence.
Deliver changed files, design/trust decisions, runner evidence, extraction/caller changes, residual
duplicates and exceptions, checks/results, and remaining risks. Do not claim static checks prove
runner execution, secret redaction, or before/after behavioral equivalence.
