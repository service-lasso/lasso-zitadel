# Development workflow

Normal work branches from current develop as feature/<issue>-<slug>, fix/<issue>-<slug>, docs/<issue>-<slug>, or chore/<issue>-<slug>. Every commit is pushed and reviewed through a develop PR. Agents do not inspect or use main for normal development. Existing owners and shared fixtures remain untouched.

Protection expectations: develop requires PR and applicable original native/package/security gates. Compatibility publication additionally requires SPEC-010 AC-010-7 protected exact-candidate approvals and readback. This document records expectations; it does not claim remote protection settings are configured. Owner handles any provider registration after review.
