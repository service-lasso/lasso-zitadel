# ZITADEL wrapper intent

Package the unchanged upstream ZITADEL v4.14.0 identity service for Service Lasso. Official Windows, Linux, and modern Darwin assets remain the default. Issue #10 adds an explicitly selected Darwin amd64 macOS 11 compatibility profile built from upstream commit 10b1af91d68700707d41e820545e478cf267511b using a private maintained Go 1.26.8 toolchain. Development only; no GA declaration.

Authoritative issue: https://github.com/service-lasso/lasso-zitadel/issues/10
Active requirements: ../specs/SPEC-010-macos11-compatibility.md
Governance execution rules are the Service Lasso Core .governance/rules/gov-01 through gov-14 plus gov-09-release-authority, supplied and read for this bounded delegated work.
