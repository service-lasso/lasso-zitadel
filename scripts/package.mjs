import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { chmod, cp, mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const zitadelVersion = process.env.ZITADEL_VERSION ?? "v4.14.0";
const targetPlatform = process.env.TARGET_PLATFORM ?? process.platform;

const targets = {
  win32: {
    upstreamAsset: `zitadel-windows-amd64.tar.gz`,
    archiveType: "zip",
    binary: "zitadel.exe",
    command: ".\\zitadel.exe",
  },
  linux: {
    upstreamAsset: `zitadel-linux-amd64.tar.gz`,
    archiveType: "tar.gz",
    binary: "zitadel",
    command: "./zitadel",
  },
  darwin: {
    upstreamAsset: `zitadel-darwin-amd64.tar.gz`,
    archiveType: "tar.gz",
    binary: "zitadel",
    command: "./zitadel",
  },
};

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    stdio: "inherit",
    shell: false,
    ...options,
  });

  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed with exit code ${result.status}`);
  }
}

function versionedAssetName(version, platform, archiveType) {
  return `lasso-zitadel-${version}-${platform}.${archiveType === "zip" ? "zip" : "tar.gz"}`;
}

async function download(url, destination) {
  if (existsSync(destination)) {
    return;
  }

  const response = await fetch(url, {
    headers: {
      "user-agent": "service-lasso-lasso-zitadel-packager",
    },
  });

  if (!response.ok || !response.body) {
    throw new Error(`Failed to download ${url}: ${response.status} ${response.statusText}`);
  }

  const bytes = Buffer.from(await response.arrayBuffer());
  await writeFile(destination, bytes);
}

async function compressPackage(packageRoot, outputPath, archiveType) {
  await mkdir(path.dirname(outputPath), { recursive: true });
  await rm(outputPath, { force: true });

  if (archiveType === "zip") {
    run("powershell", [
      "-NoLogo",
      "-NoProfile",
      "-Command",
      `Compress-Archive -Path ${JSON.stringify(path.join(packageRoot, "*"))} -DestinationPath ${JSON.stringify(outputPath)} -Force`,
    ]);
    return outputPath;
  }

  run("tar", ["-czf", outputPath, "-C", packageRoot, "."]);
  return outputPath;
}

async function findBinary(root, binaryName) {
  const entries = await readdir(root, { withFileTypes: true });
  for (const entry of entries) {
    const candidate = path.join(root, entry.name);
    if (entry.isFile() && entry.name === binaryName) {
      return candidate;
    }
    if (entry.isDirectory()) {
      const found = await findBinary(candidate, binaryName);
      if (found) {
        return found;
      }
    }
  }

  return null;
}

export async function packageZitadel(platform = targetPlatform, version = zitadelVersion) {
  if (process.env.ZITADEL_PACKAGE_PROFILE === "macos11") {
    if (platform !== "darwin" || version !== "v4.14.0") throw new Error("Compatibility profile requires Darwin v4.14.0");
    return packageMacos11(process.env.ZITADEL_COMPAT_BUILD, process.env.SERVICE_LASSO_RELEASE_VERSION);
  }
  if (!process.env.ZITADEL_PACKAGE_PROFILE || process.env.ZITADEL_PACKAGE_PROFILE === "supported") {
    return packageSupported(platform, version, process.env.ZITADEL_SUPPORTED_BUILD);
  }
  if (process.env.ZITADEL_PACKAGE_PROFILE !== "official-baseline") {
    throw new Error("Unknown ZITADEL_PACKAGE_PROFILE");
  }
  const target = targets[platform];
  if (!target) {
    throw new Error(`Unsupported target platform: ${platform}`);
  }

  if (!/^v\d+\.\d+\.\d+$/.test(version)) {
    throw new Error(`Expected ZITADEL version like "v4.14.0", got "${version}".`);
  }

  const upstreamUrl = `https://github.com/zitadel/zitadel/releases/download/${version}/${target.upstreamAsset}`;
  const vendorRoot = path.join(repoRoot, "vendor", version, platform);
  const outputRoot = path.join(repoRoot, "output", "package", version, platform);
  const extractRoot = path.join(outputRoot, "extract");
  const packageRoot = path.join(outputRoot, "payload");
  const upstreamArchive = path.join(vendorRoot, target.upstreamAsset);
  const assetName = versionedAssetName(version, platform, target.archiveType);
  const outputPath = path.join(repoRoot, "dist", assetName);

  await mkdir(vendorRoot, { recursive: true });
  await rm(outputRoot, { recursive: true, force: true });
  await mkdir(extractRoot, { recursive: true });
  await mkdir(packageRoot, { recursive: true });

  await download(upstreamUrl, upstreamArchive);
  run("tar", ["-xzf", upstreamArchive, "-C", extractRoot]);

  const extractedBinary = await findBinary(extractRoot, target.binary);
  if (!extractedBinary) {
    throw new Error(`Expected ZITADEL binary "${target.binary}" was not found under ${extractRoot}`);
  }

  await cp(path.dirname(extractedBinary), packageRoot, { recursive: true });
  const packagedBinary = path.join(packageRoot, target.binary);
  const binaryStat = await stat(packagedBinary);
  if (!binaryStat.isFile()) {
    throw new Error(`Packaged ZITADEL command was not found at ${packagedBinary}`);
  }
  if (target.archiveType !== "zip") {
    await chmod(packagedBinary, 0o755);
  }

  await writeFile(
    path.join(packageRoot, "SERVICE-LASSO-PACKAGE.json"),
    `${JSON.stringify(
      {
        serviceId: "zitadel",
        upstream: {
          repo: "zitadel/zitadel",
          version,
          asset: target.upstreamAsset,
          url: upstreamUrl,
        },
        packagedBy: "service-lasso/lasso-zitadel",
        platform,
        arch: "amd64",
        command: target.command,
      },
      null,
      2,
    )}\n`,
    "utf8",
  );

  await compressPackage(packageRoot, outputPath, target.archiveType);
  console.log(`[lasso-zitadel] packaged ${outputPath}`);
  return outputPath;
}

