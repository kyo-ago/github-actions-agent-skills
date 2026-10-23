# Execution efficiency without changed semantics

- Choose events, activity types, branches and paths that match actual work. Check branch/tag
  filter semantics and negative-pattern ordering. Do not filter out required status checks in
  a way that leaves merge protection permanently pending. Include `merge_group` where required
  by the repository's merge queue. Add manual triggers only when they serve a real use.
- Avoid duplicate push/PR runs only when coverage remains equivalent. Do not suppress fork PR
  checks or release/security checks to save minutes.
- Cancel stale **CI** only when work is safely interruptible. Scope the concurrency group to
  workflow plus relevant ref/PR to prevent unrelated workflow cancellation. Review same-branch
  push/PR interactions and reusable-workflow group collisions.
- For deployment, signing, publishing and other mutations, choose a serialization strategy
  preserving recovery and ordering; do not default to `cancel-in-progress: true`. Even with
  cancellation disabled, default concurrency may replace a pending run. If every deployment
  must run, check current queue support/product availability or use an appropriate durable
  deployment queue. Concurrency is not a transactional lock.
- Cache package downloads only if restore/save costs beat reinstalling. Include OS/architecture,
  relevant runtime/tool versions and lockfile hash. Do not reuse compiled/native dependencies
  across incompatible environments. Avoid caching credentials or broad workspace outputs.
- Evaluate current cache access controls for trust separation before enabling writes; keep
  privileged deployment caches separate from untrusted PR data. A cache hit is not proof of
  integrity or correctness. Measure hit rate and job duration rather than assuming savings.
- Choose slim using [runners](runners.md). Include cold tool setup, CPU bottlenecks, artifacts,
  cache costs and billing in the comparison. Do not parallelize beyond repository/service
  limits or hide failures with matrix settings.

Official sources:
- [Workflow syntax: events, filters and concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
