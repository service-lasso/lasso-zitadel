# SPEC-018: Supported default package security

Status: Active Development preparation, issue [#18](https://github.com/service-lasso/lasso-zitadel/issues/18).
Owner: /root/fix_zitadel_supported_package_security. Prerequisite #17 landed at c494e8396731d89fd601c39abbf391b41f8611e4; fresh boundary investigation confirmed shared packageZitadel default routing before implementation.

The protected publisher selects original upstream default binaries. Producer 37276240789 Linux module inventory directly shows Go 1.25.8 and the affected dependency graph. A repair of the explicit Mac 11 source profile alone cannot qualify these defaults.

- AC-018-1: Default Windows, Linux and Darwin amd64 binaries derive from the same authenticated v4.14.0 dependency-repaired source and complete generated assets as #17. Consume its authenticated recipe; never duplicate or alter its overlay.
- AC-018-2: Build defaults with official maintained Go 1.26.8, CGO_ENABLED=0, GOAMD64=v1 and existing target contracts. Keep default Darwin macOS >=12 and the custom Mac 11 compiler recipe unchanged.
- AC-018-3: Bind each exact binary to source recipe identity, effective source hashes, full generated inventory, official toolchain archive digest, environment and module inventory. Packaging rejects identity/digest drift.
- AC-018-4: Nonzero-return vulnerability scanners gate every exact default binary. Native Windows/Linux/modern Intel Darwin package version/help checks and metadata checks exercise the repaired package; retain original upstream three-OS package/startup checks as baseline evidence.
- AC-018-5: Final publication assets select repaired defaults exclusively. Original upstream downloads remain baseline artifacts and cannot enter the final qualified public inventory. Preserve protected owner receipt, trust, create-only publisher, attestation/checksum and exact readback gates; document inventory additions explicitly.
- AC-018-6: Focused regressions reject stale or substituted source/binary/provenance and preserve existing public service API/configuration/architecture. Full hosted producer and native checks are required direct qualification; local tests support source review only.

Archive security refinement after fresh review: embedded producer hashes/reports alone cannot qualify final bytes. Standalone packaging, native archive checks and every publisher inventory mode independently read actual Go build information with official Go1.26.8, compare the actual module inventory, and install/execute pinned govulncheck@v1.7.0 against extracted final bytes. Missing tools, mismatches, findings, errors and deadlines fail closed. Production CLI has no scanner skip or test override. Synthetic fixtures use imported unit APIs only; hosted benign Go builds exercise actual metadata and pinned scanner controls.

Scope: default binary build, packaging, security and publication selection. No service API/config change, OS trust/clock mutation, shared WSL mutation, deployment, promotion or GA decision. Parent owns independent review, integration and any authorized publisher dispatch.

Explicit transition of SPEC-010 AC-010-5: original official packages remain three-OS baseline checks via `official-baseline` only; normal default packaging fails closed without authenticated supported source output. Final default filenames and the 13-file public inventory remain unchanged. Embedded proofs and publisher archive inspection reject old originals. Full producer builds/scans defaults with pristine official Go before modifying the existing compatibility linker. Independent native default archive checks add required Windows/Linux/modern Intel Darwin version/help and existing manifest contracts.

Traceability: #18 -> AC-018-1..6; prerequisite #17; existing SPEC-010/013/015 protections remain.
