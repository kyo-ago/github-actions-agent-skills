# Runner selection

Treat `ubuntu-slim` as the preferred **candidate** for short GitHub API/CLI automation, issue/PR
management, notifications, simple repository maintenance, and lightweight Bash/Python/Node
scripts. Verify requirements before adopting it, including tool installation and retry costs.

## Mandatory live evidence

At workflow design time read both:

- [Hosted runner specifications and single-CPU limits](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [Official ubuntu-slim installed software README](https://github.com/actions/runner-images/blob/main/images/ubuntu-slim/ubuntu-slim-Readme.md)

Record retrieval date and README revision/image when obtainable. Do not embed a large tool
version inventory here. For every required command/runtime, verify presence and version support
against this README and the action's upstream runtime requirements; do not infer from a standard
Ubuntu image. Provisioning an absent tool may defeat the reason to use slim.

Check all of the following before choosing slim:

| Requirement | Decision evidence |
| --- | --- |
| CPU, RAM, architecture, disk | Current hosted-runner table and workload peak demand, including dependencies/artifacts |
| Maximum duration | Current single-CPU limit and measured/estimated worst case with headroom; set explicit timeout |
| Isolation | Container on shared host, not a full VM; verify filesystem/network assumptions |
| Privileged operations | Unprivileged container; mounting, kernel access and Docker-in-Docker cannot be assumed |
| Docker | Docker **client** in README does not imply a usable daemon/socket; reject daemon-dependent jobs absent explicit support |
| Languages and tools | Confirm Bash/Python/Node/gh and any package manager, compiler, browser, SDK actually needed |
| Actions | Inspect JavaScript runtime, OS/architecture, downloaded tools and nested action requirements |
| Job/service containers | Require explicitly documented support; use a standard VM runner for Docker/service-container workloads |
| Product and policy | Verify label availability for repository/plan and GitHub.com vs GHES/self-hosted environments |

The checked documentation describes single-CPU slim jobs with a 15-minute ceiling and an
unprivileged container. Treat this as a dated observation, recheck at use, and never configure
a longer timeout to pretend the platform ceiling disappeared. Recheck CPU/memory/disk rather
than copying a stale numeric table into workflows.

Use a compatible standard/larger runner for workloads that fail these checks, including heavy
native builds or browser suites. Check that runner's current README too. Windows/macOS/ARM
requirements override any Linux cost preference.

If official information cannot be retrieved, report tool/limit compatibility as unverified.
Retain a known-compatible existing runner or use a conservatively justified standard runner;
do not silently switch to slim. Dynamic matrix labels require expanding and checking each case.

## Route dependency-update CI by event sender

Use `ubuntu-slim` for eligible bot-triggered CI jobs and `ubuntu-latest` for human-triggered
jobs when reducing developer wait time is a priority. Check both branches of the expression
against the same job requirements and keep the same checks on both runners.

```yaml
runs-on: ${{ github.event.sender.type == 'Bot' && 'ubuntu-slim' || 'ubuntu-latest' }}
```

Check the payload of each CI trigger. This expression selects slim when GitHub reports a `Bot`
sender and falls back to `ubuntu-latest` when the sender is absent or has another type. It uses
the event sender even if someone else authored the PR or reruns the job. If self-hosted Renovate
uses a dedicated user account with a PAT, include that account's `github.event.sender.login`
explicitly if it should use slim. Keep this routing separate from permissions and trust decisions.
If release latency is the priority, use a compatible standard runner for release jobs even when
a bot starts the release.

- [Context availability and event payloads](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts)
- [Renovate identities on GitHub](https://docs.renovatebot.com/modules/platform/github/)
