import hashlib,json,os,pathlib,subprocess,sys
sys.dont_write_bytecode = True
from macos11_dependency_recipe import identity
from binary_symbols import inspect_symbols
from macos11_build_environment import record_environment
root,owned=map(pathlib.Path,sys.argv[1:])
recorded_environment=record_environment()
inspect_symbols('go',owned/'artifacts/zitadel',dict(os.environ,GOOS='linux'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
pins=json.loads((root/'toolchains/macos11/input-pins.json').read_text())
files=['upstream.tar.gz','go.tar.gz','go.src.tar.gz','recipe/go1.26.8.patch',
       'recipe/source-hashes.json','go/pkg/tool/linux_amd64/link','linker-build.log',
       'zitadel-build.log','asset-provenance.json','api-generator-inventory.json','module-verify.log','artifacts/zitadel']
doc={'profile':'custom-maintained-go1.26.8-darwin-amd64-macos11',
     'wrapperSHA':os.environ['WRAPPER_SHA'],'upstreamSHA':pins['upstreamSHA'],
     'brokerRecipeSHA':pins['brokerRecipeSHA'],'buildDate':os.environ['BUILD_DATE'],
     'version':'v4.14.0','linkFlags':'-linkmode=internal',
     'buildFlags':'-mod=readonly -x -work -trimpath',
     'binaryEnvironment':{'GOOS':'darwin','GOARCH':'amd64','GOAMD64':'v1','CGO_ENABLED':'0'},
     **recorded_environment,
     'hashes':{p:sha(owned/p) for p in files},
     'buildInformation':subprocess.check_output(['go','version','-m',str(owned/'artifacts/zitadel')],text=True)}
source=owned/('zitadel-'+pins['upstreamSHA'])
excluded={'node_modules','.nx','.angular','.artifacts','.git'}
doc['effectiveSourceHashes']={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*'))
                              if p.is_file() and not excluded.intersection(p.relative_to(source).parts)}
doc['dependencyRecipe'] = identity(root)
(owned/'artifacts/build-provenance.json').write_text(json.dumps(doc,indent=2)+'\n')
