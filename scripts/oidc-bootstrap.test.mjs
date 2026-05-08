import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import {
  assertSafeBootstrapConfig,
  planServiceLassoOidcBootstrap,
  serviceLassoOidcBootstrapDefaults,
  writeSafeMetadata,
} from "./oidc-bootstrap.mjs";

const secretSentinels = [
  "ACTUAL_CLIENT_SECRET",
  "BEGIN PRIVATE KEY",
  "refresh_token=",
  "access_token=",
  "id_token=",
  "session_cookie=",
  "password=",
];

function assertNoSecretMaterial(value) {
  const text = JSON.stringify(value);
  for (const sentinel of secretSentinels) {
    assert.equal(text.includes(sentinel), false, `leaked sentinel: ${sentinel}`);
  }
}

{
  const plan = planServiceLassoOidcBootstrap({});
  assert.equal(plan.status, "create-required");
  assert.deepEqual(
    plan.actions.map((action) => action.action).slice(0, 2),
    ["create_project", "create_oidc_application"],
  );
  assert.equal(plan.safeMetadata.issuer, "https://zitadel.servicelasso.localhost");
  assert.equal(plan.safeMetadata.clientSecretValue, "redacted");
  assert.equal(plan.safeMetadata.clientSecretRef.startsWith("secretref://"), true);
  assertNoSecretMaterial(plan);
}

{
  const state = {
    projects: {
      "service-lasso": {
        name: "Service Lasso",
        applications: {
          "service-lasso-auth-facade": {
            name: "Service Lasso auth facade",
            redirectUris: serviceLassoOidcBootstrapDefaults.redirectUris,
            postLogoutRedirectUris: serviceLassoOidcBootstrapDefaults.postLogoutRedirectUris,
            allowedOrigins: serviceLassoOidcBootstrapDefaults.allowedOrigins,
            grantTypes: serviceLassoOidcBootstrapDefaults.grantTypes,
            responseTypes: serviceLassoOidcBootstrapDefaults.responseTypes,
            authMethod: serviceLassoOidcBootstrapDefaults.authMethod,
            clientSecretRef: serviceLassoOidcBootstrapDefaults.clientSecretRef,
          },
        },
      },
    },
  };
  const plan = planServiceLassoOidcBootstrap(state);
  assert.equal(plan.status, "already-present");
  assert.equal(plan.actions.every((action) => action.action.startsWith("verify_")), true);
  assertNoSecretMaterial(plan);
}

{
  const state = {
    projects: {
      "service-lasso": {
        name: "Old Service Lasso",
        applications: {
          "service-lasso-auth-facade": {
            name: "Service Lasso auth facade",
            redirectUris: ["https://auth.servicelasso.localhost/old-callback"],
            postLogoutRedirectUris: [],
            allowedOrigins: ["https://auth.servicelasso.localhost"],
            grantTypes: ["authorization_code"],
            responseTypes: ["code"],
            authMethod: "client_secret_post",
            clientSecretRef: "secretref://@secretsbroker/zitadel/old-client-secret",
          },
        },
      },
    },
  };
  const plan = planServiceLassoOidcBootstrap(state);
  assert.equal(plan.status, "update-required");
  assert.equal(plan.actions.some((action) => action.action === "update_project"), true);
  assert.equal(plan.actions.some((action) => action.action === "update_oidc_setting"), true);
  assert.equal(plan.actions.some((action) => action.action === "store_client_secret_ref"), true);
  assertNoSecretMaterial(plan);
}

assert.throws(
  () => assertSafeBootstrapConfig({ issuer: "https://zitadel.local", redirectUris: ["https://auth.local/oauth2/callback"] }),
  /servicelasso\.localhost|\.local/,
);

assert.throws(
  () => assertSafeBootstrapConfig({ clientSecretRef: "ACTUAL_CLIENT_SECRET" }),
  /secretref:\/\//,
);

{
  const tmp = await mkdtemp(path.join(os.tmpdir(), "lasso-zitadel-oidc-"));
  try {
    const outputPath = path.join(tmp, "metadata.json");
    const plan = planServiceLassoOidcBootstrap({});
    await writeSafeMetadata(outputPath, plan.safeMetadata);
    const written = await readFile(outputPath, "utf8");
    assert.match(written, /zitadel\.servicelasso\.localhost/);
    assert.doesNotMatch(written, /ACTUAL_CLIENT_SECRET|BEGIN PRIVATE KEY|refresh_token=|access_token=/i);
  } finally {
    await rm(tmp, { recursive: true, force: true });
  }
}

console.log("[lasso-zitadel] OIDC bootstrap tests passed");
