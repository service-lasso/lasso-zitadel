"""Synthetic boundary fixtures only: never real build or security acceptance."""
import hashlib,json,pathlib,tarfile,io,zipfile
from macos11_dependency_recipe import identity
def make_archive(path,platform,head,root,mutate=None):
    recipe=identity(root)
    binary=b'Synthetic boundary binary, not executable\n';report=b'Fixture scanner report; not scanner acceptance\n'
    goos={'win32':'windows','linux':'linux','darwin':'darwin'}[platform]
    modules=('fixture: go1.26.8\n\tbuild\tGOOS='+goos+'\n\tbuild\tGOARCH=amd64\n\tbuild\tGOAMD64=v1\n\tbuild\tCGO_ENABLED=0\n').encode()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    assets=json.dumps({'wrapperSHA':head,'upstreamSHA':recipe and '10b1af91d68700707d41e820545e478cf267511b','dependencyRecipe':recipe}).encode()
    generator=b'{"fixture":"not full generated acceptance"}'
    target={'goos':goos,'arch':'amd64','binarySHA256':sha(binary),'modulesSHA256':sha(modules),
            'source':{'target':goos+'/amd64','format':'text','exitCode':0,'reportSHA256':sha(report)},
            'binary':{'format':'text','exitCode':0,'reportSHA256':sha(report)}}
    doc={'schema':1,'profile':'authenticated-maintained-go1.26.8-defaults','wrapperSHA':head,
         'upstreamSHA':'10b1af91d68700707d41e820545e478cf267511b','dependencyRecipe':recipe,'assetSHA256':sha(assets),
         'generatorSHA256':sha(generator),'toolchainArchiveSHA256':'d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b',
         'environment':{'GOENV':'off','GOWORK':'off','GOTOOLCHAIN':'local','CGO_ENABLED':'0','GOARCH':'amd64','GOAMD64':'v1'},
         'scanner':'golang.org/x/vuln/cmd/govulncheck@v1.7.0','targets':dict.fromkeys(('win32','linux','darwin'),target)}
    metadata={'profile':doc['profile'],'binarySource':'authenticated-source-build','wrapperCommit':head,'binarySHA256':sha(binary),'platform':platform,'arch':'amd64','upstream':{'sourceCommit':doc['upstreamSHA']}}
    files={'zitadel.exe' if platform=='win32' else 'zitadel':binary,'modules.txt':modules,
           'asset-provenance.json':assets,'api-generator-inventory.json':generator,
           'source-vulnerabilities.txt':report,'binary-vulnerabilities.txt':report,
           'default-build-provenance.json':json.dumps(doc).encode(),'SERVICE-LASSO-PACKAGE.json':json.dumps(metadata).encode()}
    if mutate: mutate(files)
    if path.suffix=='.zip':
        with zipfile.ZipFile(path,'w') as z:
            for n,b in files.items():z.writestr(n,b)
    else:
        with tarfile.open(path,'w:gz') as t:
            for n,b in files.items():
                info=tarfile.TarInfo(n);info.size=len(b);t.addfile(info,io.BytesIO(b))
