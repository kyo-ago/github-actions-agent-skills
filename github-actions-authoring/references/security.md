# Security and trust boundaries

Read before changing events, credentials, permissions, or executable inputs.

## Establish provenance first

Map who controls each event field, checkout ref, script, dependency lifecycle hook, artifact,
cache, and output. Token scopes depend on explicit permissions, event, repository/organization
settings, fork policies, and reusable-workflow boundaries. Do not assert that an event always
has all secrets or always has a read-only token. Same-repository PR code also needs a trust review.

- Declare workflow `permissions: {}` or a justified minimal read scope; grant individual jobs
  only what their operations require. An explicit scope map sets omitted scopes to none.
  Job scopes do not add to a workflow map: assess the complete effective job map.
- Avoid `write-all`. A metadata-only API job may need no checkout and no contents permission.
- Use `pull_request` for untrusted tests. For `pull_request_target` and `workflow_run`, never
  check out or execute untrusted revisions, install their packages, load their local actions,
  evaluate their scripts, or run binaries obtained from their artifacts. A trusted checkout
  followed by an untrusted artifact/script is still unsafe. Review comment/issue triggers too.
- Separate privileged follow-up operations. Authenticate the source repository, workflow/run,
  commit, event and conclusion as applicable. A successful run or matching artifact name does
  not make attacker-generated contents trustworthy. Parse only validated data, never commands.
- For workspace-local actions, checkout the intended trusted revision first. Minimize credential
  persistence (`persist-credentials: false` unless an authenticated Git operation needs it).
  This reduces exposure; it does not make untrusted code safe in a privileged job.

## Keep data out of generated programs

Do not splice untrusted expressions into `run`, JavaScript `script`, shell templates, `eval`,
or generated commands. Composite inputs, branch names, issue bodies, matrix values, outputs,
and configuration can carry untrusted data. Pass values through step env or typed action inputs,
quote shell expansions, validate formats/allowlists and use `--` where supported. An action input
is only safe if its implementation also treats it as data.

```yaml
- name: Validate repository identifier
  shell: bash
  env:
    REPOSITORY: ${{ github.repository }}
  run: |
    [[ "$REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || exit 1
    printf 'Repository identifier validated\n'
```

For `$GITHUB_OUTPUT` / `$GITHUB_ENV`, validate single-line values or use a fresh delimiter and
ensure no collision; arbitrary hostile multiline data is better kept in a file. Avoid command
injection via data written to these files. Never log event dumps containing credentials.

## Credentials, caches, and runners

- Secrets and derived credentials must not reach logs, debug tracing, artifacts, caches, or
  ordinary outputs. Mask derived values before use; masking is a fallback, not proof of safety.
  Do not enable blanket `set -x`. Review failure paths and third-party tool error output too.
- Prefer OIDC with short-lived credentials, `id-token: write` only on the required job, and
  provider trust policies constrained by repository, audience, ref/environment and workflow
  where supported. Verify provider-specific claim support; never copy a universal trust policy.
- Treat cache contents as executable supply-chain inputs. Never cache credentials. Avoid broad
  restore prefixes across trust domains. Check the current cache access policy, including
  `cache-mode` where supported; never enable writes for untrusted runs just to improve hit rate.
- Validate artifact provenance and contents, use narrowly scoped paths/retention, and avoid
  extracting untrusted files over trusted scripts or action metadata.
- Do not send public/untrusted PRs to persistent self-hosted runners. Prefer ephemeral isolated
  runners without ambient credentials/network access; runner groups and labels alone are not
  a sandbox. Separate tenants and privileged jobs.

Review action source/dependencies using [dependencies](dependencies.md). Assess security again
after extraction: sharing code must not widen permissions or expose secrets to additional steps.

Official sources:
- [Secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [Events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [OIDC](https://docs.github.com/en/actions/concepts/security/openid-connect)
- [Dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
