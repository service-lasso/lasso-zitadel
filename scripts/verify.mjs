import { spawn } from "node:child_process";
import { mkdir, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { packageZitadel } from "./package.mjs";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const platform = process.env.TARGET_PLATFORM ?? process.platform;
const version = process.env.ZITADEL_VERSION ?? "v4.14.0";

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: repoRoot,
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
      ...options,
    });

    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr?.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.once("error", reject);
    child.once("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error(`${command} ${args.join(" ")} failed with exit code ${code}\n${stdout}\n${stderr}`));
      }
    });
  });
}

async function runVersion(binaryPath) {
  const attempts = [["--version"], ["version"]];
  const failures = [];

  for (const args of attempts) {
    try {
      const result = await run(binaryPath, args);
      const output = `${result.stdout}\n${result.stderr}`.trim();
      if (output.includes(version)) {
        return output;
      }
      failures.push(`${binaryPath} ${args.join(" ")} did not report ${version}:\n${output}`);
    } catch (error) {
      failures.push(error instanceof Error ? error.message : String(error));
    }
  }

  throw new Error(`Could not verify ZITADEL version.\n${failures.join("\n\n")}`);
}

const manifest = JSON.parse(await readFile(path.join(repoRoot, "service.json"), "utf8"));
if (
  manifest.id !== "zitadel" ||
  manifest.enabled !== false ||
  manifest.version !== version ||
  manifest.artifact?.source?.repo !== "service-lasso/lasso-zitadel" ||
  manifest.artifact?.source?.channel !== "latest"
) {
  throw new Error(`Unexpected ZITADEL manifest identity: ${JSON.stringify(manifest)}`);
}

if (manifest.env?.ZITADEL_PORT !== "${HTTP_PORT}" || manifest.env?.ZITADEL_MASTERKEY) {
  throw new Error("ZITADEL manifest should map port but must not bake a master key.");
}

const artifact = await packageZitadel(platform, version);
const verifyRoot = path.join(repoRoot, "output", "verify", version, platform);
const extractRoot = path.join(verifyRoot, "extract");
const binary = platform === "win32" ? "zitadel.exe" : "zitadel";
const binaryPath = path.join(extractRoot, binary);

await rm(verifyRoot, { recursive: true, force: true });
await mkdir(extractRoot, { recursive: true });
await run("tar", ["-xf", artifact, "-C", extractRoot]);

const packageMetadata = JSON.parse(
  await readFile(path.join(extractRoot, "SERVICE-LASSO-PACKAGE.json"), "utf8"),
);
if (
  packageMetadata.serviceId !== "zitadel" ||
  packageMetadata.upstream?.repo !== "zitadel/zitadel" ||
  packageMetadata.upstream?.version !== version ||
  packageMetadata.packagedBy !== "service-lasso/lasso-zitadel" ||
  packageMetadata.platform !== platform
) {
  throw new Error(`Unexpected package metadata: ${JSON.stringify(packageMetadata)}`);
}

const versionOutput = await runVersion(binaryPath);
console.log(`[lasso-zitadel] verification passed for ${version} on ${platform}: ${versionOutput}`);
