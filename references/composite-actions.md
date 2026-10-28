# Behavior-preserving composite extraction

These tier/input rules are **skill conventions**, not GitHub platform requirements. GitHub
permits designs that this convention deliberately rejects. Preserve security and observable
behavior before reducing repetition.

## Scan and reach a useful fixed point

Enumerate each job's and composite's ordered steps, including unchanged files. Compare all six
scopes: within one workflow (including one job), across workflows, workflow to composite,
across composites, within one composite, and newly introduced steps against that whole inventory.
Look for exact contiguous sequences and sequences equivalent except for legitimate input data.
Never sort/reorder steps or equate superficially similar shell commands.

The helper finds runs of at least two steps, preserving all step fields for exact comparison.
It separately suggests matching shapes where only scalar `with`/`env` values differ. It does
not normalize shell programs, substitute arbitrary literals, expand local actions, or prove
equivalence. Review other semantic candidates manually, including different step names/IDs.
Different job permissions, defaults, working directories, matrices, environments, conditions,
runner OS and trust may make identical-looking steps incompatible.

For each candidate, in this order:

1. Reuse an existing compatible composite as-is.
2. Extract a common part from existing composites and use it at the needed call sites.
3. Extract shared workflow sequences.
4. Extract shared sequences across composites.
5. Recompute the dependency graph, update levels and **all** callers, validate, and re-scan.
6. Repeat until no new useful compatible candidate remains. Keep a disposition/reason for
   rejected candidates, so unchanged matches do not cause an endless extraction loop.

Do not build thin one-step wrappers simply to remove duplication. A single step may warrant an
action only when it provides an independently useful contract or substantial shared logic.
Do not recursively fragment stable code merely to fill tiers. If whole jobs/permissions/services
must be shared, consider a reusable workflow rather than forcing job semantics into a composite.

## Dependency depth, not Atomic Design responsibilities

Use `.github/actions/<tier>/<kebab-name>/action.yml` per action:

| Depth | Tier |
| --- | --- |
| 1 | atoms |
| 2 | molecules |
| 3 | organisms |
| 4 | templates |
| 5 | pages |

A node with no **local composite** dependencies has depth 1 (remote actions and local JS/Docker
actions do not increase it). Every other node has `1 + max(child depths)`. Edges may skip tiers
but must point strictly down. An action using only atoms belongs in molecules, not organisms.
Reject cycles and depth greater than five; redesign composition instead. Only create tiers used.

Resolve `./...` from the caller's `GITHUB_WORKSPACE` repository root, even inside a nested action;
it is not relative to the action directory. Ensure the correct checkout, path and ref exist
**before** use, including conditions and nondefault checkout paths. For externally distributed
composites, `./` still means the consuming workspace; do not assume it selects the action repo.
GitHub.com also documents `$/...` for same-repository actions at the running commit, without a
checkout or `@ref`; it is unavailable on GHES. Verify the target platform before using it.
The helper resolves both forms against the scanned repository, so source-local dependency
depth is checked even after lockfile tooling rewrites references. It cannot verify deployment
platform support or actual workspace contents at runtime.

## Input contract

**Do not use inputs solely to switch operations or toggle internal processing.** Examples:
`enable-cache`, `skip-tests`, `run-build`, `deploy`, `mode`, `operation`. Judge their use, not
their names. A value named `mode` passed as ordinary tool data is not automatically forbidden.
Trace aliases through env, outputs, nested `with`, shell `if`/`case`, scripts, and dynamic
commands. A toggle remains forbidden when hidden behind `env.FLAG` rather than `inputs.flag`.

Separate fixed operations into actions such as atoms/install-dependencies, atoms/build and a
molecules/install-and-build that calls both. Workflow-side `if` can choose which action to call.
Do not extract trivial install/build wrappers if they add no useful contract in the actual repo.

Path, version, command-argument and other data inputs are allowed; quote/validate them safely.
Avoid input-dependent internal `if` even for data inputs unless **all five** hold:

1. The action still has exactly one responsibility.
2. Splitting would cause substantial duplication or maintenance cost.
3. The condition is simple and predictable.
4. Permissions and trust/security boundaries do not change.
5. Keeping it together has a clear concrete benefit.

Record the reasoning for **each** criterion next to the action or in a linked review record.
This exception does not authorize operation toggles. The helper always flags input-related
conditions for review; an exception comment cannot automatically suppress the finding.
Required input metadata does not enforce presence at runtime: validate required nonempty data
inside the action when missing input would be unsafe or produce confusing failures.

## Extraction compatibility checklist

Before replacing any sequence, record and verify:

- Order and `if` semantics, including implicit `success()`, failure/skips/cancellation and matrix
  expansion. Moving an outer condition into a composite may change later step status checks.
- `shell`, `working-directory`, inherited workflow/job defaults, step/job/workflow `env`, and
  exact `with` values. Materialize inherited defaults where required; do not assume inheritance.
- Step IDs and all outputs/consumers. Define composite `outputs.<name>.value` mapping internal
  output-producing steps, then update consumers such as `steps.shared.outputs.digest`.
- Step `outcome`/`conclusion`, `continue-on-error`, timeout and error propagation. Unsupported
  or unobservable semantics must remain outside the composite, or extraction must be rejected.
- Context availability using current metadata/context rules. Workflow `secrets` context is not
  available inside composite actions; pass a narrowly scoped needed value explicitly via the
  caller, without broadening secret exposure. Do not move job/matrix/needs expressions blindly.
- Token permissions remain at the caller job boundary; a composite cannot declare its own
  job permissions, runner, services or trigger. Separate privilege levels instead of merging.
- File paths, checkout order/ref, shared filesystem mutations, `$GITHUB_ENV` / `$GITHUB_PATH`
  side effects, action pre/post hooks and cleanup behavior.

Use the current [metadata syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax)
and [composite tutorial](https://docs.github.com/en/actions/tutorials/creating-a-composite-action).
Forward outputs with `value: ${{ steps.producer.outputs.value }}` in metadata. Keep caller IDs
stable where possible, but do not claim preserved internal outcomes merely because outputs match.
Record before/after contracts and sandbox test evidence. If equivalence is not demonstrated,
report the candidate as unverified and retain the original sequence.
