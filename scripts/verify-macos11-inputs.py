"""Authenticate archives and exact extracted build input, never just claims."""
import hashlib,json,os,pathlib,subprocess,sys,tarfile

root,owned=map(pathlib.Path,sys.argv[1:3])
stage=sys.argv[3]
pins=json.loads((root/'toolchains/macos11/input-pins.json').read_text())
assets=json.loads((owned/'asset-provenance.json').read_text())
head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
def digest(p):
    if p.is_symlink(): raise SystemExit('Linked input refused: '+str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest()
def equal(p,expected):
    if digest(p)!=expected: raise SystemExit('Input digest disagreement: '+str(p))
if assets['wrapperSHA']!=head or assets['upstreamSHA']!=pins['upstreamSHA']:
    raise SystemExit('Exact asset generation wrapper/source mismatch')
equal(owned/'upstream.tar.gz',pins['upstreamArchiveSHA256'])
equal(owned/'go.tar.gz','d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b')
source=owned/('zitadel-'+pins['upstreamSHA'])
for relative,expected in assets['lockfiles'].items(): equal(source/relative,expected)
excluded={'node_modules','.nx','.angular','.artifacts','.git'}
actual={str(p.relative_to(source)):digest(p) for p in sorted(source.rglob('*'))
        if p.is_file() and not excluded.intersection(p.relative_to(source).parts)}
if actual!=assets['effectiveSourceHashes']:
    raise SystemExit('Effective source inventory changed since full asset generation')
generated=('pkg/grpc/','openapi/v2/zitadel/','internal/api/ui/console/static/',
           'internal/api/ui/login/static/resources/themes/zitadel/css/',
           'internal/api/ui/login/statik/statik.go','internal/notification/statik/statik.go',
           'internal/statik/statik.go','internal/api/assets/authz.go','internal/api/assets/router.go',
           'apps/docs/content/apis/assets/assets.mdx','console/dist/',
           'console/src/app/proto/generated/','packages/zitadel-proto/src/',
           'packages/zitadel-proto/dist/',
           'packages/zitadel-client/dist/')
with tarfile.open(owned/'upstream.tar.gz') as archive:
    for member in archive.getmembers():
        if not member.isfile(): continue
        relative=member.name.split('/',1)[1]
        original=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
        if actual.get(relative)!=original and not relative.startswith(generated):
            raise SystemExit('Ungenerated upstream source drift: '+relative)
for relative,expected in assets['generatedAssets'].items(): equal(source/relative,expected)
for relative,expected in assets['tools'].items(): equal(source/'.artifacts/bin/linux/amd64'/relative,expected)
patches={}
if stage!='pristine':
    equal(owned/'go.src.tar.gz','4e39b98e42f946fa05ac8bc5b71877df97dbdb7cbb1a777b541667ad7117fd2e')
    equal(owned/'recipe/go1.26.8.patch','170a7b026b48999929a02c4a724a878f7837ee6fe62d829cfe0a276312a5e9f3')
    equal(owned/'recipe/source-hashes.json','02086a4ece2f4785c73aa601700723b21e7e2edf5c916084881f2f3e286ca870')
    patches=json.loads((owned/'recipe/source-hashes.json').read_text())
with tarfile.open(owned/'go.tar.gz') as archive:
    for member in archive.getmembers():
        if not member.isfile(): continue
        relative=member.name.removeprefix('go/')
        expected=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
        if relative in patches: expected=patches[relative]['after']
        if stage=='linked' and relative=='pkg/tool/linux_amd64/link':
            expected=json.loads((owned/'linker-inventory.json').read_text())['sha256']
        equal(owned/'go'/relative,expected)
for relative,expected in assets['buildTools'].items(): equal(owned/relative,expected)
print('Verified exact wrapper, authenticated archives, source, assets, locks and toolchain:',stage)
