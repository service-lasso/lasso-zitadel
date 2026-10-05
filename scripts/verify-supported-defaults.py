"""Validate supported package proofs, both owned staging and final archives."""
import hashlib,json,os,pathlib,subprocess,sys,tarfile,tempfile,zipfile
sys.dont_write_bytecode=True
from macos11_dependency_recipe import identity
root=pathlib.Path(__file__).resolve().parent.parent
GO_HASH='d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b'
def digest(data): return hashlib.sha256(data).hexdigest()
def build_settings(modules,platform):
    required={'GOOS':{'win32':'windows','linux':'linux','darwin':'darwin'}[platform],
              'GOARCH':'amd64','GOAMD64':'v1','CGO_ENABLED':'0'}
    rows={}
    for line in modules.splitlines():
        if not line.startswith('\tbuild\t'):continue
        entry=line.removeprefix('\tbuild\t')
        if '=' not in entry:raise SystemExit('Malformed actual binary build setting')
        key,value=entry.split('=',1)
        if key in rows:raise SystemExit('Duplicate actual binary build setting')
        rows[key]=value
    if any(rows.get(k)!=v for k,v in required.items()):raise SystemExit('Actual binary target/portable CPU settings disagreement')
def validate(read,platform,head):
    doc=json.loads(read('default-build-provenance.json'));assets=json.loads(read('asset-provenance.json'))
    if doc.get('schema')!=1 or doc.get('profile')!='authenticated-maintained-go1.26.8-defaults' or doc.get('wrapperSHA')!=head:
        raise SystemExit('Default provenance profile/wrapper disagreement')
    recipe=identity(root)
    if doc.get('dependencyRecipe')!=recipe or assets.get('dependencyRecipe')!=recipe or assets.get('wrapperSHA')!=head or doc.get('upstreamSHA')!=assets.get('upstreamSHA'):
        raise SystemExit('Default authenticated source disagreement')
    if doc.get('assetSHA256')!=digest(read('asset-provenance.json')) or doc.get('generatorSHA256')!=digest(read('api-generator-inventory.json')) or doc.get('toolchainArchiveSHA256')!=GO_HASH:
        raise SystemExit('Default asset/toolchain disagreement')
    expected={'GOENV':'off','GOWORK':'off','GOTOOLCHAIN':'local','CGO_ENABLED':'0','GOARCH':'amd64','GOAMD64':'v1'}
    if doc.get('environment')!=expected or set(doc.get('targets',{}))!={'win32','linux','darwin'} or doc.get('scanner')!='golang.org/x/vuln/cmd/govulncheck@v1.7.0':
        raise SystemExit('Default build/scanner contract disagreement')
    target=doc['targets'][platform];goos={'win32':'windows','linux':'linux','darwin':'darwin'}[platform]
    if target.get('goos')!=goos or target.get('arch')!='amd64' or target.get('binarySHA256')!=digest(read('zitadel.exe' if platform=='win32' else 'zitadel')) or target.get('modulesSHA256')!=digest(read('modules.txt')):
        raise SystemExit('Default target/binary/module disagreement')
    modules=read('modules.txt').decode()
    if not modules.splitlines() or modules.splitlines()[0].rsplit(': ',1)[-1]!='go1.26.8':
        raise SystemExit('Default actual binary build information disagreement')
    build_settings(modules,platform)
    metadata=json.loads(read('SERVICE-LASSO-PACKAGE.json'))
    if metadata.get('profile')!=doc['profile'] or metadata.get('binarySource')!='authenticated-source-build' or metadata.get('wrapperCommit')!=head or metadata.get('binarySHA256')!=target['binarySHA256'] or metadata.get('platform')!=platform or metadata.get('arch')!='amd64' or metadata.get('upstream',{}).get('sourceCommit')!=doc['upstreamSHA']:
        raise SystemExit('Default package metadata disagreement')
    for kind in ('source','binary'):
        scan=target.get(kind,{})
        if scan.get('exitCode')!=0 or type(scan.get('exitCode')) is not int or scan.get('format')!='text' or scan.get('reportSHA256')!=digest(read(kind+'-vulnerabilities.txt')):
            raise SystemExit('Default exact security evidence disagreement')
    if target['source'].get('target')!=goos+'/amd64': raise SystemExit('Default source scan target disagreement')
    return doc
