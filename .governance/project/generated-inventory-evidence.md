# Issue 10 generated inventory correction

Development; AC-010-1/3/4. Base develop 143a1ca71a9457e0fc12cad1c7b9e4c37cdfdde8.

Preserved hosted failure: https://github.com/service-lasso/lasso-zitadel/actions/runs/37267875269
The complete compatibility-build-diagnostics artifact confirms API generate and console build completion before pristine source verification refused packages/zitadel-proto/types/zitadel/application/v2/api_pb.d.ts. No binary/native acceptance follows from that completion.

Pinned upstream 10b1af91d68700707d41e820545e478cf267511b contracts inspected through the provider contents API:
- apps/api/project.json and buf.gen.yaml: pkg/grpc Go, openapi/v2/zitadel JSON, exact generated routes/docs/statik files.
- internal/api/ui/login/static/resources/generate.go: Sass zitadel.css and its source map.
- console/project.json and console/buf.gen.yaml: generated JavaScript/TypeScript/OpenAPI JSON, Angular dist copied to API static.
- packages/zitadel-proto/project.json and buf.gen.yaml: es/cjs JavaScript and types declarations; no src or dist exemption.
- packages/zitadel-client/project.json and tsup.config.ts: dist ESM/CJS, declarations and source maps. Hosted build-console.log lines 199-265 confirm proto/client generation and all listed client extensions; lines 3572 confirm all six console tasks passed.

Preserved private diagnostics: D:/projects/service-lasso/_evidence/zitadel10-generated-inventory-37267875269
- build-console.log SHA256 2f04e50fae42faa827f63797b5416720d0e50001db81711ae5c9974d1ba94483
- generate.log SHA256 e030c9ae22a4bc4e6b6ef2affd3421fee5fc0e6b00b58878389c65d94ed5e6c7

Verification: five generated inventory regression groups pass, covering legitimate output formats, ungenerated source/wrong-extension additions, generator contract drift/deletion, complete inventory omission/addition/tamper, and symlink files/directories. Existing 45 publication and 16 standalone packaging negative checks pass. New tests run before hosted generation. Imports suppress bytecode writes to preserve clean wrapper checks. git diff --check passes.

Authenticated upstream/compiler archives, exact wrapper SHA, immutable Broker recipe and all twelve producer provenance keys remain unchanged. Final full hosted producer, Go/security/Mach-O, modern/native Mac, browser/lifecycle and publication gates remain pending with parent ownership. No duplicate local full Nx build or shared WSL mutation was performed; the old diagnostic directory was absent in the available Ubuntu distribution.

State: scoped source correction ready for fresh review through a develop PR; isolated issue checkout retained until its governed landing path completes.
