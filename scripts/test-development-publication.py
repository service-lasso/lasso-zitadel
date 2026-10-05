"""AC-010-7 boundary tests; fixture receipts are never native acceptance."""
import copy,hashlib,json,os,pathlib,subprocess,sys,tempfile
sys.dont_write_bytecode=True
from supported_default_fixtures import make_archive
root=pathlib.Path(__file__).resolve().parent.parent
sha='a'*40;tag='2026.10.5-'+sha[:7]
pins=json.loads((root/'toolchains/macos11/input-pins.json').read_text())
env={**os.environ,'GITHUB_SHA':sha,'GITHUB_RUN_ID':'123456','CANDIDATE_VERSION':tag}
required=('native-host-roots-chain','native-wrong-hostname','native-current-time-positive',
          'native-current-time-negative','native-unknown-self-signed','go-custom-root-eku-pair',
          'native-process-local-anchor-eku-pair','independent-concurrent-chain-ownership',
          'live-trusted-https','macho-imports-minos-signing','version-help',
          'fresh-owned-postgresql-masterkey','trusted-tls-http2-ready','oidc-discovery-issuer',
          'console-shell-loaded-js','real-redirect-loginv1-form','stop-restart-retention',
          'zero-owned-processes')
count=0
def run(script,args,expected):
    global count
    if script=='verify-development-assets.py':
        # Synthetic proof fixtures exercise publisher boundaries through a unit
        # API adapter only. Production CLI always executes the real inspector.
        code="import importlib.util,pathlib,sys; sys.dont_write_bytecode=True; p=pathlib.Path(sys.argv[1]); sys.path.insert(0,str(p.parent)); s=importlib.util.spec_from_file_location('publisher',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.main(sys.argv[2:],archive_validator=lambda p,t,h:m.supported.archive(p,t,h,inspector=lambda r,t:None),compatibility_inspector=lambda p,e:None)"
        command=[sys.executable,'-c',code,str(root/'scripts'/script),*map(str,args)]
    else:command=[sys.executable,str(root/'scripts'/script),*map(str,args)]
    result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True)
    if (result.returncode==0)!=expected:
        raise SystemExit(script+' unexpected boundary result: '+result.stderr)
    count+=1
