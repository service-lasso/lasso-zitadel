import { spawnSync } from "node:child_process";
import { chmod, cp, mkdir, readdir, rm, stat, writeFile } from "node:fs/promises";
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

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  await packageZitadel();
}
