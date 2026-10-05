"""Bind publication to the real owner's actual issue comment and exact bytes."""
import hashlib,json,os,pathlib,re,sys
comments_path,assets_path,output_path=map(pathlib.Path,sys.argv[1:])
candidate=os.environ['GITHUB_SHA'];run_id=str(os.environ['GITHUB_RUN_ID'])
if not re.fullmatch('[a-f0-9]{40}',candidate): raise SystemExit('Invalid candidate SHA')
names=('lasso-zitadel-v4.14.0-darwin-amd64-macos11.tar.gz',
       'service-darwin-amd64-macos11.json','macos11-build-provenance.json',
       'macos11-asset-provenance.json','macos11-go-trust-probe-amd64',
       'macos11-api-generator-inventory.json','macos11-security-scan.json')
hashes={n:hashlib.sha256((assets_path/n).read_bytes()).hexdigest() for n in names}
build=json.loads((assets_path/'macos11-build-provenance.json').read_text())
assets=json.loads((assets_path/'macos11-asset-provenance.json').read_text())
pins=json.loads(pathlib.Path('toolchains/macos11/input-pins.json').read_text())
if build['wrapperSHA']!=candidate or assets['wrapperSHA']!=candidate or build['brokerRecipeSHA']!=pins['brokerRecipeSHA']:
    raise SystemExit('Candidate/source/recipe identity mismatch')
manifest=json.loads((assets_path/'service-darwin-amd64-macos11.json').read_text())
source=manifest['artifact']['source']
if source.get('repo')!='service-lasso/lasso-zitadel' or source.get('tag')!=os.environ['CANDIDATE_VERSION'] or 'channel' in source:
    raise SystemExit('Compatibility manifest must pin exact tag')
required=('native-host-roots-chain','native-wrong-hostname','native-current-time-positive',
          'native-current-time-negative','native-unknown-self-signed','go-custom-root-eku-pair',
          'native-process-local-anchor-eku-pair','independent-concurrent-chain-ownership',
          'live-trusted-https','macho-imports-minos-signing','version-help',
          'fresh-owned-postgresql-masterkey','trusted-tls-http2-ready','oidc-discovery-issuer',
          'console-shell-loaded-js','real-redirect-loginv1-form','stop-restart-retention',
          'zero-owned-processes')
pages=json.loads(comments_path.read_text())
comments=[c for page in pages for c in page] if pages and isinstance(pages[0],list) else pages
for comment in reversed(comments):
    if comment.get('user',{}).get('id')!=170312: continue
    body=comment.get('body','').strip()
    if not body.startswith('ZITADEL10_NATIVE_RECEIPT\n'): continue
    try: receipt=json.loads(body.split('\n',1)[1])
    except ValueError: continue
    if receipt.get('schema')!=1 or receipt.get('candidateSHA')!=candidate or str(receipt.get('workflowRunID'))!=run_id: continue
    host=receipt.get('host',{})
    if host.get('architecture')!='x86_64' or not re.fullmatch(r'11\.\d+\.\d+',host.get('version','')): continue
    if receipt.get('artifactSHA256')!=hashes or receipt.get('binarySHA256')!=build['hashes']['artifacts/zitadel']: continue
    if receipt.get('brokerRecipeSHA')!=pins['brokerRecipeSHA']: continue
    gates=receipt.get('gates',{})
    if set(gates)!=set(required) or any(gates[g] is not True for g in required): continue
    if not isinstance(receipt.get('evidence'),str) or not receipt['evidence'].strip(): continue
    receipt['githubComment']={'id':comment['id'],'url':comment['html_url'],'actualAuthorID':170312}
    output_path.write_text(json.dumps(receipt,indent=2)+'\n')
    print('Authorized exact-candidate actual Big Sur receipt verified');break
else: raise SystemExit('No complete owner-authored exact-candidate Big Sur receipt; publication blocked')