with tempfile.TemporaryDirectory(prefix='zitadel10-publication-boundaries-') as temporary:
    directory=pathlib.Path(temporary);assets=directory/'assets';assets.mkdir()
    receipt_names=('lasso-zitadel-v4.14.0-darwin-amd64-macos11.tar.gz',
        'service-darwin-amd64-macos11.json','macos11-build-provenance.json',
        'macos11-asset-provenance.json','macos11-go-trust-probe-amd64',
        'macos11-api-generator-inventory.json','macos11-security-scan.json')
    for name in receipt_names: (assets/name).write_text('non-native boundary fixture\n')
    (assets/'macos11-build-provenance.json').write_text(json.dumps({'wrapperSHA':sha,'brokerRecipeSHA':pins['brokerRecipeSHA'],'hashes':{'artifacts/zitadel':'b'*64}}))
    (assets/'macos11-asset-provenance.json').write_text(json.dumps({'wrapperSHA':sha}))
    (assets/'service-darwin-amd64-macos11.json').write_text(json.dumps({'artifact':{'source':{'repo':'service-lasso/lasso-zitadel','tag':tag}}}))
    hashes={n:hashlib.sha256((assets/n).read_bytes()).hexdigest() for n in receipt_names}
    receipt={'schema':1,'candidateSHA':sha,'workflowRunID':'123456','host':{'architecture':'x86_64','version':'11.7.11'},
             'artifactSHA256':hashes,'binarySHA256':'b'*64,'brokerRecipeSHA':pins['brokerRecipeSHA'],
             'gates':dict.fromkeys(required,True),'evidence':'Boundary test fixture only; no native result'}
    comments=directory/'comments.json';output=directory/'receipt.json'
    def check(value,author=170312,expected=False):
        comments.write_text(json.dumps([{'id':1,'html_url':'https://example.invalid/fixture','user':{'id':author},'body':'ZITADEL10_NATIVE_RECEIPT\n'+json.dumps(value)}]))
        run('verify-macos11-receipt.py',[comments,assets,output],expected)
    check(receipt,expected=True)
    check(receipt,author=999)
    for key,value in [('workflowRunID','789'),('candidateSHA','c'*40),('brokerRecipeSHA','c'*40),('schema',True)]:
        changed=copy.deepcopy(receipt);changed[key]=value;check(changed)
    changed=copy.deepcopy(receipt);changed['host']['version']='12.0.0';check(changed)
    changed=copy.deepcopy(receipt);changed['gates'].pop(required[-1]);check(changed)
    changed=copy.deepcopy(receipt);changed['gates'][required[0]]=1;check(changed)
    changed=copy.deepcopy(receipt);changed['artifactSHA256'][receipt_names[0]]='c'*64;check(changed)
    original=(assets/receipt_names[0]).read_bytes();(assets/receipt_names[0]).write_bytes(original+b'drift');check(receipt)
    (assets/receipt_names[0]).write_bytes(original)
    for name in ('lasso-zitadel-v4.14.0-win32.zip','lasso-zitadel-v4.14.0-linux.tar.gz','lasso-zitadel-v4.14.0-darwin.tar.gz','service.json','macos11-native-receipt.json'):
        (assets/name).write_text('Boundary asset\n')
    for platform,suffix in [('win32','zip'),('linux','tar.gz'),('darwin','tar.gz')]:
        make_archive(assets/f'lasso-zitadel-v4.14.0-{platform}.{suffix}',platform,sha,root)
    run('verify-development-assets.py',[assets,'write'],True)
    run('verify-development-assets.py',[assets,'verify'],True)
    (assets/'unexpected-file').write_text('extra');run('verify-development-assets.py',[assets,'verify'],False);(assets/'unexpected-file').unlink()
    checksum=(assets/'SHA256SUMS.txt').read_bytes();(assets/'SHA256SUMS.txt').write_bytes(checksum+checksum.splitlines(keepends=True)[0]);run('verify-development-assets.py',[assets,'verify'],False);(assets/'SHA256SUMS.txt').write_bytes(checksum)
    for omitted in checksum.splitlines(keepends=True):
        (assets/'SHA256SUMS.txt').write_bytes(checksum.replace(omitted,b''))
        run('verify-development-assets.py',[assets,'verify'],False)
    (assets/'SHA256SUMS.txt').write_bytes(checksum)
    for payload in assets.iterdir():
        if payload.name=='SHA256SUMS.txt': continue
        original=payload.read_bytes();payload.write_bytes(original+b'published drift')
        run('verify-development-assets.py',[assets,'verify'],False)
        payload.write_bytes(original)
    readback={'tagName':tag,'name':tag,'targetCommitish':sha,'isDraft':False,'isPrerelease':True,
              'assets':[{'name':p.name,'digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in assets.iterdir()]}
    remote=directory/'readback.json'
    def remote_check(doc,expected=False):
        remote.write_text(json.dumps(doc));run('verify-development-assets.py',[assets,'readback',remote],expected)
    remote_check(readback,True)
    changed=copy.deepcopy(readback);changed['targetCommitish']='develop';remote_check(changed)
    changed=copy.deepcopy(readback);changed['assets'][0]['digest']='sha256:'+'c'*64;remote_check(changed)
    changed=copy.deepcopy(readback);changed['assets'][0]['size']+=1;remote_check(changed)
    changed=copy.deepcopy(readback);changed['assets'].append(changed['assets'][0]);remote_check(changed)
    changed=copy.deepcopy(readback);changed['isPrerelease']=False;remote_check(changed)
print(f'{count} publication identity/owner/hash/negative boundary checks passed; no native acceptance claim')
