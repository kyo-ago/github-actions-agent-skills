# Runner selection

Treat `ubuntu-slim` as the preferred **candidate** for short GitHub API/CLI automation, issue/PR
management, notifications, simple repository maintenance, and lightweight Bash/Python/Node
scripts. Verify requirements before adopting it. The cheapest minute can be the slower, more
expensive job after tool installation and retries.

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

## Examples of decisions, not universal templates

- A five-minute `gh api` metadata request with explicit API permissions, env-based authentication,
  and no checkout/build/container requirements is a strong slim candidate after tool verification.
- A short Python script is a candidate only after checking its interpreter and dependencies;
  a Python job compiling a large native dependency may not be lightweight.
- Docker build/run, service databases, privileged mounts, large builds, browser suites, high
  memory use, or jobs near/over the slim ceiling should use `ubuntu-24.04` or another compatible
  standard/larger runner. Check that runner's own current README too.
- A compatible Windows/macOS/ARM requirement overrides any Linux cost preference.

If official information cannot be retrieved, report tool/limit compatibility as unverified.
Retain a known-compatible existing runner or use a conservatively justified standard runner;
do not silently switch to slim. Dynamic matrix labels require expanding and checking each case.
