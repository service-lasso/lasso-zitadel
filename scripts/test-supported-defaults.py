"""AC-018-3/5 rejection tests; synthetic metadata never qualifies binaries."""
import importlib.util,json,pathlib,subprocess,sys,tempfile
sys.dont_write_bytecode=True
from supported_default_fixtures import make_archive
root=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('supported',root/'scripts/verify-supported-defaults.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
count=0
with tempfile.TemporaryDirectory(prefix='zitadel18-boundary-') as directory:
    for platform,suffix in [('win32','zip'),('linux','tar.gz'),('darwin','tar.gz')]:
        archive=pathlib.Path(directory)/('fixture.'+suffix)
        def check(mutate=None,expected=False):
            global count
            make_archive(archive,platform,head,root,mutate)
            try:module.archive(archive,platform,head,inspector=lambda read,target:None);passed=True
            except (SystemExit,ValueError,KeyError):passed=False
            if passed!=expected:raise SystemExit('Unexpected default boundary result '+platform)
            count+=1
        check(expected=True)
        check(lambda f:f.update({'zitadel.exe' if platform=='win32' else 'zitadel':b'substituted affected binary'}))
        check(lambda f:f.update({'modules.txt':f['modules.txt'].replace(b'go1.26.8',b'go1.25.8')}))
        check(lambda f:f.update({'source-vulnerabilities.txt':b'substituted scan'}))
        check(lambda f:f.update({'api-generator-inventory.json':b'{}'}))
        def change_doc(key,value):
            def mutate(f):
                doc=json.loads(f['default-build-provenance.json']);doc[key]=value;f['default-build-provenance.json']=json.dumps(doc).encode()
            return mutate
        check(change_doc('wrapperSHA','f'*40))
        check(change_doc('dependencyRecipe',{}))
        check(change_doc('profile','official-baseline'))
        check(change_doc('toolchainArchiveSHA256','f'*64))
        check(change_doc('environment',{}))
        def failed_scan(f):
            doc=json.loads(f['default-build-provenance.json']);doc['targets'][platform]['binary']['exitCode']=3;f['default-build-provenance.json']=json.dumps(doc).encode()
        check(failed_scan)
        check(lambda f:f.update({'SERVICE-LASSO-PACKAGE.json':b'{"profile":"official-baseline"}'}))
print('Supported default boundaries passed:',count)
