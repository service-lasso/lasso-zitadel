"""Defensive actual-module/scanner controls; no old affected executable test."""
import importlib.util,os,pathlib,subprocess,sys,tempfile,unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
root=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('supported',root/'scripts/verify-supported-defaults.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Inspection(unittest.TestCase):
    def test_independent_modules_and_exact_bytes_scan(self):
        settings='\n\tbuild\tGOOS=linux\n\tbuild\tGOARCH=amd64\n\tbuild\tGOAMD64=v1\n\tbuild\tCGO_ENABLED=0\n'
        files={'zitadel':b'synthetic bytes','modules.txt':('claimed/path: go1.26.8'+settings).encode()}
        calls=[]
        def run(command,**kwargs):
            calls.append(command)
            if '-mode=binary' in command:self.assertEqual(pathlib.Path(command[-1]).read_bytes(),files['zitadel'])
        with patch.object(module.subprocess,'check_output',side_effect=['go version go1.26.8 linux/amd64','actual/path: go1.26.8'+settings]),patch.object(module.subprocess,'run',side_effect=run):
            module.inspect_binary(files.__getitem__,'linux')
        self.assertEqual(calls[0][1:],['install','golang.org/x/vuln/cmd/govulncheck@v1.7.0'])
        self.assertEqual(calls[1][1],'-mode=binary')
    def test_actual_metadata_mismatch_denied(self):
        with patch.object(module.subprocess,'check_output',side_effect=['go version go1.26.8 linux/amd64','actual: go1.26.8\n\tbuild\tGOOS=windows\n']),patch.object(module.subprocess,'run') as runner:
            with self.assertRaises(SystemExit):module.inspect_binary({'zitadel':b'fixture','modules.txt':b'claimed: go1.26.8\n\tbuild\tGOOS=linux\n'}.__getitem__,'linux')
            runner.assert_not_called()
    def test_scanner_failure_is_not_receipt(self):
        settings='\n\tbuild\tGOOS=linux\n\tbuild\tGOARCH=amd64\n\tbuild\tGOAMD64=v1\n\tbuild\tCGO_ENABLED=0\n'
        with patch.object(module.subprocess,'check_output',side_effect=['go version go1.26.8 linux/amd64','actual: go1.26.8'+settings]),patch.object(module.subprocess,'run',side_effect=[None,subprocess.CalledProcessError(3,['scanner'])]):
            with self.assertRaises(subprocess.CalledProcessError):module.inspect_binary({'zitadel':b'fixture','modules.txt':('claimed: go1.26.8'+settings).encode()}.__getitem__,'linux')
    def test_portable_cpu_settings(self):
        good='fixture: go1.26.8\n\tbuild\tGOOS=linux\n\tbuild\tGOARCH=amd64\n\tbuild\tGOAMD64=v1\n\tbuild\tCGO_ENABLED=0\n'
        module.build_settings(good,'linux')
        for bad in [good.replace('GOAMD64=v1','GOAMD64=v3'),good.replace('GOARCH=amd64','GOARCH=arm64'),
                    good.replace('\tbuild\tGOAMD64=v1\n',''),good+'\tbuild\tGOARCH=amd64\n',
                    good.replace('CGO_ENABLED=0','CGO_ENABLED=1'),good.replace('GOOS=linux','GOOS=darwin')]:
            with self.subTest(bad=bad),self.assertRaises(SystemExit):module.build_settings(bad,'linux')
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
    print('Actual benign three-target Go metadata and pinned scanner controls passed')
if __name__=='__main__':
    if '--real' in sys.argv:real_control()
    else:unittest.main()
