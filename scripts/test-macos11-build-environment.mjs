// GOENV-META-2/3: actual Go output through the production recorder and packager boundary.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { validateCompatibilityEnvironment } from "./package.mjs";

const scripts = path.dirname(fileURLToPath(import.meta.url));
const python = process.platform === "win32" ? "python" : "python3";
const env = { ...process.env, GOWORK: "off", GOTOOLCHAIN: "local", GOFLAGS: "", CGO_ENABLED: "0", GOAMD64: "v1" };
const version = spawnSync("go", ["version"], { env, encoding: "utf8" });
assert.equal(version.status, 0, `Actual Go is required: ${version.stderr}`);
console.log(version.stdout.trim());
const directory = await mkdtemp(path.join(os.tmpdir(), "zitadel-goenv-control-"));
const temporaryRoot = path.resolve(os.tmpdir());
assert.equal(path.dirname(path.resolve(directory)), temporaryRoot, "Control directory must be directly within the temporary root");
assert.ok(path.basename(directory).startsWith("zitadel-goenv-control-"));
const config = path.join(directory, "go-config");
await writeFile(config, "");
const settings = { binaryEnvironment: { GOOS: "darwin", GOARCH: "amd64", GOAMD64: "v1", CGO_ENABLED: "0" }, buildFlags: "-mod=readonly -x -work -trimpath", linkFlags: "-linkmode=internal" };
function record(environment) {
  return spawnSync(python, ["-B", "-c", "import json; from macos11_build_environment import record_environment; print(json.dumps(record_environment()))"], { cwd: scripts, env: environment, encoding: "utf8" });
}
try {
  const disabledEnv = { ...env, GOENV: "off" };
  const disabled = record(disabledEnv);
  assert.equal(disabled.status, 0, disabled.stderr);
  const recorded = JSON.parse(disabled.stdout);
  assert.equal(recorded.requestedEnvironment.GOENV, "off");
  assert.equal(recorded.environment.GOENV, "");
  const provenance = { ...recorded, ...settings };
  validateCompatibilityEnvironment(provenance);

  const defaultEnv = { ...env }; delete defaultEnv.GOENV;
  for (const environment of [defaultEnv, { ...env, GOENV: "" }, { ...env, GOENV: config }, { ...env, GOENV: path.join(directory, "missing-config") }]) {
    // Query Go independently to establish the enabled/default effective state.
    const effective = spawnSync("go", ["env", "-json", "GOENV"], { env: environment, encoding: "utf8" });
    assert.equal(effective.status, 0, effective.stderr);
    const actual = JSON.parse(effective.stdout).GOENV;
    assert.equal(typeof actual, "string");
    assert.notEqual(actual, "", "Enabled/default Go configuration must remain distinct from off");
    const refused = record(environment);
    assert.notEqual(refused.status, 0);
    assert.match(refused.stderr, /requires requested GOENV=off/);
    assert.throws(() => validateCompatibilityEnvironment({ ...provenance, requestedEnvironment: { GOENV: environment.GOENV }, environment: { ...recorded.environment, GOENV: actual } }), /Compatibility build environment disagreement/);
    // Forging the raw off field cannot make an enabled effective config acceptable.
    assert.throws(() => validateCompatibilityEnvironment({ ...provenance, environment: { ...recorded.environment, GOENV: actual } }), /Compatibility build environment disagreement/);
  }

  let refusals = 0;
  for (const value of [undefined, {}, { GOENV: "" }, { GOENV: "OFF" }, { GOENV: null }]) {
    assert.throws(() => validateCompatibilityEnvironment({ ...provenance, requestedEnvironment: value }), /Compatibility build environment disagreement/); refusals++;
  }
  for (const value of [undefined, {}, { ...recorded.environment, GOENV: "off" }, { ...recorded.environment, GOENV: null }]) {
    assert.throws(() => validateCompatibilityEnvironment({ ...provenance, environment: value }), /Compatibility build environment disagreement/); refusals++;
  }
  for (const [key, value] of Object.entries({ GOWORK: "", GOTOOLCHAIN: "auto", GOFLAGS: "-trimpath", CGO_ENABLED: "1", GOAMD64: "v2" })) {
    assert.throws(() => validateCompatibilityEnvironment({ ...provenance, environment: { ...recorded.environment, [key]: value } }), /Compatibility build environment disagreement/); refusals++;
  }
  validateCompatibilityEnvironment(provenance);
  console.log(`Actual disabled Go recorder/package control, four enabled/default controls and ${refusals} metadata refusals passed; no full candidate qualification`);
} finally {
  assert.equal(path.dirname(path.resolve(directory)), temporaryRoot);
  await rm(directory, { recursive: true, force: true });
}
