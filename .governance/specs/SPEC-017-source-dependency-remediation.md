# SPEC-017: Authenticated source dependency security remediation

Status: Active; Development; scoped issue #17. Baseline develop 158c9ea9fbe4299107cbe86cdaa316394c1aa577; hosted producer 37276240789 source scan exit 3 with nine reachable advisories. Owner /root/fix_zitadel_source_vulnerabilities; parent owns independent review, landing and exact hosted/native/publication acceptance.

- AC-017-1: Retain exact v4.14.0 upstream archive/SHA and immutable Broker Go1.26.8 recipe. Apply only wrapper-authenticated go.mod/go.sum dependency overlay before full generation, with exact before/after hashes and fixed file inventory; no mutable download, general source exemption or generated classification for locks.
- AC-017-2: Pin coherent OTel stable1.45/log0.21, grpc>=1.83.1, x/text>=0.39, x/net>=0.55 and gorilla/csrf1.7.3; retain checksum-bound resolved transitive graph. No advisory exclusions or scan narrowing.
- AC-017-3: Preserve full Console/LoginV1/protobuf generation, exact generated/source/lock/generator inventories, every pristine/patched/linked guard and 12 provenance inputs. Record authenticated dependency recipe identity through asset/build/package custody. Describe custom source truthfully.
- AC-017-4: Verify patch/path/hash tamper, omissions, extra source, links and legitimate overlay controls plus existing generated/scanner/package/publisher/preflight regressions and original official3OS CI. Security gate remains full source ./... plus exact binary with mandatory nonzero failure.
- AC-017-5: Parent-owned fresh review and exact merged hosted producer/security/native18/protected publisher evidence remain required. No local full Linux build, shared WSL mutation, author merge/publisher dispatch or GA declaration.

Traceability: issue https://github.com/service-lasso/lasso-zitadel/issues/17 maps AC-017-1..5; extends SPEC-010 AC-010-1/3/4 while preserving AC-010-2/5/6/7 and SPEC-013. Repository source remains archive-identical except the explicitly authenticated dependency overlay and declared generator outputs. Nine primary Go vulnerability reports were checked live 2026-10-05; latest upstream v4.19.4 does not fix all affected OTel/csrf pins.