export async function packageSupported(platform, version, buildDirectory) {
  const target = targets[platform];
  if (!target || version !== "v4.14.0") throw new Error("Supported defaults require an existing v4.14.0 amd64 target");
  if (!buildDirectory || !path.isAbsolute(buildDirectory)) throw new Error("Authenticated completed supported source build required");
  run(process.platform === "win32" ? "python" : "python3", [path.join(repoRoot, "scripts/verify-supported-defaults.py"), "owned", buildDirectory, platform]);
  const provenance = JSON.parse(await readFile(path.join(buildDirectory, "defaults/provenance.json"), "utf8"));
  const packageRoot = path.join(repoRoot, "output/package/v4.14.0", platform, "supported-payload");
  if (existsSync(packageRoot)) throw new Error("Supported staging exists; use fresh owned output");
  await mkdir(packageRoot, { recursive: true });
  for (const file of [target.binary, "modules.txt"]) await cp(path.join(buildDirectory, "defaults", platform, file), path.join(packageRoot, file));
  for (const [source, dest] of [["defaults/provenance.json", "default-build-provenance.json"], ["asset-provenance.json", "asset-provenance.json"], ["api-generator-inventory.json", "api-generator-inventory.json"], [`security-default-source-${platform}.log`, "source-vulnerabilities.txt"], [`security-default-binary-${platform}.log`, "binary-vulnerabilities.txt"]]) await cp(path.join(buildDirectory, source), path.join(packageRoot, dest));
  for (const file of ["README.md", "LICENSE"]) await cp(path.join(buildDirectory, `zitadel-${provenance.upstreamSHA}`, file), path.join(packageRoot, file));
  await cp(path.join(buildDirectory, "go/LICENSE"), path.join(packageRoot, "GO-LICENSE"));
  if (platform !== "win32") await chmod(path.join(packageRoot, target.binary), 0o755);
  await writeFile(path.join(packageRoot, "SERVICE-LASSO-PACKAGE.json"), `${JSON.stringify({ serviceId: "zitadel", upstream: { repo: "zitadel/zitadel", version, sourceCommit: provenance.upstreamSHA }, packagedBy: "service-lasso/lasso-zitadel", platform, arch: "amd64", command: target.command, profile: provenance.profile, binarySource: "authenticated-source-build", wrapperCommit: provenance.wrapperSHA, binarySHA256: provenance.targets[platform].binarySHA256 }, null, 2)}\n`);
  const outputPath = path.join(repoRoot, "dist", versionedAssetName(version, platform, target.archiveType));
  await mkdir(path.dirname(outputPath), { recursive: true });
  if (platform === "win32" && process.platform !== "win32") {
    run("python3", ["-c", "import pathlib,sys,zipfile; r=pathlib.Path(sys.argv[1]); z=zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED); [z.write(p,p.name) for p in sorted(r.iterdir())]; z.close()", packageRoot, outputPath]);
  } else await compressPackage(packageRoot, outputPath, target.archiveType);
  // Owned verification above authenticates every official compiler byte.
  run(process.platform === "win32" ? "python" : "python3", [path.join(repoRoot, "scripts/verify-supported-defaults.py"), "archive", outputPath, platform], {
    env: { ...process.env, GOROOT: path.join(buildDirectory, "go"), PATH: `${path.join(buildDirectory, "go/bin")}${path.delimiter}${process.env.PATH ?? ""}` },
  });
  return outputPath;
}

