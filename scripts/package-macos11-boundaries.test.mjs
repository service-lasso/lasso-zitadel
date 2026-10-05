import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, mkdir, readFile, writeFile, rm } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { packageMacos11 } from "./package.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const directory = await mkdtemp(path.join(root, "output-boundary-fixture-"));
const keys = ["upstream.tar.gz", "go.tar.gz", "go.src.tar.gz", "recipe/go1.26.8.patch", "recipe/source-hashes.json", "go/pkg/tool/linux_amd64/link", "linker-build.log", "zitadel-build.log", "asset-provenance.json", "api-generator-inventory.json", "module-verify.log", "artifacts/zitadel"];
const sha = spawnSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).stdout.trim();
const pins = JSON.parse(await readFile(path.join(root, "toolchains/macos11/input-pins.json")));
const recipeBytes = await readFile(path.join(root, "toolchains/macos11/dependency-recipe.json"));
const recipe = JSON.parse(recipeBytes);
const dependencyRecipe = { recipeSHA256: createHash("sha256").update(recipeBytes).digest("hex"), patchSHA256: recipe.patchSHA256, files: recipe.files };
let count = 0;
try {
  for (const key of keys) {
    await mkdir(path.dirname(path.join(directory, key)), { recursive: true });
    await writeFile(path.join(directory, key), "deliberately unauthenticated input fixture");
  }
  const assets = { wrapperSHA: sha, upstreamSHA: pins.upstreamSHA, upstreamArchiveSHA256: pins.upstreamArchiveSHA256, effectiveSourceHashes: { "README.md": "a".repeat(64) } };
  assets.dependencyRecipe = dependencyRecipe;
  await writeFile(path.join(directory, "asset-provenance.json"), JSON.stringify(assets));
  const hashes = Object.fromEntries(await Promise.all(keys.map(async key => [key, createHash("sha256").update(await readFile(path.join(directory, key))).digest("hex")])));
  const provenance = { wrapperSHA: sha, brokerRecipeSHA: pins.brokerRecipeSHA, effectiveSourceHashes: assets.effectiveSourceHashes, hashes,
    dependencyRecipe,
    environment: { GOENV: "off", GOWORK: "off", GOTOOLCHAIN: "local", GOFLAGS: "", CGO_ENABLED: "0", GOAMD64: "v1" },
    binaryEnvironment: { GOOS: "darwin", GOARCH: "amd64", GOAMD64: "v1", CGO_ENABLED: "0" },
    buildFlags: "-mod=readonly -x -work -trimpath", linkFlags: "-linkmode=internal -s -w" };
  async function reject(value, pattern) {
    await writeFile(path.join(directory, "artifacts/build-provenance.json"), JSON.stringify(value));
    await assert.rejects(packageMacos11(directory, `2026.10.5-${sha.slice(0, 7)}`), pattern);
    count++;
  }
  for (const key of keys) {
    const omitted = structuredClone(provenance); delete omitted.hashes[key];
    await reject(omitted, /mandatory build provenance/);
  }
  const invalid = structuredClone(provenance); invalid.hashes["upstream.tar.gz"] = "invalid";
  await reject(invalid, /mandatory build provenance/);
  const missingRecipe = structuredClone(provenance); delete missingRecipe.dependencyRecipe;
  await reject(missingRecipe, /Dependency recipe provenance/);
  const alteredRecipe = structuredClone(provenance); alteredRecipe.dependencyRecipe.files['go.mod'].after = "b".repeat(64);
  await reject(alteredRecipe, /Dependency recipe provenance/);
  const sourceDrift = structuredClone(provenance); sourceDrift.effectiveSourceHashes["README.md"] = "b".repeat(64);
  await reject(sourceDrift, /source inventories disagree/);
  await writeFile(path.join(directory, "api-generator-inventory.json"), "tampered inventory");
  await reject(provenance, /Provenance input drift: api-generator-inventory.json/);
  await writeFile(path.join(directory, "api-generator-inventory.json"), "deliberately unauthenticated input fixture");
  // Recomputed local hashes cannot authenticate fake archives: exercise the real Python guard.
  await reject(provenance, /verify-macos11-inputs.py.*failed/);
  console.log(`${count} standalone packaging negative boundary checks passed; no build/native acceptance claim`);
} finally {
  await rm(directory, { recursive: true, force: true });
}