def inspect_binary(read,platform):
    """Derive module custody and re-scan actual bytes; never trust embedded claims."""
    env=dict(os.environ,GOENV='off',GOWORK='off',GOTOOLCHAIN='local',GOFLAGS='',GOOS='',GOARCH='',
             GOPROXY='https://proxy.golang.org,direct',GOSUMDB='sum.golang.org',GOPRIVATE='',GONOPROXY='',GONOSUMDB='',
             GOMAXPROCS='2',GOMEMLIMIT='3GiB')
    for name in ('GOEXPERIMENT','GOCOMPILEDEBUG','GOTOOLDIR','CC','CXX','FC','AR','LD','CGO_CFLAGS','CGO_CPPFLAGS','CGO_CXXFLAGS','CGO_LDFLAGS'):
        env.pop(name,None)
    version=subprocess.check_output(['go','version'],env=env,text=True).strip()
    if not version.startswith('go version go1.26.8 '): raise SystemExit('Independent official Go1.26.8 inspection required')
    with tempfile.TemporaryDirectory(prefix='zitadel18-final-inspection-') as temporary:
        directory=pathlib.Path(temporary);binary=directory/('zitadel.exe' if platform=='win32' else 'zitadel')
        binary.write_bytes(read(binary.name))
        actual=subprocess.check_output(['go','version','-m',str(binary)],env=env,text=True)
        build_settings(actual,platform)
        claimed=read('modules.txt').decode()
        def normalized(value):
            lines=value.splitlines()
            return [lines[0].rsplit(': ',1)[-1],*lines[1:]] if lines else []
        if normalized(actual)!=normalized(claimed): raise SystemExit('Actual binary module inventory differs from embedded proof')
        tools=directory/'scanner';tools.mkdir();env['GOBIN']=str(tools)
        subprocess.run(['go','install','golang.org/x/vuln/cmd/govulncheck@v1.7.0'],env=env,cwd=directory,check=True,timeout=600)
        scanner=tools/('govulncheck.exe' if os.name=='nt' else 'govulncheck')
        # Fresh trusted pinned scanner executes against the actual final bytes.
        # Default TEXT mode findings/errors/timeouts remain nonzero failures.
        subprocess.run([str(scanner),'-mode=binary',str(binary)],env=env,cwd=directory,check=True,timeout=900)
def archive(path,platform,head,inspector=inspect_binary):
    if path.suffix=='.zip':
        with zipfile.ZipFile(path) as z:
            names=z.namelist()
            if len(set(names))!=len(names) or any('/' in n or '\\' in n or n in ('.','..') for n in names): raise SystemExit('Unsafe default archive')
            validate(z.read,platform,head)
            inspector(z.read,platform)
    else:
        with tarfile.open(path) as t:
            members={m.name.removeprefix('./'):m for m in t.getmembers() if m.name not in ('.','./')}
            if len(members)!=len([m for m in t.getmembers() if m.name not in ('.','./')]) or any(not m.isfile() or '/' in n or '\\' in n or n in ('.','..') for n,m in members.items()): raise SystemExit('Unsafe default archive')
            read=lambda n:t.extractfile(members[n]).read()
            validate(read,platform,head)
            inspector(read,platform)
if __name__=='__main__':
    mode,directory,platform=sys.argv[1:4];head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if mode=='archive': archive(pathlib.Path(directory),platform,head)
    elif mode=='owned':
        owned=pathlib.Path(directory)
        subprocess.run([sys.executable,str(root/'scripts/verify-macos11-inputs.py'),str(root),str(owned),'pristine'],check=True)
        target=owned/'defaults'/platform
        files={'default-build-provenance.json':owned/'defaults/provenance.json','asset-provenance.json':owned/'asset-provenance.json','api-generator-inventory.json':owned/'api-generator-inventory.json',
            'source-vulnerabilities.txt':owned/('security-default-source-'+platform+'.log'),'binary-vulnerabilities.txt':owned/('security-default-binary-'+platform+'.log')}
        metadata={'profile':'authenticated-maintained-go1.26.8-defaults','binarySource':'authenticated-source-build','wrapperCommit':head,
                  'binarySHA256':json.loads((owned/'defaults/provenance.json').read_text())['targets'][platform]['binarySHA256'],
                  'platform':platform,'arch':'amd64','upstream':{'sourceCommit':json.loads((owned/'asset-provenance.json').read_text())['upstreamSHA']}}
        validate(lambda n:json.dumps(metadata).encode() if n=='SERVICE-LASSO-PACKAGE.json' else (files[n] if n in files else target/n).read_bytes(),platform,head)
    else: raise SystemExit('Unknown default verification mode')
