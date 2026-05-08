# lasso-zitadel

`lasso-zitadel` is the canonical Service Lasso service repo for packaging
ZITADEL as a release-backed optional managed service.

The repo does not fork ZITADEL. It downloads official `zitadel/zitadel` release
archives, wraps them in Service Lasso-compatible platform archives, and
publishes those archives from protected `main` pushes using the project version
pattern:

```text
yyyy.m.d-<shortsha>
```

## Runtime Requirements

ZITADEL requires:

- PostgreSQL 14 through 18.
- A stable 32-byte master key. Do not rotate it casually; encrypted data depends
  on it.
- `ZITADEL_DATABASE_POSTGRES_DSN` in the service process environment.
- `ZITADEL_MASTERKEY` in the service process environment when using the default
  Service Lasso command line.

The released manifest is disabled by default. A consuming project should copy or
reference `services/zitadel/service.json`, provide the database/masterkey
environment, and then enable the service.

## Release Assets

Each release publishes ZITADEL `v4.14.0` amd64 archives for each supported
platform:

- `lasso-zitadel-v4.14.0-win32.zip`
- `lasso-zitadel-v4.14.0-linux.tar.gz`
- `lasso-zitadel-v4.14.0-darwin.tar.gz`
- `service.json`
- `SHA256SUMS.txt`

The released `service.json` keeps `artifact.source.channel` set to `latest` for
new consumers. Apps that need pinned behavior can replace `channel` with the
verified release tag.

## Service Lasso Contract

The service manifest declares:

- optional managed service, `enabled: false` by default
- native archive acquisition from GitHub releases
- HTTP port mapping through `ZITADEL_PORT` and `ZITADEL_EXTERNALPORT`
- local HTTP healthcheck at `/debug/ready`
- default command line:
  `start-from-init --masterkeyFromEnv --tlsMode disabled`

For production/day-two operation, ZITADEL recommends separating init, setup, and
runtime phases. This package gives Service Lasso a working binary and manifest;
the consuming application owns the database and operational policy.

## Service Lasso OIDC bootstrap

`npm run bootstrap:oidc` provides the Service Lasso-side bootstrap contract for
the ZITADEL OIDC application used by the Traefik OIDC middleware. The script is safe
to run repeatedly: it compares a supplied state snapshot with the desired
Service Lasso OIDC project/application settings and emits a create, update, or
already-present plan plus metadata that the Traefik OIDC middleware can consume.

Default local SSO endpoints:

```text
issuer:                 https://zitadel.servicelasso.localhost
redirect URI:           https://auth.servicelasso.localhost/oauth2/callback
post-logout redirect:   https://auth.servicelasso.localhost/logout/callback
allowed origins:        https://auth.servicelasso.localhost
                        https://serviceadmin.servicelasso.localhost
client secret storage:  secretref://@secretsbroker/zitadel/traefik-oidc-auth/client-secret
metadata output:        runtime/service-lasso-oidc.metadata.json
```

The bootstrap output is metadata-only. It may include issuer, client id,
redirect/post-logout URIs, allowed origins, and a `secretref://` pointer for the
client secret. It must not print or write raw client secrets, access tokens, ID
tokens, refresh tokens, session cookies, private keys, provider credentials, or
database passwords.

Example dry state-driven run:

```powershell
$env:ZITADEL_BOOTSTRAP_STATE = "runtime\zitadel-state.snapshot.json"
$env:ZITADEL_BOOTSTRAP_METADATA_PATH = "runtime\service-lasso-oidc.metadata.json"
npm run bootstrap:oidc
```

The state snapshot shape used by tests is intentionally small and mirrors the
bootstrap contract rather than ZITADEL internals:

```json
{
  "projects": {
    "service-lasso": {
      "name": "Service Lasso",
      "applications": {
        "traefik-oidc-auth": {
          "name": "Service Lasso Traefik OIDC middleware",
          "redirectUris": ["https://auth.servicelasso.localhost/oauth2/callback"],
          "postLogoutRedirectUris": ["https://auth.servicelasso.localhost/logout/callback"],
          "allowedOrigins": ["https://auth.servicelasso.localhost"],
          "grantTypes": ["authorization_code", "refresh_token"],
          "responseTypes": ["code"],
          "authMethod": "client_secret_basic",
          "clientSecretRef": "secretref://@secretsbroker/zitadel/traefik-oidc-auth/client-secret"
        }
      }
    }
  }
}
```

Later API-backed bootstrap code should use this same safe output boundary while
mapping the plan actions to ZITADEL management API calls.

## Local Verification

```powershell
npm test
```

This runs OIDC bootstrap contract tests, packages the current platform, extracts
the archive, verifies package metadata, and runs the ZITADEL binary version
command from the extracted payload. For the OIDC contract tests only, run:

```powershell
npm run test:oidc
```
