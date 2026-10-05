"""Bounded generated output and authenticated source inventory regressions."""
import io
import hashlib
import pathlib
import tarfile
import tempfile
import unittest
import sys
sys.dont_write_bytecode = True
from macos11_generated_inventory import generated, generated_inventory, source_inventory, verify_source, verify_generated

class InventoryTests(unittest.TestCase):
    def test_pinned_outputs(self):
        paths = ['packages/zitadel-proto/cjs/zitadel/application/v2/api_pb.js',
                 'packages/zitadel-proto/es/zitadel/application/v2/api_pb.js',
                 'packages/zitadel-proto/types/zitadel/application/v2/api_pb.d.ts',
                 'packages/zitadel-client/dist/chunk-ABC.cjs.map',
                 'packages/zitadel-client/dist/v1.d.cts',
                 'console/src/app/proto/generated/zitadel/admin.swagger.json',
                 'pkg/grpc/zitadel/application.pb.go',
                 'pkg/grpc/admin/admin_grpc.pb.go',
                 'pkg/grpc/admin/admin.pb.gw.go',
                 'pkg/grpc/admin/admin.pb.validate.go',
                 'pkg/grpc/admin/admin.pb.authoptions.go',
                 'pkg/grpc/admin/admin.pb.zitadel.go',
                 'pkg/grpc/admin/adminconnect/admin.connect.go',
                 'openapi/v2/zitadel/admin.swagger.json',
                 'console/dist/console/media/logo.svg',
                 'internal/api/ui/console/static/3rdpartylicenses.txt',
                 'internal/api/ui/login/static/resources/themes/zitadel/css/zitadel.css.map']
        for p in paths:
            with self.subTest(path=p): self.assertTrue(generated(p))
        inventory = dict.fromkeys(paths, 'a' * 64)
        self.assertEqual(generated_inventory(inventory), inventory)

    def test_nonoutputs(self):
        for p in ['packages/zitadel-proto/src/evil.ts', 'packages/zitadel-proto/dist/evil.js',
                  'packages/zitadel-proto/types/evil.ts', 'packages/zitadel-proto/es/evil.go',
                  'packages/zitadel-proto/cjs/evil.json', 'pkg/grpc/evil.sh',
                  'pkg/grpc/action/action.go', 'pkg/grpc/app/application.go',
                  'pkg/grpc/user/user.go', 'pkg/grpc/admin/arbitrary.go',
                  'internal/api/ui/console/static/gitkeep',
                  'internal/api/assets/generator/evil.go', 'internal/statik/generate.go',
                  'internal/api/ui/login/static/evil.js',
                  'internal/api/ui/login/statik/statik.go.extra',
                  'packages/zitadel-proto/types/../../evil.d.ts', '/pkg/grpc/evil.go']:
            with self.subTest(path=p): self.assertFalse(generated(p))

    def test_archive_drift_and_additions(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = pathlib.Path(tmp) / 'upstream.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                member = tarfile.TarInfo('zitadel-fixed/packages/zitadel-proto/project.json')
                data = b'authenticated generator contract'
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))
            original = {'packages/zitadel-proto/project.json': hashlib.sha256(data).hexdigest()}
            legitimate = original | {'packages/zitadel-proto/types/zitadel/application/v2/api_pb.d.ts': 'a'*64}
            verify_source(archive, legitimate)
            for inventory in [legitimate | {'packages/zitadel-proto/src/evil.ts': 'a'*64},
                              legitimate | {'packages/zitadel-proto/types/evil.go': 'a'*64},
                              legitimate | {'packages/zitadel-proto/project.json': 'b'*64}, {}]:
                with self.assertRaises(SystemExit): verify_source(archive, inventory)

    def test_tracked_handwritten_source_stays_authenticated(self):
        # Representative real pinned inputs in directories receiving copied outputs.
        tracked = ['pkg/grpc/action/action.go', 'pkg/grpc/app/application.go',
                   'pkg/grpc/user/user.go', 'internal/api/ui/console/static/gitkeep']
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = root / 'source'
            source.mkdir()
            archive = root / 'upstream.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                for relative in tracked:
                    data = b'package action\nfunc Localizers() {}\n' if relative.endswith('.go') else b''
                    member = tarfile.TarInfo('zitadel-fixed/' + relative)
                    member.size = len(data)
                    tar.addfile(member, io.BytesIO(data))
                    path = source / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            authentic = source_inventory(source)
            verify_source(archive, authentic)
            self.assertEqual(generated_inventory(authentic), {})
            for relative in tracked:
                path = source / relative
                original = path.read_bytes()
                for mutation in ('modify', 'delete'):
                    with self.subTest(path=relative, mutation=mutation):
                        if mutation == 'modify':
                            path.write_bytes(original + b'changed')
                        else:
                            path.unlink()
                        inventory = source_inventory(source)
                        # A freshly recorded complete inventory must not waive source drift.
                        verify_generated(inventory, generated_inventory(inventory))
                        with self.assertRaisesRegex(SystemExit, 'Ungenerated upstream source drift'):
                            verify_source(archive, inventory)
                        path.write_bytes(original)
            added = source / 'pkg/grpc/action/arbitrary.go'
            added.write_text('package action\nfunc Injected() {}\n')
            inventory = source_inventory(source)
            with self.assertRaisesRegex(SystemExit, 'Unexpected non-generated source addition'):
                verify_source(archive, inventory)
            added.unlink()
            for basename in ('action.pb.go', 'action_grpc.pb.go', 'action.pb.gw.go',
                             'action.pb.validate.go', 'action.pb.authoptions.go',
                             'action.pb.zitadel.go', 'actionconnect/action.connect.go'):
                path = source / 'pkg/grpc/action' / basename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('generator output')
            inventory = source_inventory(source)
            verify_source(archive, inventory)
            self.assertEqual(len(generated_inventory(inventory)), 7)
            verify_generated(inventory, generated_inventory(inventory))

    def test_complete_inventory_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp)
            path = source / 'packages/zitadel-proto/types/api_pb.d.ts'
            path.parent.mkdir(parents=True)
            path.write_text('generated')
            recorded = generated_inventory(source_inventory(source))
            verify_generated(source_inventory(source), recorded)
            for incomplete in ({}, recorded | {'pkg/grpc/absent.go': 'a'*64}):
                with self.assertRaisesRegex(SystemExit, 'Complete generated'): verify_generated(source_inventory(source), incomplete)
            path.write_text('tampered')
            with self.assertRaisesRegex(SystemExit, 'Complete generated'): verify_generated(source_inventory(source), recorded)
            path.unlink()
            with self.assertRaisesRegex(SystemExit, 'Complete generated'): verify_generated(source_inventory(source), recorded)

    def test_linked_generated_file_and_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / 'source'
            source.mkdir()
            target = pathlib.Path(tmp) / 'outside'
            target.mkdir()
            (target / 'api_pb.d.ts').write_text('external')
            for directory in (False, True):
                link = source / ('types' if directory else 'api_pb.d.ts')
                link.symlink_to(target if directory else target/'api_pb.d.ts', target_is_directory=directory)
                try:
                    with self.assertRaisesRegex(SystemExit, 'Linked source refused'): source_inventory(source)
                finally: link.unlink()

if __name__ == '__main__': unittest.main()
