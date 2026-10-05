# SPEC-021: Security-fixed logging adapter compatibility

Active; Development; issue #21; owner /root/fix_zitadel_otel_bridge_compatibility. Base develop c494e8396731d89fd601c39abbf391b41f8611e4. Full producer 37287250979 failed with removed OTel log.KeyValue/log.Value symbols in otelslog v0.18.0 after authenticated asset generation. Preserve that failure.

- AC-021-1: Upgrade the smallest coherent logging adapter dependency graph compatible with fixed OTel stable1.45/log0.21. Do not downgrade advisory fixes or change ordinary upstream source.
- AC-021-2: Regenerate the exact go.mod/go.sum overlay against original immutable upstream 10b1af91d68700707d41e820545e478cf267511b. Preserve original before hashes; authenticate new after/patch hashes and recipe identity.
- AC-021-3: Verify legitimate adapter and upstream caller compilation, checksum/patch/source custody controls and existing targeted regressions. Full hosted generation/build/security/native verification remains parent-owned; local targeted compilation is partial evidence.
- AC-021-4: Freeze pushed develop-targeted PR for fresh parent review. Author does not merge, dispatch producers/publishers, mutate shared WSL or claim release/security acceptance. Parallel issue18 owns supported/default package and workflow files.

Traceability: https://github.com/service-lasso/lasso-zitadel/issues/21 maps AC-021-1..4; preserves SPEC-017 AC-017-1..5 and SPEC-010/SPEC-013 gates.
