import json, os, pathlib, subprocess, sys
sys.dont_write_bytecode = True
from macos11_generated_inventory import source_inventory, generated_inventory, verify_source, digest
from macos11_dependency_recipe import identity

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
inventory = source_inventory(source)
verify_source(owned / 'upstream.tar.gz', inventory)

tools = source / '.artifacts/bin/linux/amd64'
document = {'wrapperSHA': os.environ['WRAPPER_SHA'], 'upstreamSHA': source_sha,
            'upstreamArchiveSHA256': digest(owned / 'upstream.tar.gz'),
            'nodeVersion': subprocess.check_output(['node','--version'],text=True).strip(),
            'pnpmVersion': subprocess.check_output(['pnpm','--version'],text=True).strip(),
            'goVersion': subprocess.check_output(['go','version'],text=True).strip(),
            'lockfiles': {p: digest(source / p) for p in ('pnpm-lock.yaml','go.mod','go.sum')},
            'tools': {p.name:digest(p) for p in sorted(tools.iterdir()) if p.is_file()},
            'generatedAssets': generated_inventory(inventory),
            'logs': {p:digest(owned / p) for p in ('pnpm-install.log','generate.log','build-console.log')}}
document['effectiveSourceHashes'] = inventory
document['dependencyRecipe'] = identity()

document['buildTools']={str(p.relative_to(owned)):digest(p) for p in [owned/'node-v22.23.3-linux-x64/bin/node',
    owned/'pnpm-runtime/node_modules/pnpm/bin/pnpm.cjs']+[p for p in (owned/'os-build-tools').rglob('*') if p.is_file()]}
document['generatorBuildInformation']={p.name:subprocess.run(['go','version','-m',str(p)],text=True,capture_output=True).stdout
                                     for p in sorted(tools.iterdir()) if p.is_file()}
document['apiGenerators']=json.loads((owned/'api-generator-inventory.json').read_text())
document['apiGeneratorInventorySHA256']=digest(owned/'api-generator-inventory.json')
(owned / 'asset-provenance.json').write_text(json.dumps(document,indent=2)+'\n')
