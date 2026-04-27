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

## Local Verification

```powershell
npm test
```

This packages the current platform, extracts the archive, verifies package
metadata, and runs the ZITADEL binary version command from the extracted payload.
