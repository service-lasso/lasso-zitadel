#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OWNED="${1:?completed private build directory}"
mkdir "$OWNED/native-inputs" "$OWNED/official-go" "$OWNED/native-probes"
python3 - "$ROOT" "$OWNED" <<'PY'
import hashlib,json,pathlib,re,sys,urllib.request
root,owned=map(pathlib.Path,sys.argv[1:])
sha=json.loads((root/'toolchains/macos11/input-pins.json').read_text())['brokerRecipeSHA']
if not re.fullmatch('[a-f0-9]{40}',sha): raise SystemExit('Immutable approved Broker recipe required')
for name,expected in json.loads((root/'toolchains/macos11/native-inputs.json').read_text()).items():
    path=pathlib.PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts: raise SystemExit('Unsafe native source path')
    data=urllib.request.urlopen('https://raw.githubusercontent.com/service-lasso/lasso-secretsbroker/'+sha+'/'+name).read()
    if hashlib.sha256(data).hexdigest()!=expected: raise SystemExit('Native fixture source drift: '+name)
    destination=owned/'native-inputs'/name;destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(data)
PY
echo "d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b  $OWNED/go.tar.gz" | sha256sum -c -
tar -xzf "$OWNED/go.tar.gz" -C "$OWNED/official-go"
unset GOEXPERIMENT GOCOMPILEDEBUG GOTOOLDIR CC CXX FC AR LD CGO_CFLAGS CGO_CPPFLAGS CGO_CXXFLAGS CGO_LDFLAGS
export GOENV=off GOFLAGS= GOWORK=off GOTOOLCHAIN=local GOAMD64=v1 CGO_ENABLED=0
for arch in amd64 arm64; do
  for profile in official custom; do
    if test "$profile" = official; then goroot="$OWNED/official-go/go"; else goroot="$OWNED/go"; fi
    GOROOT="$goroot" GOCACHE="$OWNED/probe-cache-$profile" GOMODCACHE="$OWNED/probe-modcache" GOOS=darwin GOARCH="$arch" \
      "$goroot/bin/go" build -trimpath -ldflags=-linkmode=internal -o "$OWNED/native-probes/$profile-$arch" "$OWNED/native-inputs/verify/macos11/go-trust-probe.go"
  done
done
python3 "$OWNED/native-inputs/scripts/check-compat-macho.py" "$OWNED/artifacts/zitadel" "$OWNED/native-probes/custom-amd64" "$OWNED/native-probes/custom-arm64" > "$OWNED/native-probes/macho.json"
cp "$OWNED/native-inputs/verify/macos11/"*.mjs "$OWNED/native-probes/"
cp "$OWNED/native-inputs/verify/macos11/native/apple-trust.c" "$OWNED/native-probes/"
cp "$ROOT/toolchains/macos11/native-inputs.json" "$OWNED/native-probes/fixture-source-hashes.json"
cd "$OWNED/native-probes"
sha256sum ./* > SHA256SUMS.txt
