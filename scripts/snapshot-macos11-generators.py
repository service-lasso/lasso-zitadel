import hashlib,json,pathlib,subprocess,sys
owned=pathlib.Path(sys.argv[1])
source=owned/'zitadel-10b1af91d68700707d41e820545e478cf267511b'
tools=source/'.artifacts/bin/linux/amd64'
document={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                   'buildInformation':subprocess.run(['go','version','-m',str(p)],text=True,capture_output=True).stdout}
          for p in sorted(tools.iterdir()) if p.is_file()}
(owned/'api-generator-inventory.json').write_text(json.dumps(document,indent=2)+'\n')
