#!/usr/bin/env bash
set -euo pipefail
umask 077
export PATH=/usr/local/bin:/usr/bin:/bin
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OWNED="${1:?completed private full-asset build directory}"
test -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)"
export WRAPPER_SHA="$(git -C "$ROOT" rev-parse HEAD)"
python3 "$ROOT/scripts/verify-macos11-inputs.py" "$ROOT" "$OWNED" pristine
python3 - "$ROOT" "$OWNED" <<'PY'
import hashlib,json,pathlib,re,sys
root,owned=map(pathlib.Path,sys.argv[1:])
pins=json.loads((root/'toolchains/macos11/input-pins.json').read_text())
if not re.fullmatch('[0-9a-f]{40}', pins.get('brokerRecipeSHA') or ''):
    raise SystemExit('Final reviewed immutable Broker recipe pin is required')
assets=json.loads((owned/'asset-provenance.json').read_text())
if assets['upstreamSHA']!=pins['upstreamSHA']:
    raise SystemExit('Asset/source identity disagreement')
source=owned/('zitadel-'+pins['upstreamSHA'])
for relative,digest in assets['generatedAssets'].items():
    if hashlib.sha256((source/relative).read_bytes()).hexdigest()!=digest:
        raise SystemExit('Generated asset drift: '+relative)
PY
RECIPE="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["brokerRecipeSHA"])' "$ROOT/toolchains/macos11/input-pins.json")"
mkdir "$OWNED/recipe"
for file in go1.26.8.patch source-hashes.json; do
  curl -fL "https://raw.githubusercontent.com/service-lasso/lasso-secretsbroker/$RECIPE/toolchains/macos11/$file" -o "$OWNED/recipe/$file"
done
echo "170a7b026b48999929a02c4a724a878f7837ee6fe62d829cfe0a276312a5e9f3  $OWNED/recipe/go1.26.8.patch" | sha256sum -c -
echo "02086a4ece2f4785c73aa601700723b21e7e2edf5c916084881f2f3e286ca870  $OWNED/recipe/source-hashes.json" | sha256sum -c -
curl -fL https://go.dev/dl/go1.26.8.src.tar.gz -o "$OWNED/go.src.tar.gz"
echo "4e39b98e42f946fa05ac8bc5b71877df97dbdb7cbb1a777b541667ad7117fd2e  $OWNED/go.src.tar.gz" | sha256sum -c -
python3 - "$OWNED" before <<'PY'
import hashlib,json,pathlib,sys,tarfile
owned=pathlib.Path(sys.argv[1]); root=owned/'go'
with tarfile.open(owned/'go.src.tar.gz') as archive:
    for name,hashes in json.load(open(owned/'recipe/source-hashes.json')).items():
        data=(root/name).read_bytes()
        if data!=archive.extractfile('go/'+name).read() or hashlib.sha256(data).hexdigest()!=hashes['before']:
            raise SystemExit('Official toolchain source disagreement: '+name)
PY
patch --batch --fuzz=0 -p1 -d "$OWNED/go" < "$OWNED/recipe/go1.26.8.patch"
python3 - "$OWNED" <<'PY'
import hashlib,json,pathlib,sys
owned=pathlib.Path(sys.argv[1])
for name,hashes in json.load(open(owned/'recipe/source-hashes.json')).items():
    if hashlib.sha256((owned/'go'/name).read_bytes()).hexdigest()!=hashes['after']:
        raise SystemExit('Toolchain patch mismatch: '+name)
PY
python3 "$ROOT/scripts/verify-macos11-inputs.py" "$ROOT" "$OWNED" patched
unset GOEXPERIMENT GOCOMPILEDEBUG GOTOOLDIR CC CXX FC AR LD CGO_CFLAGS CGO_CPPFLAGS CGO_CXXFLAGS CGO_LDFLAGS
export GOENV=off GOWORK=off GOTOOLCHAIN=local GOFLAGS= CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOAMD64=v1
export GOPROXY=https://proxy.golang.org,direct GOSUMDB=sum.golang.org GOPRIVATE= GONOPROXY= GONOSUMDB=
export GOROOT="$OWNED/go" GOCACHE="$OWNED/cache" GOMODCACHE="$OWNED/modcache" PATH="$OWNED/go/bin:/usr/local/bin:/usr/bin:/bin"
go build -x -work -trimpath -o "$GOROOT/pkg/tool/linux_amd64/link.owned" cmd/link 2> "$OWNED/linker-build.log"
mv "$GOROOT/pkg/tool/linux_amd64/link.owned" "$GOROOT/pkg/tool/linux_amd64/link"
python3 - "$OWNED" <<'PY'
import hashlib,json,pathlib,sys
owned=pathlib.Path(sys.argv[1])
(owned/'linker-inventory.json').write_text(json.dumps({'sha256':hashlib.sha256((owned/'go/pkg/tool/linux_amd64/link').read_bytes()).hexdigest()}))
PY
python3 "$ROOT/scripts/verify-macos11-inputs.py" "$ROOT" "$OWNED" linked
SOURCE=10b1af91d68700707d41e820545e478cf267511b
export BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir "$OWNED/artifacts"
cd "$OWNED/zitadel-$SOURCE"
go mod verify > "$OWNED/module-verify.log" 2>&1
CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 GOAMD64=v1 go build -mod=readonly -x -work -trimpath \
  -ldflags="-linkmode=internal -X github.com/zitadel/zitadel/cmd/build.commit=$SOURCE -X github.com/zitadel/zitadel/cmd/build.date=$BUILD_DATE -X github.com/zitadel/zitadel/cmd/build.version=v4.14.0" \
  -o "$OWNED/artifacts/zitadel" . 2> "$OWNED/zitadel-build.log"
python3 "$ROOT/scripts/verify-macos11-inputs.py" "$ROOT" "$OWNED" linked
python3 "$ROOT/scripts/record-macos11-build.py" "$ROOT" "$OWNED"
test "$(git -C "$ROOT" rev-parse HEAD)" = "$WRAPPER_SHA"
test -z "$(git -C "$ROOT" status --porcelain --untracked-files=all)"
