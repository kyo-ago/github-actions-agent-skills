---
name: github-actions-agent-skills
description: Create, modify, and validate GitHub Actions workflows and composite actions. Use for CI/CD authoring, workflow hardening, runner selection including ubuntu-slim, and behavior-preserving extraction of repeated steps into local composite actions.
---

# GitHub Actions authoring

Apply this priority: **Security > Correctness and Reliability > Maintainability > Execution Efficiency**.
This skill authorizes neither deployment, publishing, nor executing untrusted repository code.
Never trade a trust boundary or observable behavior for deduplication or speed.

## Start with repository evidence

Before creating a workflow, inspect existing `.github/workflows/*.{yml,yaml}`, local actions
(especially `.github/actions/`), language/build manifests, package managers and lockfiles,
scripts, reusable workflows, CI conventions, and repeated step sequences. For edits, inspect
affected callers and dependencies too. Do not execute project scripts merely to inspect them.

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

1. Apply the security, dependency, reliability and efficiency references to the affected work.
   Prefer considering `ubuntu-slim` for short API/CLI automation and lightweight scripts only
   after verifying current tools and limits in the runner reference.
2. For every new workflow, scan **all workflows and composite actions**, including unchanged
   files, for exact and input-value-only equivalent **contiguous** step sequences. Inspect
   same-workflow, cross-workflow, workflow/action, cross-action, and within-action duplicates.
   For edits, do this whenever shared processing is affected or duplication is introduced.
3. Follow the composite reference's extraction order, compatibility checklist and re-scan loop.
   Its mandatory conventions are dependency-depth tiers `atoms` through `pages` (maximum five)
   under `.github/actions/<tier>/<kebab-name>/action.yml`, and **no operation-toggle inputs**.
   Data-dependent internal conditions require its five-part exception assessment.
   Preserve observable behavior and trust boundaries; retain incompatible duplicates with reasons.

## Validate and deliver

Run the read-only helper from the **target repository root** (script path is skill-relative):

```bash
python /path/to/skill/scripts/inspect_actions.py . --format json
```

Install the helper's Python dependency only if using it; see README. It reports structural findings
and duplicate **candidates**, not semantic equivalence. Review `review` findings even on exit 0;
see the validation reference for exit codes and `--strict-review`.

Complete the validation reference's checks; do not execute adversarial fixtures.
Report checks as passed, failed, unavailable, or unverified, with evidence.
Deliver changed files, design/trust decisions, runner evidence, extraction/caller changes, residual
duplicates and exceptions, checks/results, and remaining risks. Do not claim static checks prove
runner execution, secret redaction, or before/after behavioral equivalence.
