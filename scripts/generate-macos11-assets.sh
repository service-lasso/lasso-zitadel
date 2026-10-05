#!/usr/bin/env bash
# Full upstream browser and API assets in a new private workspace.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
test -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)"
OWNED="${1:?new absolute owned build directory}"
case "$OWNED" in /*) ;; *) exit 2;; esac
test ! -e "$OWNED"
mkdir -m 700 "$OWNED"
export OWNED WRAPPER_SHA="$(git -C "$ROOT" rev-parse HEAD)"
export PATH=/usr/local/bin:/usr/bin:/bin
export GOENV=off GOWORK=off GOTOOLCHAIN=local GOFLAGS= CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOAMD64=v1
export GOPROXY=https://proxy.golang.org,direct GOSUMDB=sum.golang.org GOPRIVATE= GONOPROXY= GONOSUMDB=
unset GOEXPERIMENT GOCOMPILEDEBUG GOTOOLDIR CC CXX FC AR LD CGO_CFLAGS CGO_CPPFLAGS CGO_CXXFLAGS CGO_LDFLAGS
SOURCE=10b1af91d68700707d41e820545e478cf267511b
curl -fL "https://codeload.github.com/zitadel/zitadel/tar.gz/$SOURCE" -o "$OWNED/upstream.tar.gz"
echo "b9e674b87de68541639aef83f6fa4da4fe75d857cce65606a72197acfd0efdfd  $OWNED/upstream.tar.gz" | sha256sum -c -
tar -xzf "$OWNED/upstream.tar.gz" -C "$OWNED"
python3 "$ROOT/scripts/macos11_dependency_recipe.py" "$OWNED/zitadel-$SOURCE"
curl -fL https://go.dev/dl/go1.26.8.linux-amd64.tar.gz -o "$OWNED/go.tar.gz"
echo "d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b  $OWNED/go.tar.gz" | sha256sum -c -
tar -xzf "$OWNED/go.tar.gz" -C "$OWNED"
curl -fL https://nodejs.org/dist/v22.23.3/node-v22.23.3-linux-x64.tar.xz -o "$OWNED/node.tar.xz"
# The digest is frozen from the official version-specific checksum inventory.
NODE_HASH="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["nodeArchiveSHA256"])' "$ROOT/toolchains/macos11/input-pins.json")"
echo "$NODE_HASH  $OWNED/node.tar.xz" | sha256sum -c -
tar -xf "$OWNED/node.tar.xz" -C "$OWNED"
export GOROOT="$OWNED/go" GOCACHE="$OWNED/cache" GOMODCACHE="$OWNED/modcache"
export PATH="$GOROOT/bin:$OWNED/node-v22.23.3-linux-x64/bin:$PATH"
test "$(go version)" = 'go version go1.26.8 linux/amd64'
test "$(node --version)" = v22.23.3
npm install --prefix "$OWNED/pnpm-runtime" pnpm@10.30.3 > "$OWNED/pnpm-runtime.log" 2>&1
export PATH="$OWNED/pnpm-runtime/node_modules/.bin:$PATH"
test "$(pnpm --version)" = 10.30.3
if ! command -v unzip >/dev/null; then
  mkdir "$OWNED/os-build-tools"
  curl -fL https://archive.ubuntu.com/ubuntu/pool/main/u/unzip/unzip_6.0-28ubuntu4.1_amd64.deb -o "$OWNED/os-build-tools/unzip.deb"
  echo "a505b9d491386167bd8e14e3383315a4a7d6539e4406745901ccf009a7988271  $OWNED/os-build-tools/unzip.deb" | sha256sum -c -
  dpkg-deb -x "$OWNED/os-build-tools/unzip.deb" "$OWNED/os-build-tools/root"
  export PATH="$OWNED/os-build-tools/root/usr/bin:$PATH"
fi
cd "$OWNED/zitadel-$SOURCE"
sha256sum pnpm-lock.yaml go.mod go.sum > "$OWNED/lockfiles.before"
export NX_DAEMON=false NX_SKIP_NX_CACHE=true NX_NO_CLOUD=true
pnpm install --frozen-lockfile --store-dir "$OWNED/pnpm-store" > "$OWNED/pnpm-install.log" 2>&1
pnpm nx run @zitadel/api:generate --skip-nx-cache > "$OWNED/generate.log" 2>&1
python3 "$ROOT/scripts/snapshot-macos11-generators.py" "$OWNED"
pnpm nx run @zitadel/api:build-console --skip-nx-cache > "$OWNED/build-console.log" 2>&1
sha256sum -c "$OWNED/lockfiles.before"
python3 "$ROOT/scripts/record-macos11-assets.py" "$OWNED" "$SOURCE"
test "$(git -C "$ROOT" rev-parse HEAD)" = "$WRAPPER_SHA"
test -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)"
