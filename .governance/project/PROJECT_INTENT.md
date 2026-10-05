# ZITADEL wrapper intent

Package the unchanged upstream ZITADEL v4.14.0 identity service for Service Lasso. Official Windows, Linux, and modern Darwin assets remain the default. Issue #10 adds an explicitly selected Darwin amd64 macOS 11 compatibility profile built from upstream commit 10b1af91d68700707d41e820545e478cf267511b using a private maintained Go 1.26.8 toolchain. Development only; no GA declaration.

Authoritative issue: https://github.com/service-lasso/lasso-zitadel/issues/10
Active requirements: ../specs/SPEC-010-macos11-compatibility.md
Governance execution rules are the Service Lasso Core .governance/rules/gov-01 through gov-14 plus gov-09-release-authority, supplied and read for this bounded delegated work.

Issue #10 generated inventory follow-up: use a single bounded output mapping for recording and verification, derived from the immutable upstream generator contracts; preserve authenticated source and compiler boundaries. Failed run 37267875269 is diagnosis evidence, not compatibility acceptance.

Issue #13 / active [SPEC-013](../specs/SPEC-013-security-runner-budget.md) AC-013-1..5: budget only isolated scanner processes and stream nonsecret resource evidence after repeated hosted runner interruption. Keep full text-mode source/binary coverage and all existing authentication/native/publication gates. Runner shutdown is directly observed; OOM and successful remediation are unproven until parent-owned exact-candidate hosted verification.

Issue #15 / active [SPEC-015](../specs/SPEC-015-preflight-checkout-purity.md): default-Python producer preflight tests leave a fresh checkout pristine; preserve all producer, authentication, scanner and publisher gates.

Issue #17 / active [SPEC-017](../specs/SPEC-017-source-dependency-remediation.md) AC-017-1..5: retain immutable v4.14.0 identity implementation and apply an authenticated dependency-only go.mod/go.sum overlay before full generation to remediate nine reachable vulnerabilities. All original and compatibility security/source/native/publication gates remain mandatory.

Issue #21 / active [SPEC-021](../specs/SPEC-021-otel-logging-compatibility.md) AC-021-1..4: correct logging bridge API compatibility exposed by full producer37287250979 without downgrading fixed security dependencies or weakening custody/build/security gates.
