# Action and reusable-workflow dependencies

Consult current official documentation and the target GitHub product/organization policy before
choosing a locking mechanism. Record source URLs, resolution date, intended release, and verified
commit. Never invent a SHA, copy an unrelated known SHA, or treat 40 hexadecimal characters as
proof that a commit exists in the intended upstream repository.

## Workflow dependency lockfiles

As checked on 2026-10-24, GitHub documents this as **public preview** for **GitHub Enterprise Cloud**.
Recheck availability for the actual repository, including GHES differences. Prefer the supported
lockfile mechanism when available and compatible; do not force a preview onto an unsupported
environment. The file's mere presence does not prove onboarding or enforcement.

- Official location: `.github/workflows/actions.lock`. Generate with the official GitHub CLI
  extension `github/gh-actions-lock` and `gh actions-lock`. **Never hand-author/edit the file**.
- Inspect installed extension/help before use. Installation runs external code: follow the
  environment's dependency-installation policy and review the upstream source/version.
- After authorized workflow/local-action edits, regenerate and review the entire diff; the
  generator can rewrite action refs and local `./` references to `$/`.
- Inspect changed commits and repository/owner numeric identities. Do not automatically accept
  moved tags, ownership changes, or `--accept-moved` resolutions.
- Confirm each intended workflow is onboarded and new/transitive dependencies are covered.
  A called reusable workflow is pinned as a dependency, but its own dependencies are governed
  by the lockfile in its defining repository. Audit that boundary separately.
- Run `gh actions-lock --verify` where online verification is available. For an offline local
  consistency check, the documented command is `gh actions-lock --verify-local --no-fix`;
  this does not reverify pins with GitHub. Reconfirm commands against the installed version.
- Policy enforcement and onboarding are distinct; changing organization policy is outside
  ordinary authoring scope. Dependabot maintains onboarded entries, not initial onboarding.

## Without a supported lockfile

Pin first-party and third-party actions and reusable workflows to verified full commit SHAs.
Resolve the intended release/tag in its upstream repository using a trusted API or Git; peel
annotated tags to commits. Verify repository ownership, release, commit reachability and source.
Record a human-readable release comment and keep it aligned with the actual pin. If offline,
retain existing verified pins or report resolution as blocked; do not emit a fictional pin as
production-ready. Test fixtures use no fabricated external SHAs.

Check nested composite dependencies and remote reusable workflows too. Pin `docker://` images
by verified digest and inspect architecture/runner compatibility; action SHA pinning alone does
not freeze downloaded packages, container base images, or scripts fetched at runtime. Avoid
unverified `curl | sh`; verify downloaded tools by provenance/checksum under project policy.

Use existing Dependabot/Renovate policy for updates. Check runtime minimum runner versions,
release notes, input/output changes, permission changes, and licensing before upgrades. Avoid
mutable branch refs and unreviewed automatic upgrades. Locking does not make malicious code safe.

Official sources:
- [Lockfile concepts and boundary](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles)
- [Generate and maintain lockfiles](https://docs.github.com/en/actions/how-tos/secure-your-work/lock-workflow-dependencies)
- [Enforcement and verification](https://docs.github.com/en/actions/how-tos/administer/enforce-workflow-lockfiles)
- [Secure use](https://docs.github.com/en/actions/reference/security/secure-use)
