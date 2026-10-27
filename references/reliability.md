# Correctness and reliability

- Give every executable job an explicit `timeout-minutes` based on realistic work and headroom,
  bounded by runner limits. Reusable-workflow call jobs do not support that keyword; inspect or
  change the callee's executable jobs instead. Document remote callee limits when unmodifiable.
- Prefer explicit `shell: bash` for Bash work: GitHub's explicit Bash invocation uses `-e` and
  `-o pipefail`, unlike the unspecified Linux/macOS shell fallback. Custom shell templates must
  deliberately preserve error propagation. Use `set -u` only if optional/unset variables are
  handled; do not blindly inject strict modes into existing scripts without compatibility checks.
- Composites must declare shell on each `run` step; caller defaults are not a substitute.
- ShellCheck catches shell defects, not expression injection or all `set -e` pitfalls. Inspect
  conditions, pipelines, subshells, command substitutions and exit codes. Avoid blanket
  `continue-on-error`, `|| true`, and swallowed failures; justify narrowly expected failures.
- Use `needs` for real job dependencies. Check skip/failure propagation, `success()` defaults,
  `failure()`, `cancelled()`, and `always()` behavior. An `always()` step may delay cancellation;
  use it only for necessary bounded cleanup/diagnostics.
- Preserve step `outcome` vs `conclusion`, especially with `continue-on-error`. A composite
  wrapper hides internal step IDs from callers. There is no general transparent mapping of
  internal outcomes to caller step outcomes: reject extraction if required behavior cannot
  be maintained. Do not replace an outcome reference with an output without caller review.
- Expose needed outputs with explicit metadata mappings to internal `steps.<id>.outputs`.
  Validate producer ID/name and rewrite **all** consumers, including job outputs and conditions.
- Use deterministic installs matching repository lockfiles (`npm ci`, frozen/locked equivalents).
  Do not introduce a second package manager or regenerate application lockfiles casually.
- Retry only bounded, identified transient network/service errors with backoff. Never retry
  tests, authentication failures, deployment mutations or non-idempotent operations blindly.
- Preserve useful command/step context and failure artifacts without tokens, credentials or
  whole-env dumps. Review both successful and unsuccessful log paths.

Test representative success, failure, skipped-step, output, and cancellation paths in an
authorized sandbox. Static validation alone cannot establish extraction equivalence.

Official sources:
- [Workflow syntax: jobs, shells, needs and timeouts](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Expressions and status functions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions)
- [Composite metadata](https://docs.github.com/en/actions/reference/workflows-and-actions/metadata-syntax)
