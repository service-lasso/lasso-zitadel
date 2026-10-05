# SPEC-018: Supported default package security

Status: Active Development preparation, issue [#18](https://github.com/service-lasso/lasso-zitadel/issues/18).
Owner: /root/fix_zitadel_supported_package_security. Product implementation waits for dependency repair #17 on develop and fresh boundary investigation.

The protected publisher selects original upstream default binaries. Producer 37276240789 Linux module inventory directly shows Go 1.25.8 and the affected dependency graph. A repair of the explicit Mac 11 source profile alone cannot qualify these defaults.

- AC-018-1: Default Windows, Linux and Darwin amd64 binaries derive from the same authenticated v4.14.0 dependency-repaired source and complete generated assets as #17. Consume its authenticated recipe; never duplicate or alter its overlay.
- AC-018-2: Build defaults with official maintained Go 1.26.8, CGO_ENABLED=0, GOAMD64=v1 and existing target contracts. Keep default Darwin macOS >=12 and the custom Mac 11 compiler recipe unchanged.
- AC-018-3: Bind each exact binary to source recipe identity, effective source hashes, full generated inventory, official toolchain archive digest, environment and module inventory. Packaging rejects identity/digest drift.
- AC-018-4: Nonzero-return vulnerability scanners gate every exact default binary. Native Windows/Linux/modern Intel Darwin package version/help checks and metadata checks exercise the repaired package; retain original upstream three-OS package/startup checks as baseline evidence.
- AC-018-5: Final publication assets select repaired defaults exclusively. Original upstream downloads remain baseline artifacts and cannot enter the final qualified public inventory. Preserve protected owner receipt, trust, create-only publisher, attestation/checksum and exact readback gates; document inventory additions explicitly.
- AC-018-6: Focused regressions reject stale or substituted source/binary/provenance and preserve existing public service API/configuration/architecture. Full hosted producer and native checks are required direct qualification; local tests support source review only.

Scope: default binary build, packaging, security and publication selection. No service API/config change, OS trust/clock mutation, shared WSL mutation, deployment, promotion or GA decision. Parent owns independent review, integration and any authorized publisher dispatch.

Traceability: #18 -> AC-018-1..6; prerequisite #17; existing SPEC-010/013/015 protections remain.
