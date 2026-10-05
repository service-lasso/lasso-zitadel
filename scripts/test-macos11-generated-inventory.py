"""Bounded generated output and authenticated source inventory regressions."""
import io
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
            import hashlib
            original = {'packages/zitadel-proto/project.json': hashlib.sha256(data).hexdigest()}
            legitimate = original | {'packages/zitadel-proto/types/zitadel/application/v2/api_pb.d.ts': 'a'*64}
            verify_source(archive, legitimate)
            for inventory in [legitimate | {'packages/zitadel-proto/src/evil.ts': 'a'*64},
                              legitimate | {'packages/zitadel-proto/types/evil.go': 'a'*64},
                              legitimate | {'packages/zitadel-proto/project.json': 'b'*64}, {}]:
                with self.assertRaises(SystemExit): verify_source(archive, inventory)

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
