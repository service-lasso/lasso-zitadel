# SPEC-015: Producer preflight checkout purity

Status: Active Development, issue #15, bounded author /root/fix_zitadel15_test_checkout_cache.

Publisher run 37274478975 failed at the pristine-checkout guard before owned build output existed. Baseline c17c40ad6825178c071366e996611415157d82d7 passes its three preflight tests but the security helper import creates untracked Python bytecode.

- AC-015-1: Default Python execution of the security runner test must not write bytecode for its dynamically loaded repository helper.
- AC-015-2: A hosted Linux PR regression runs every exact compatibility producer preflight command on a fresh checkout, with normal bytecode defaults, and asserts Git status remains pristine after each command. Derive commands from the producer workflow so future additions are covered.
- AC-015-3: Preserve the original producer pristine-checkout guard and all authentication, complete source/binary scans, private budgets, native, and protected publisher gates. Do not ignore or clean caches in the producer.

Traceability: issue #15 -> AC-015-1..3; SPEC-010 and SPEC-013 remain unchanged. Parent owns fresh independent review, merged-source hosted qualification and native/publication acceptance. Checkout-purity regression does not qualify a full build or release.
