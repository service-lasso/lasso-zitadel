"""Fixed create-only publication inventory, checksums and exact API readback."""
import hashlib,json,os,pathlib,re,sys
sys.dont_write_bytecode=True
import importlib.util
spec=importlib.util.spec_from_file_location('supported',pathlib.Path(__file__).parent/'verify-supported-defaults.py')
supported=importlib.util.module_from_spec(spec);spec.loader.exec_module(supported)
root=pathlib.Path(sys.argv[1]);mode=sys.argv[2]
names={'lasso-zitadel-v4.14.0-win32.zip','lasso-zitadel-v4.14.0-linux.tar.gz',
       'lasso-zitadel-v4.14.0-darwin.tar.gz','service.json',
       'lasso-zitadel-v4.14.0-darwin-amd64-macos11.tar.gz',
       'service-darwin-amd64-macos11.json','macos11-build-provenance.json',
       'macos11-asset-provenance.json','macos11-go-trust-probe-amd64',
       'macos11-api-generator-inventory.json','macos11-security-scan.json',
       'macos11-native-receipt.json'}
if mode!='write': names.add('SHA256SUMS.txt')
paths={p.name:p for p in root.iterdir()}
if set(paths)!=names or any(not p.is_file() or p.is_symlink() or p.stat().st_size<=0 for p in paths.values()):
    raise SystemExit('Unexpected/missing/linked/empty publication asset inventory')
for platform,name in [('win32','lasso-zitadel-v4.14.0-win32.zip'),('linux','lasso-zitadel-v4.14.0-linux.tar.gz'),('darwin','lasso-zitadel-v4.14.0-darwin.tar.gz')]:
    supported.archive(paths[name],platform,os.environ['GITHUB_SHA'])
hashes={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()}
if mode=='write':
    (root/'SHA256SUMS.txt').write_text(''.join(hashes[n]+'  '+n+'\n' for n in sorted(hashes)))
else:
    lines=(root/'SHA256SUMS.txt').read_text().splitlines()
    expected=[hashes[n]+'  '+n for n in sorted(names-{'SHA256SUMS.txt'})]
    if lines!=expected: raise SystemExit('Release checksum inventory disagreement')
if mode=='readback':
    doc=json.loads(pathlib.Path(sys.argv[3]).read_text())
    tag=os.environ['CANDIDATE_VERSION'];sha=os.environ['GITHUB_SHA']
    if not re.fullmatch(r'\d{4}\.\d{1,2}\.\d{1,2}-'+sha[:7],tag): raise SystemExit('Invalid candidate version binding')
    if doc.get('tagName')!=tag or doc.get('name')!=tag or doc.get('targetCommitish')!=sha or doc.get('isDraft') is not False or doc.get('isPrerelease') is not True:
        raise SystemExit('Published release identity disagreement')
    assets=doc.get('assets',[])
    if len(assets)!=len(names) or {a.get('name') for a in assets}!=names: raise SystemExit('Published asset inventory disagreement')
    for asset in assets:
        name=asset['name']
        if asset.get('digest')!='sha256:'+hashes[name] or asset.get('size')!=paths[name].stat().st_size:
            raise SystemExit('Published asset bytes/size mismatch: '+name)
print('Exact publication inventory verified:',mode)
