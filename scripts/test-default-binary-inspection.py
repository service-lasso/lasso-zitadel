"""Defensive actual-module/scanner controls; no old affected executable test."""
import importlib.util,io,os,pathlib,subprocess,sys,tarfile,tempfile,unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
from binary_symbols import require_symbols, inspect_archive_symbols
root=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('supported',root/'scripts/verify-supported-defaults.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Inspection(unittest.TestCase):
    def test_compatibility_archive_inspects_actual_bytes_and_refuses_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=pathlib.Path(temporary)/'compatibility.tar.gz'
            def write(names,kind=tarfile.REGTYPE):
                with tarfile.open(path,'w:gz') as archive:
                    for name in names:
                        member=tarfile.TarInfo(name);member.type=kind
                        member.size=3 if kind==tarfile.REGTYPE else 0
                        archive.addfile(member,io.BytesIO(b'bin') if member.size else None)
            calls=[]
            def inspect(go,binary,env):calls.append(binary.read_bytes())
            write(['./zitadel'])
            inspect_archive_symbols(path,{},inspector=inspect)
            self.assertEqual(calls,[b'bin'])
            for names,kind in [([],tarfile.REGTYPE),(['zitadel','./zitadel'],tarfile.REGTYPE),
                               (['zitadel'],tarfile.SYMTYPE)]:
                write(names,kind)
                with self.assertRaises(SystemExit):inspect_archive_symbols(path,{},inspector=inspect)
            self.assertEqual(calls,[b'bin'])

    def test_required_scanner_symbols(self):
        good='140189cc0 R go:func.*\n140002200 T runtime.main\n'
        require_symbols(good)
        require_symbols(good.replace(' R ', ' r '))
        for bad in ['',good.replace('go:func.*','go.func.*'),good.replace('runtime.main','other.main'),
                    good.replace('140189cc0 R','0 R'),good.replace(' R ',' U '),
                    good+'140189cc0 R go:func.*\n']:
            with self.subTest(bad=bad),self.assertRaises(SystemExit):require_symbols(bad)

    def test_independent_modules_and_exact_bytes_scan(self):
        settings='\n\tbuild\tGOOS=linux\n\tbuild\tGOARCH=amd64\n\tbuild\tGOAMD64=v1\n\tbuild\tCGO_ENABLED=0\n'
        files={'zitadel':b'synthetic bytes','modules.txt':('claimed/path: go1.26.8'+settings).encode()}
        calls=[]
        def run(command,**kwargs):
            calls.append(command)
            if '-mode=binary' in command:self.assertEqual(pathlib.Path(command[-1]).read_bytes(),files['zitadel'])
        with patch.object(module.subprocess,'check_output',side_effect=['go version go1.26.8 linux/amd64','actual/path: go1.26.8'+settings,
             'go version go1.26.8 linux/amd64','140189cc0 R go:func.*\n140002200 T runtime.main\n']),patch.object(module.subprocess,'run',side_effect=run):
            module.inspect_binary(files.__getitem__,'linux')
        self.assertEqual(calls[0][1:],['install','golang.org/x/vuln/cmd/govulncheck@v1.7.0'])
        self.assertEqual(calls[1][1],'-mode=binary')
    def test_actual_metadata_mismatch_denied(self):
        with patch.object(module.subprocess,'check_output',side_effect=['go version go1.26.8 linux/amd64','actual: go1.26.8\n\tbuild\tGOOS=windows\n']),patch.object(module.subprocess,'run') as runner:
            with self.assertRaises(SystemExit):module.inspect_binary({'zitadel':b'fixture','modules.txt':b'claimed: go1.26.8\n\tbuild\tGOOS=linux\n'}.__getitem__,'linux')
            runner.assert_not_called()
    def test_scanner_failure_is_not_receipt(self):
        settings='\n\tbuild\tGOOS=linux\n\tbuild\tGOARCH=amd64\n\tbuild\tGOAMD64=v1\n\tbuild\tCGO_ENABLED=0\n'
        with patch.object(module.subprocess,'check_output',side_effect=['go version go1.26.8 linux/amd64','actual: go1.26.8'+settings,
             'go version go1.26.8 linux/amd64','140189cc0 R go:func.*\n140002200 T runtime.main\n']),patch.object(module.subprocess,'run',side_effect=[None,subprocess.CalledProcessError(3,['scanner'])]):
            with self.assertRaises(subprocess.CalledProcessError):module.inspect_binary({'zitadel':b'fixture','modules.txt':('claimed: go1.26.8'+settings).encode()}.__getitem__,'linux')
    def test_portable_cpu_settings(self):
        good='fixture: go1.26.8\n\tbuild\tGOOS=linux\n\tbuild\tGOARCH=amd64\n\tbuild\tGOAMD64=v1\n\tbuild\tCGO_ENABLED=0\n'
        module.build_settings(good,'linux')
        for bad in [good.replace('GOAMD64=v1','GOAMD64=v3'),good.replace('GOARCH=amd64','GOARCH=arm64'),
                    good.replace('\tbuild\tGOAMD64=v1\n',''),good+'\tbuild\tGOARCH=amd64\n',
                    good.replace('CGO_ENABLED=0','CGO_ENABLED=1'),good.replace('GOOS=linux','GOOS=darwin')]:
            with self.subTest(bad=bad),self.assertRaises(SystemExit):module.build_settings(bad,'linux')
    def test_missing_actual_symbols_prevents_scanner_and_receipt(self):
        settings='\n\tbuild\tGOOS=linux\n\tbuild\tGOARCH=amd64\n\tbuild\tGOAMD64=v1\n\tbuild\tCGO_ENABLED=0\n'
        with patch.object(module.subprocess,'check_output',side_effect=['go version go1.26.8 linux/amd64','actual: go1.26.8'+settings,
             'go version go1.26.8 linux/amd64','140002200 T runtime.main\n']),patch.object(module.subprocess,'run') as runner:
            with self.assertRaisesRegex(SystemExit,'function symbols'):
                module.inspect_binary({'zitadel':b'fixture','modules.txt':('claimed: go1.26.8'+settings).encode()}.__getitem__,'linux')
            runner.assert_not_called()

def real_control():
    with tempfile.TemporaryDirectory(prefix='zitadel18-benign-go-') as temporary:
        directory=pathlib.Path(temporary)
        (directory/'go.mod').write_text('module example.invalid/benign-inspection-control\n\ngo 1.26.8\n')
        (directory/'main.go').write_text('package main\nfunc main() {}\n')
        for platform,goos in [('win32','windows'),('linux','linux'),('darwin','darwin')]:
            binary=directory/('zitadel.exe' if platform=='win32' else 'zitadel')
            subprocess.run(['go','build','-o',str(binary),'.'],cwd=directory,env=dict(os.environ,GOOS=goos,GOARCH='amd64',GOAMD64='v1',CGO_ENABLED='0'),check=True)
            files={binary.name:binary.read_bytes(),'modules.txt':subprocess.check_output(['go','version','-m',str(binary)])}
            module.inspect_binary(files.__getitem__,platform)
            stripped=directory/('stripped.exe' if platform=='win32' else 'stripped')
            subprocess.run(['go','build','-ldflags=-s -w','-o',str(stripped),'.'],cwd=directory,env=dict(os.environ,GOOS=goos,GOARCH='amd64',GOAMD64='v1',CGO_ENABLED='0'),check=True)
            files={binary.name:stripped.read_bytes(),'modules.txt':subprocess.check_output(['go','version','-m',str(stripped)])}
            try:
                module.inspect_binary(files.__getitem__,platform)
            except (SystemExit,subprocess.CalledProcessError):
                pass
            else:
                raise AssertionError('Stripped actual binary was accepted: '+platform)
    print('Actual benign three-target Go metadata and pinned scanner controls passed')
if __name__=='__main__':
    if '--real' in sys.argv:real_control()
    else:unittest.main()
