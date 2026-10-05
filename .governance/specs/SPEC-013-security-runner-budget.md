# SPEC-013: Security runner budgeting and interruption evidence

Status: Active, bounded owner-authorized Development follow-up, issue #13.

Attempts 1 and 2 of run 37270061392 completed the full authenticated build but interrupted the scanner step. Attempt 2 directly logged a runner shutdown signal; OOM remains unproven. This change improves observability and conservatively reduces scanner pressure, without claiming the root cause is fixed.

- AC-013-1: Preserve pinned private Go and govulncheck v1.7.0, complete darwin/amd64 source `./...` scan and exact compatibility binary scan in default text mode. Findings, scanner failures and deadlines must stop receipts and packaging. No exclusions, ignores, allowlists or alternate pass flags.
- AC-013-2: Apply GOMEMLIMIT=3GiB (a Go soft memory target, not an OS cap), GOMAXPROCS=2 and GOFLAGS=-p=2 only to scanner installation/scanning. Preserve build environment, full assets and linked input authentication.
- AC-013-3: Bound installation to 10 minutes, source scanning to 45 minutes and binary scanning to 15 minutes. Terminate the owned process group on deadline and fail nonzero. Resource exhaustion or a deadline never qualifies a candidate.
- AC-013-4: Stream nonsecret stage/start/end/exit, Linux host memory and current cgroup memory/OOM counters at ten-second intervals, including before execution. Retain stdout, stderr and time/max-RSS reports with always() diagnostics; abrupt hosted shutdown can prevent uploads, so streamed GitHub logs are essential. Never dump environment variables, secrets or arbitrary process command lines.
- AC-013-5: Behavioral tests cover success, nonzero and timeout, mandatory command targets/environment and no receipt after either failed scan. Existing publication/input/asset regressions stay required. Parent owns distinct independent review, exact merged-source hosted qualification, native evidence and protected publication. Local tests are surrogate evidence for runner reliability.

Traceability: issue #13 -> AC-013-1..5; SPEC-010 AC-010-1..7 remain unchanged.