export async function packageMacos11(buildDirectory, releaseVersion) {
  if (!buildDirectory || !path.isAbsolute(buildDirectory)) throw new Error("Absolute completed compatibility build required");
  const provenance = JSON.parse(await readFile(path.join(buildDirectory, "artifacts/build-provenance.json"), "utf8"));
  const requiredHashes = [
    "upstream.tar.gz", "go.tar.gz", "go.src.tar.gz", "recipe/go1.26.8.patch",
    "recipe/source-hashes.json", "go/pkg/tool/linux_amd64/link", "linker-build.log",
    "zitadel-build.log", "asset-provenance.json", "api-generator-inventory.json",
    "module-verify.log", "artifacts/zitadel",
  ];
  if (!provenance.hashes || requiredHashes.some((key) => !Object.hasOwn(provenance.hashes, key) || !/^[a-f0-9]{64}$/.test(provenance.hashes[key]))) {
    throw new Error("Missing or invalid mandatory build provenance hashes");
  }
  const pins = JSON.parse(await readFile(path.join(repoRoot, "toolchains/macos11/input-pins.json"), "utf8"));
  const assetBytes = await readFile(path.join(buildDirectory, "asset-provenance.json"));
  const assets = JSON.parse(assetBytes.toString("utf8"));
  const recipeBytes = await readFile(path.join(repoRoot, "toolchains/macos11/dependency-recipe.json"));
  const dependencyRecipe = JSON.parse(recipeBytes);
  const dependencyIdentity = { recipeSHA256: createHash("sha256").update(recipeBytes).digest("hex"), patchSHA256: dependencyRecipe.patchSHA256, files: dependencyRecipe.files };
  if (JSON.stringify(provenance.dependencyRecipe) !== JSON.stringify(dependencyIdentity) || JSON.stringify(assets.dependencyRecipe) !== JSON.stringify(dependencyIdentity)) {
    throw new Error("Dependency recipe provenance disagreement");
  }
  if (!provenance.effectiveSourceHashes || JSON.stringify(Object.entries(provenance.effectiveSourceHashes).sort()) !== JSON.stringify(Object.entries(assets.effectiveSourceHashes ?? {}).sort())) {
    throw new Error("Build and asset effective source inventories disagree");
  }
  const head = spawnSync("git", ["rev-parse", "HEAD"], { cwd: repoRoot, encoding: "utf8" });
  if (head.status !== 0 || head.stdout.trim() !== provenance.wrapperSHA) throw new Error("Build must bind current wrapper commit");
  if (!/^[a-f0-9]{40}$/.test(pins.brokerRecipeSHA ?? "") || provenance.brokerRecipeSHA !== pins.brokerRecipeSHA) throw new Error("Reviewed recipe pin disagreement");
  if (assets.wrapperSHA !== provenance.wrapperSHA || assets.upstreamSHA !== pins.upstreamSHA || assets.upstreamArchiveSHA256 !== pins.upstreamArchiveSHA256) throw new Error("Asset source/wrapper identity disagreement");
  if (createHash("sha256").update(assetBytes).digest("hex") !== provenance.hashes["asset-provenance.json"]) throw new Error("Asset provenance digest disagreement");
  const expectedEnvironment = { GOENV: "off", GOWORK: "off", GOTOOLCHAIN: "local", GOFLAGS: "", CGO_ENABLED: "0", GOAMD64: "v1" };
  if (Object.entries(expectedEnvironment).some(([key, value]) => provenance.environment?.[key] !== value) ||
      provenance.binaryEnvironment?.GOOS !== "darwin" || provenance.binaryEnvironment?.GOARCH !== "amd64" ||
      provenance.binaryEnvironment?.GOAMD64 !== "v1" || provenance.binaryEnvironment?.CGO_ENABLED !== "0" ||
      provenance.buildFlags !== "-mod=readonly -x -work -trimpath" || provenance.linkFlags !== "-linkmode=internal") throw new Error("Compatibility build environment disagreement");
  for (const [relative, expected] of Object.entries(provenance.hashes)) {
    if (path.isAbsolute(relative) || relative.split(/[\\/]/).includes("..")) throw new Error("Unsafe provenance path");
    if (createHash("sha256").update(await readFile(path.join(buildDirectory, relative))).digest("hex") !== expected) throw new Error(`Provenance input drift: ${relative}`);
  }
  // Standalone packaging authenticates archives, source, assets and the linked toolchain.
  run(process.platform === "win32" ? "python" : "python3", [path.join(repoRoot, "scripts/verify-macos11-inputs.py"), repoRoot, buildDirectory, "linked"]);
  run(process.platform === "win32" ? "python" : "python3", [path.join(repoRoot, "scripts/verify-binary-symbols.py"), path.join(buildDirectory, "artifacts/zitadel")]);
  if (!/^\d{4}\.\d{1,2}\.\d{1,2}-[a-f0-9]{7}$/.test(releaseVersion ?? "") || !releaseVersion.endsWith(`-${provenance.wrapperSHA.slice(0, 7)}`)) {
    throw new Error("Compatibility release tag must bind exact wrapper SHA");
  }
  if (provenance.profile !== "custom-maintained-go1.26.8-darwin-amd64-macos11" || provenance.upstreamSHA !== "10b1af91d68700707d41e820545e478cf267511b") {
    throw new Error("Unexpected compatibility source/profile");
  }
  const binary = path.join(buildDirectory, "artifacts/zitadel");
  const hash = createHash("sha256").update(await readFile(binary)).digest("hex");
  if (hash !== provenance.hashes["artifacts/zitadel"]) throw new Error("Compatibility binary hash mismatch");
  const assetName = "lasso-zitadel-v4.14.0-darwin-amd64-macos11.tar.gz";
  const packageRoot = path.join(repoRoot, "output/package/v4.14.0/darwin-amd64-macos11/payload");
  if (existsSync(packageRoot)) throw new Error("Compatibility staging already exists; use fresh owned checkout/output");
  await mkdir(packageRoot, { recursive: true });
  await cp(binary, path.join(packageRoot, "zitadel"));
  await chmod(path.join(packageRoot, "zitadel"), 0o755);
  const upstreamRoot = path.join(buildDirectory, `zitadel-${provenance.upstreamSHA}`);
  for (const file of ["README.md", "LICENSE"]) await cp(path.join(upstreamRoot, file), path.join(packageRoot, file));
  await cp(path.join(buildDirectory, "go/LICENSE"), path.join(packageRoot, "GO-LICENSE"));
  await cp(path.join(buildDirectory, "recipe/go1.26.8.patch"), path.join(packageRoot, "go1.26.8-compatibility.patch"));
  await cp(path.join(buildDirectory, "recipe/source-hashes.json"), path.join(packageRoot, "toolchain-source-hashes.json"));
  for (const [source, destination] of [["artifacts/build-provenance.json", "build-provenance.json"], ["asset-provenance.json", "asset-provenance.json"]]) {
    await cp(path.join(buildDirectory, source), path.join(packageRoot, destination));
  }
  await cp(path.join(buildDirectory, "api-generator-inventory.json"), path.join(packageRoot, "api-generator-inventory.json"));
  const manifest = JSON.parse(await readFile(path.join(repoRoot, "service.json"), "utf8"));
  delete manifest.artifact.source.channel;
  manifest.artifact.source.tag = releaseVersion;
  manifest.artifact.platforms.darwin.assetName = assetName;
  manifest.description += " Explicit custom maintained Go 1.26.8 Intel macOS 11 compatibility profile.";
  await mkdir(path.join(repoRoot, "dist"), { recursive: true });
  await writeFile(path.join(repoRoot, "dist/service-darwin-amd64-macos11.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  await writeFile(path.join(packageRoot, "SERVICE-LASSO-PACKAGE.json"), `${JSON.stringify({ serviceId: "zitadel", upstream: { repo: "zitadel/zitadel", version: "v4.14.0", sourceCommit: provenance.upstreamSHA }, packagedBy: "service-lasso/lasso-zitadel", platform: "darwin", arch: "amd64", command: "./zitadel", profile: provenance.profile, binarySource: "custom-source-build", wrapperCommit: provenance.wrapperSHA, binarySHA256: hash }, null, 2)}\n`);
  await writeFile(path.join(packageRoot, "COMPATIBILITY.txt"), "Custom maintained Go 1.26.8 build of ZITADEL v4.14.0 with an authenticated dependency-only security patch for Intel macOS 11. This is a separately selected compatibility profile, not an official upstream Darwin binary or official Go macOS 11 support. See build-provenance.json and asset-provenance.json for the exact dependency recipe.\n");
  const outputPath = await compressPackage(packageRoot, path.join(repoRoot, "dist", assetName), "tar.gz");
  run(process.platform === "win32" ? "python" : "python3", [path.join(repoRoot, "scripts/verify-binary-symbols.py"), "--archive", outputPath]);
  return outputPath;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await packageZitadel();
}
