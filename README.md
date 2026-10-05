# lasso-zitadel

`lasso-zitadel` is the canonical Service Lasso service repo for packaging
ZITADEL as a release-backed optional managed service.

The repo builds authenticated ZITADEL v4.14.0 source with a bounded security
dependency overlay and complete upstream generated assets. Supported amd64
defaults use official maintained Go 1.26.8; the explicit Intel macOS 11 profile
uses its separately reviewed compatibility compiler. Original upstream release
archives remain baseline test inputs. The repo publishes qualified archives
through a manual, release-owner workflow dispatch from
the qualified `develop` revision, using the project version pattern:

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
- canonical `healthchecks[]` HTTP readiness check at `/debug/ready`
- default command line:
  `start-from-init --masterkeyFromEnv --tlsMode disabled`

For production/day-two operation, ZITADEL recommends separating init, setup, and
runtime phases. This package gives Service Lasso a working binary and manifest;
the consuming application owns the database and operational policy.

## Browser-local consumer topology

For a disposable local browser test, start from
[`examples/browser-local.service.json`](examples/browser-local.service.json).
It keeps PostgreSQL app-owned, receives the master key through a broker
reference, uses a generated `@localcert` certificate, serves trusted HTTPS with
HTTP/2, and sets Login V2 to `false` **before first instance creation** so the
supported embedded Login V1 route is available. Do not apply that Login V2
setting to a database that has already been initialized with a different login
configuration; use a fresh disposable database instead.

After the Service Lasso API, PostgreSQL, `@localcert`, and ZITADEL are running,
run the supplied smoke without passing an insecure TLS option:

```powershell
.\scripts\Test-ZitadelStartup.ps1 -RootCaPath <path-to-localcert-rootCA.pem>
```

The smoke verifies Service Lasso health, trusted HTTPS/HTTP2 readiness, OIDC
discovery and issuer consistency, the console shell and module, and a real
console authorization redirect to the Login V1 form. It intentionally does not
create a project, client, role, user, or persistent browser login.

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
$env:ZITADEL_SUPPORTED_BUILD = 'C:\absolute\completed-authenticated-build'
npm test
```

This runs OIDC bootstrap and browser-local topology contract tests, packages the
current platform, extracts the archive, verifies package metadata, and runs the
ZITADEL binary version/help commands from the extracted payload. Normal
packaging fails without an authenticated completed source build. The full
producer runs on a hosted Linux runner; Windows paths above illustrate native
package verification only. CI retains original upstream baseline tests with
the explicit `official-baseline` profile; baseline archives cannot enter the
protected final publication inventory. For the OIDC contract
tests only, run:

```powershell
npm run test:oidc
```
