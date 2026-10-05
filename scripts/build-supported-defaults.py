"""AC-018: official-Go defaults from the authenticated full repaired source."""
import hashlib,importlib.util,json,os,pathlib,subprocess,sys,time
sys.dont_write_bytecode=True
from macos11_dependency_recipe import identity
root,owned=map(pathlib.Path,sys.argv[1:3])
spec=importlib.util.spec_from_file_location('security_runner',root/'scripts/run-macos11-security.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
def digest(p):
    if p.is_symlink(): raise SystemExit('Linked default input refused')
    return hashlib.sha256(p.read_bytes()).hexdigest()
def guard():
    subprocess.run([sys.executable,str(root/'scripts/verify-macos11-inputs.py'),str(root),str(owned),'pristine'],check=True)
guard()
assets=json.loads((owned/'asset-provenance.json').read_text())
source=owned/('zitadel-'+assets['upstreamSHA'])
directory=owned/'defaults';directory.mkdir()
env=dict(os.environ,GOENV='off',GOWORK='off',GOTOOLCHAIN='local',GOFLAGS='-p=2',CGO_ENABLED='0',GOARCH='amd64',GOAMD64='v1',
         GOROOT=str(owned/'go'),GOCACHE=str(owned/'cache'),GOMODCACHE=str(owned/'modcache'),
         GOMEMLIMIT='3GiB',GOMAXPROCS='2',PATH=f'{owned}/go/bin:/usr/bin:/bin',GOBIN=str(directory/'security-tools'))
for name in ('GOEXPERIMENT','GOCOMPILEDEBUG','GOTOOLDIR','CC','CXX','FC','AR','LD','CGO_CFLAGS','CGO_CPPFLAGS','CGO_CXXFLAGS','CGO_LDFLAGS'):
    env.pop(name,None)
env.update(GOPROXY='https://proxy.golang.org,direct',GOSUMDB='sum.golang.org',GOPRIVATE='',GONOPROXY='',GONOSUMDB='')
go=str(owned/'go/bin/go')
if subprocess.check_output([go,'version'],env=dict(env,GOOS='linux'),text=True).strip()!='go version go1.26.8 linux/amd64':
    raise SystemExit('Official maintained Go required')
(directory/'security-tools').mkdir()
runner.run_stage('default-install',[go,'install','golang.org/x/vuln/cmd/govulncheck@v1.7.0'],source,dict(env,GOOS='linux'),owned,600)
scanner=str(directory/'security-tools/govulncheck')
records={}
for platform,goos in [('win32','windows'),('linux','linux'),('darwin','darwin')]:
    target=directory/platform;target.mkdir()
    binary=target/('zitadel.exe' if platform=='win32' else 'zitadel')
    targetenv=dict(env,GOOS=goos)
    stamp=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    flags='-linkmode=internal -s -w -X github.com/zitadel/zitadel/cmd/build.commit='+assets['upstreamSHA']+' -X github.com/zitadel/zitadel/cmd/build.date='+stamp+' -X github.com/zitadel/zitadel/cmd/build.version=v4.14.0'
    with (target/'build.log').open('w') as log:
        subprocess.run([go,'build','-mod=readonly','-x','-work','-trimpath','-ldflags='+flags,'-o',str(binary),'.'],cwd=source,env=targetenv,stderr=log,check=True)
    (target/'modules.txt').write_text(subprocess.check_output([go,'version','-m',str(binary)],env=dict(env,GOOS='linux'),text=True))
    runner.run_stage('default-source-'+platform,[scanner,'./...'],source,targetenv,owned,2700)
    runner.run_stage('default-binary-'+platform,[scanner,'-mode=binary',str(binary)],source,dict(env,GOOS='linux'),owned,900)
    records[platform]={'goos':goos,'arch':'amd64','binarySHA256':digest(binary),
        'modulesSHA256':digest(target/'modules.txt'),'buildLogSHA256':digest(target/'build.log'),
        'source':{'target':goos+'/amd64','format':'text','exitCode':0,'reportSHA256':digest(owned/('security-default-source-'+platform+'.log'))},
        'binary':{'format':'text','exitCode':0,'reportSHA256':digest(owned/('security-default-binary-'+platform+'.log'))}}
guard()
doc={'schema':1,'profile':'authenticated-maintained-go1.26.8-defaults','wrapperSHA':assets['wrapperSHA'],
     'upstreamSHA':assets['upstreamSHA'],'dependencyRecipe':identity(root),'assetSHA256':digest(owned/'asset-provenance.json'),
     'generatorSHA256':digest(owned/'api-generator-inventory.json'),'toolchainArchiveSHA256':digest(owned/'go.tar.gz'),
     'environment':{k:env[k] for k in ('GOENV','GOWORK','GOTOOLCHAIN','CGO_ENABLED','GOARCH','GOAMD64')},
     'scanner':'golang.org/x/vuln/cmd/govulncheck@v1.7.0','scannerSHA256':digest(pathlib.Path(scanner)),'targets':records}
(directory/'provenance.json').write_text(json.dumps(doc,indent=2)+'\n')
