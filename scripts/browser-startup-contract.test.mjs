import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const example = JSON.parse(await readFile(path.join(repoRoot, "examples", "browser-local.service.json"), "utf8"));
const smoke = await readFile(path.join(repoRoot, "scripts", "Test-ZitadelStartup.ps1"), "utf8");
const http2 = await readFile(path.join(repoRoot, "scripts", "Test-ZitadelHttp2.mjs"), "utf8");

assert.equal(example.enabled, true);
assert.deepEqual(example.depend_on, ["postgres", "@localcert"]);
assert.equal(example.commandline.default, " start-from-init --masterkeyFromEnv --tlsMode enabled");
assert.equal(example.env.ZITADEL_EXTERNALSECURE, "true");
assert.equal(example.env.ZITADEL_TLS_CERTPATH, "${CERT_FILE}");
assert.equal(example.env.ZITADEL_TLS_KEYPATH, "${CERT_KEY}");
assert.equal(example.env.ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED, "false");
assert.equal(Object.hasOwn(example.env, "ZITADEL_MASTERKEY"), true);
assert.equal(example.env.ZITADEL_MASTERKEY.includes("${identity."), true);
assert.equal(JSON.stringify(example).includes("password="), false);
assert.deepEqual(example.healthchecks.map((check) => check.id), ["zitadel-https-ready", "zitadel-oidc-discovery-ready"]);
for (const requiredGate of ["--cacert", "trusted-http2", "openid-configuration", "Management Console", "main-", "/oauth/v2/authorize", "/ui/login/login"]) {
  assert.equal(smoke.includes(requiredGate), true, `Missing browser startup gate: ${requiredGate}`);
}
assert.equal(http2.includes('ALPNProtocols: ["h2"]'), true);
console.log("[lasso-zitadel] browser-local startup contract tests passed");
