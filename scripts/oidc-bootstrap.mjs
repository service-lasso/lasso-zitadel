import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const serviceLassoOidcBootstrapDefaults = Object.freeze({
  projectKey: "service-lasso",
  projectName: "Service Lasso",
  applicationKey: "service-lasso-auth-facade",
  applicationName: "Service Lasso auth facade",
  issuer: "https://zitadel.servicelasso.localhost",
  redirectUris: ["https://auth.servicelasso.localhost/oauth2/callback"],
  postLogoutRedirectUris: ["https://auth.servicelasso.localhost/logout/callback"],
  allowedOrigins: [
    "https://auth.servicelasso.localhost",
    "https://serviceadmin.servicelasso.localhost",
  ],
  grantTypes: ["authorization_code", "refresh_token"],
  responseTypes: ["code"],
  authMethod: "client_secret_basic",
  clientSecretRef: "secretref://@secretsbroker/zitadel/service-lasso-auth-facade/client-secret",
  exportedMetadataPath: "runtime/service-lasso-oidc.metadata.json",
});

const secretLikePatterns = [
  /client[_-]?secret\s*[:=]/i,
  /access[_-]?token\s*[:=]/i,
  /refresh[_-]?token\s*[:=]/i,
  /id[_-]?token\s*[:=]/i,
  /session[_-]?cookie\s*[:=]/i,
  /BEGIN PRIVATE KEY/i,
  /password\s*[:=]/i,
];

function sortedUnique(values) {
  return [...new Set(values)].sort();
}

function normalizeConfig(config = {}) {
  const merged = { ...serviceLassoOidcBootstrapDefaults, ...config };
  return {
    ...merged,
    redirectUris: sortedUnique(merged.redirectUris ?? []),
    postLogoutRedirectUris: sortedUnique(merged.postLogoutRedirectUris ?? []),
    allowedOrigins: sortedUnique(merged.allowedOrigins ?? []),
    grantTypes: sortedUnique(merged.grantTypes ?? []),
    responseTypes: sortedUnique(merged.responseTypes ?? []),
  };
}

export function assertSafeBootstrapConfig(config) {
  const normalized = normalizeConfig(config);
  const text = JSON.stringify(normalized);

  if (!normalized.issuer.includes("servicelasso.localhost")) {
    throw new Error("ZITADEL issuer must use the servicelasso.localhost local domain.");
  }

  for (const uri of [...normalized.redirectUris, ...normalized.postLogoutRedirectUris, ...normalized.allowedOrigins]) {
    if (uri.includes(".local/")) {
      throw new Error(`Use servicelasso.localhost, not .local, for local SSO URI: ${uri}`);
    }
    if (!uri.includes("servicelasso.localhost")) {
      throw new Error(`OIDC URI must stay within the Service Lasso local domain: ${uri}`);
    }
  }

  if (!normalized.clientSecretRef.startsWith("secretref://")) {
    throw new Error("clientSecretRef must be a secretref:// pointer, not inline secret material.");
  }

  if (secretLikePatterns.some((pattern) => pattern.test(text))) {
    throw new Error("OIDC bootstrap config/output contains secret-like inline material.");
  }

  return normalized;
}

export function planServiceLassoOidcBootstrap(currentState = {}, config = serviceLassoOidcBootstrapDefaults) {
  const desired = assertSafeBootstrapConfig(config);
  const project = currentState.projects?.[desired.projectKey];
  const app = project?.applications?.[desired.applicationKey];
  const actions = [];

  if (!project) {
    actions.push({ action: "create_project", key: desired.projectKey, name: desired.projectName });
  } else if (project.name !== desired.projectName) {
    actions.push({ action: "update_project", key: desired.projectKey, from: project.name, to: desired.projectName });
  } else {
    actions.push({ action: "verify_project", key: desired.projectKey, status: "already-present" });
  }

  if (!app) {
    actions.push({ action: "create_oidc_application", key: desired.applicationKey, name: desired.applicationName });
  } else if (app.name !== desired.applicationName) {
    actions.push({ action: "update_oidc_application", key: desired.applicationKey, from: app.name, to: desired.applicationName });
  } else {
    actions.push({ action: "verify_oidc_application", key: desired.applicationKey, status: "already-present" });
  }

  const existing = app ?? {};
  const comparableFields = ["redirectUris", "postLogoutRedirectUris", "allowedOrigins", "grantTypes", "responseTypes", "authMethod"];
  for (const field of comparableFields) {
    const desiredValue = Array.isArray(desired[field]) ? sortedUnique(desired[field]) : desired[field];
    const currentValue = Array.isArray(existing[field]) ? sortedUnique(existing[field]) : existing[field];
    if (JSON.stringify(currentValue) !== JSON.stringify(desiredValue)) {
      actions.push({ action: "update_oidc_setting", key: desired.applicationKey, field, value: desiredValue });
    } else {
      actions.push({ action: "verify_oidc_setting", key: desired.applicationKey, field, status: "already-present" });
    }
  }

  if (existing.clientSecretRef !== desired.clientSecretRef) {
    actions.push({ action: "store_client_secret_ref", key: desired.applicationKey, secretRef: desired.clientSecretRef });
  } else {
    actions.push({ action: "verify_client_secret_ref", key: desired.applicationKey, status: "already-present" });
  }

  const changed = actions.some((action) => !action.action.startsWith("verify_"));
  return {
    status: changed ? (project ? "update-required" : "create-required") : "already-present",
    safeMetadata: {
      issuer: desired.issuer,
      clientId: `${desired.projectKey}:${desired.applicationKey}`,
      projectKey: desired.projectKey,
      applicationKey: desired.applicationKey,
      redirectUris: desired.redirectUris,
      postLogoutRedirectUris: desired.postLogoutRedirectUris,
      allowedOrigins: desired.allowedOrigins,
      clientSecretRef: desired.clientSecretRef,
      clientSecretValue: "redacted",
    },
    actions,
  };
}

export async function loadBootstrapState(statePath) {
  if (!statePath) {
    return {};
  }
  try {
    return JSON.parse(await readFile(statePath, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT") {
      return {};
    }
    throw error;
  }
}

export async function writeSafeMetadata(metadataPath, metadata) {
  await mkdir(path.dirname(metadataPath), { recursive: true });
  await writeFile(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`, "utf8");
}

async function main() {
  const statePath = process.env.ZITADEL_BOOTSTRAP_STATE;
  const metadataPath = process.env.ZITADEL_BOOTSTRAP_METADATA_PATH ?? serviceLassoOidcBootstrapDefaults.exportedMetadataPath;
  const state = await loadBootstrapState(statePath);
  const plan = planServiceLassoOidcBootstrap(state);
  await writeSafeMetadata(metadataPath, plan.safeMetadata);
  console.log(JSON.stringify({ status: plan.status, actions: plan.actions, safeMetadata: plan.safeMetadata }, null, 2));
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
