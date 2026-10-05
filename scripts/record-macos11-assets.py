import hashlib, json, os, pathlib, subprocess, sys

owned, source_sha = pathlib.Path(sys.argv[1]), sys.argv[2]
source = owned / ('zitadel-' + source_sha)
required = ['internal/statik/statik.go', 'internal/notification/statik/statik.go',
            'internal/api/ui/login/statik/statik.go',
            'internal/api/ui/login/static/resources/themes/zitadel/css/zitadel.css',
            'internal/api/ui/console/static/index.html', 'pkg/grpc', 'openapi/v2/zitadel']
for relative in required:
    if not (source / relative).exists():
        raise SystemExit('Missing required full-build asset: ' + relative)
console = source / 'internal/api/ui/console/static'
if not any(console.rglob('*.js')):
    raise SystemExit('Missing executable console JavaScript')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
roots = ['pkg/grpc', 'openapi/v2/zitadel', 'internal/api/ui/console/static',
         'internal/api/ui/login/static', 'internal/api/ui/login/statik',
         'internal/notification/statik', 'internal/statik', 'internal/api/assets']
files = sorted({p for root in roots for p in (source / root).rglob('*') if p.is_file()})
tools = source / '.artifacts/bin/linux/amd64'
document = {'wrapperSHA': os.environ['WRAPPER_SHA'], 'upstreamSHA': source_sha,
            'upstreamArchiveSHA256': digest(owned / 'upstream.tar.gz'),
            'nodeVersion': subprocess.check_output(['node','--version'],text=True).strip(),
            'pnpmVersion': subprocess.check_output(['pnpm','--version'],text=True).strip(),
            'goVersion': subprocess.check_output(['go','version'],text=True).strip(),
            'lockfiles': {p: digest(source / p) for p in ('pnpm-lock.yaml','go.mod','go.sum')},
            'tools': {p.name:digest(p) for p in sorted(tools.iterdir()) if p.is_file()},
            'generatedAssets': {str(p.relative_to(source)): digest(p) for p in files},
            'logs': {p:digest(owned / p) for p in ('pnpm-install.log','generate.log','build-console.log')}}
excluded={'node_modules','.nx','.angular','.artifacts','.git'}
document['effectiveSourceHashes']={str(p.relative_to(source)):digest(p) for p in sorted(source.rglob('*'))
                                   if p.is_file() and not excluded.intersection(p.relative_to(source).parts)}
document['buildTools']={str(p.relative_to(owned)):digest(p) for p in [owned/'node-v22.23.3-linux-x64/bin/node',
    owned/'pnpm-runtime/node_modules/pnpm/bin/pnpm.cjs']+[p for p in (owned/'os-build-tools').rglob('*') if p.is_file()]}
document['generatorBuildInformation']={p.name:subprocess.run(['go','version','-m',str(p)],text=True,capture_output=True).stdout
                                     for p in sorted(tools.iterdir()) if p.is_file()}
(owned / 'asset-provenance.json').write_text(json.dumps(document,indent=2)+'\n')
