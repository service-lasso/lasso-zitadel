import hashlib,json,pathlib,subprocess,sys
owned=pathlib.Path(sys.argv[1])
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
scanner=owned/'security-tools/govulncheck'
build=json.loads((owned/'artifacts/build-provenance.json').read_text())
doc={'candidateSHA':build['wrapperSHA'],'binarySHA256':digest(owned/'artifacts/zitadel'),
     'scanner':'golang.org/x/vuln/cmd/govulncheck@v1.7.0','scannerSHA256':digest(scanner),
     'scannerBuildInformation':subprocess.check_output([str(owned/'go/bin/go'),'version','-m',str(scanner)],text=True),
     'source':{'target':'darwin/amd64','mode':'source','format':'text','exitCode':0,
               'reportSHA256':digest(owned/'source-vulnerabilities.txt')},
     'binary':{'mode':'binary','format':'text','exitCode':0,
               'reportSHA256':digest(owned/'binary-vulnerabilities.txt')}}
(owned/'security-scan.json').write_text(json.dumps(doc,indent=2)+'\n')
