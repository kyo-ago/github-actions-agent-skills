# Maintainability and source record

Give workflows, jobs, steps and action directories meaningful purpose-based names, consistent
with the repository. Prefer a few explicit steps over an abstraction whose control flags create
a second programming language. Move complex scripts into repository files when that makes
testing/error reporting clearer; preserve working directories and environment contracts.

Use comments primarily for reasons: trust boundaries, runner constraints, required-check filter
decisions, retention, or why a duplicate remains. Avoid repeating the YAML in prose. Reuse
existing update policy for action pins/lockfiles and review upstream changelogs before upgrades.

Record changed workflow/action paths, old-to-new call paths, exposed outputs, contract changes,
exception decisions, and remaining duplicate candidates. Include changes to previously existing
files in the delivery report. Keep a candidate unchanged if safe extraction is not demonstrated.
Do not create unused tier directories or refactor unrelated application code.

## Research record

Checked 2026-10-24 (Asia/Tokyo). These are links, not vendored manuals. Recheck changing features
at authoring time. Official specifications take precedence over third-party examples.

| Source | Used for |
| --- | --- |
| [Secure use](https://docs.github.com/en/actions/reference/security/secure-use) | Trust boundaries, least privilege, injection, dependency locking |
| [Hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) | Platform limits and slim container constraints |
| [Slim README](https://github.com/actions/runner-images/blob/main/images/ubuntu-slim/ubuntu-slim-Readme.md) | Installed tools; checked blob `22be90d1042991747514a37411382137bf54b4b8`, image `20261021.31.1` |
| [Create a composite action](https://docs.github.com/en/actions/tutorials/creating-a-composite-action) | Local action execution and output forwarding |
| [Metadata syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax) | Composite inputs/outputs, shell, local self references |
| [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) | Job schemas, contexts, permissions, concurrency |
| [Agent Skills specification](https://agentskills.io/specification) | Frontmatter, install-directory name, progressive disclosure |
| [Lockfile concepts](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles) | Preview status, transitive and reusable-workflow boundaries |
| [Lockfile generation](https://docs.github.com/en/actions/how-tos/secure-your-work/lock-workflow-dependencies) | Official CLI and local-path rewrites |
| [Lockfile enforcement](https://docs.github.com/en/actions/how-tos/administer/enforce-workflow-lockfiles) | Enterprise Cloud availability and verification commands |

The following requested examples were inspected for comparison, **not copied**:

- [gihyo.jp good practices](https://gihyo.jp/article/2024/10/good-practices-for-github-actions):
  timeout, Bash, cancellation and naming ideas. Do not adopt blanket Bash tracing near secrets,
  automatic cancellation of deployment, or an old runner recommendation without current checks.
- [JSdotNet skill](https://github.com/JSdotNet/ai-plugins/blob/main/plugins/github/skills/github-actions/SKILL.md)
  and [resource](https://github.com/JSdotNet/ai-plugins/blob/main/plugins/github/resources/github-actions.md):
  version resolution and security comparison. This skill accounts for official lockfile support,
  avoids unconditional branch filters/cancellation, and does not assume universal OIDC claims.
- [awesome-copilot hardening](https://github.com/github/awesome-copilot/blob/main/skills/github-actions-hardening/SKILL.md):
  threat-oriented review comparison. Do not import broad assertions that certain event types
  always receive full secrets/write tokens, or assume all fork configurations are identical.
  This authoring skill performs authorized edits and covers first-party dependencies too.

No third-party text, templates or code is vendored, and no third-party license is claimed for this
original implementation. If adding copied assets later, inspect their source license and retain
required notices; do not infer a file's license from its host organization.
