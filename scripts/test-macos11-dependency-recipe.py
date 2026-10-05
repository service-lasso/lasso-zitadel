"""AC-017-1/3/4: strict lockfile overlay and archive/source custody."""
import copy
import difflib
import hashlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import sys
import subprocess
sys.dont_write_bytecode = True
from macos11_dependency_recipe import apply, recipe, identity
from macos11_generated_inventory import verify_source, source_inventory
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.directory = self.root / 'toolchains/macos11'
        self.directory.mkdir(parents=True)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.before = {'go.mod': b'module test\nrequire example.org/module v1.0.0\n',
                       'go.sum': b'example.org/module v1.0.0 h1:old\n'}
        self.after = {k: v.replace(b'v1.0.0', b'v1.1.0') for k, v in self.before.items()}
        diff = ''.join(''.join(difflib.unified_diff(self.before[k].decode().splitlines(True),
                       self.after[k].decode().splitlines(True), fromfile='a/'+k, tofile='b/'+k))
                       for k in ('go.mod', 'go.sum')).encode()
        (self.directory / 'dependencies.patch').write_bytes(diff)
        self.document = {'upstreamSHA': 'a'*40, 'patchSHA256': sha(diff),
                         'files': {k: {'before': sha(self.before[k]), 'after': sha(self.after[k])}
                                   for k in self.before}}
        (self.directory / 'input-pins.json').write_text(json.dumps({'upstreamSHA': 'a'*40}))
        subprocess.run(['git', 'init', '-b', 'develop', str(self.root)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.root), 'config', 'user.email', 'fixture@example.invalid'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'config', 'user.name', 'Fixture'], check=True)
        self.write_manifest()
        for relative, data in self.before.items():
            (self.source / relative).write_bytes(data)
        (self.source / 'auth.go').write_bytes(b'package auth\n')
        self.archive = self.root / 'upstream.tar.gz'
        with tarfile.open(self.archive, 'w:gz') as tar:
            for relative, data in (self.before | {'auth.go': b'package auth\n'}).items():
                member = tarfile.TarInfo('zitadel-test/' + relative)
                member.size = len(data)
                tar.addfile(member, io.BytesIO(data))

    def write_manifest(self):
        (self.directory / 'dependency-recipe.json').write_text(json.dumps(self.document))
        subprocess.run(['git', '-C', str(self.root), 'add', 'toolchains'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'commit', '--allow-empty', '-m', 'Fixture recipe'], check=True, capture_output=True)

    def verify(self):
        with patch('macos11_generated_inventory.recipe', lambda: recipe(self.root)):
            verify_source(self.archive, source_inventory(self.source))

    def test_legitimate_patch_and_replay(self):
        apply(self.source, self.root)
        self.verify()
        self.assertEqual(identity(self.root)['files'], self.document['files'])
        with self.assertRaisesRegex(SystemExit, 'original digest'):
            apply(self.source, self.root)

    def test_wrong_original_is_rejected_before_mutation(self):
        for relative in self.before:
            original = (self.source / relative).read_bytes()
            (self.source / relative).write_bytes(b'untrusted')
            with self.assertRaisesRegex(SystemExit, 'original digest'):
                apply(self.source, self.root)
            self.assertEqual((self.source / relative).read_bytes(), b'untrusted')
            (self.source / relative).write_bytes(original)

    def test_refreshed_inventory_cannot_hide_lock_or_source_drift(self):
        apply(self.source, self.root)
        for relative in ('go.mod', 'go.sum', 'auth.go'):
            original = (self.source / relative).read_bytes()
            for mutation in ('modify', 'delete'):
                with self.subTest(path=relative, mutation=mutation):
                    if mutation == 'modify':
                        (self.source / relative).write_bytes(b'tampered')
                    else:
                        (self.source / relative).unlink()
                    with self.assertRaises(SystemExit):
                        self.verify()
                    (self.source / relative).write_bytes(original)
        (self.source / 'injected.go').write_text('package injected')
        with self.assertRaisesRegex(SystemExit, 'Unexpected non-generated'):
            self.verify()

    def test_recipe_paths_hashes_and_upstream_are_fixed(self):
        authentic = copy.deepcopy(self.document)
        mutations = [lambda d: d['files'].pop('go.sum'),
                     lambda d: d['files'].update({'auth.go': d['files']['go.mod']}),
                     lambda d: d.update({'upstreamSHA': 'b'*40}),
                     lambda d: d['files']['go.mod'].update({'before': 'invalid'}),
                     lambda d: d.update({'patchSHA256': 'b'*64})]
        for mutation in mutations:
            self.document = copy.deepcopy(authentic)
            mutation(self.document)
            self.write_manifest()
            with self.assertRaises(SystemExit):
                recipe(self.root)
        self.document = authentic
        self.write_manifest()
        data = (self.directory / 'dependencies.patch').read_bytes()
        (self.directory / 'dependencies.patch').write_bytes(data + b'--- a/auth.go\n+++ b/auth.go\n')
        self.document['patchSHA256'] = sha((self.directory / 'dependencies.patch').read_bytes())
        self.write_manifest()
        with self.assertRaisesRegex(SystemExit, 'file inventory'):
            recipe(self.root)

    def test_wrong_after_hash_and_links(self):
        self.document['files']['go.mod']['after'] = 'b'*64
        self.write_manifest()
        with self.assertRaisesRegex(SystemExit, 'patched digest'):
            apply(self.source, self.root)
        (self.source / 'go.mod').write_bytes(self.before['go.mod'])
        path = self.source / 'go.sum'
        path.unlink()
        path.symlink_to(self.directory / 'dependencies.patch')
        with self.assertRaisesRegex(SystemExit, 'Linked dependency'):
            apply(self.source, self.root)

    def test_committed_recipe_valid(self):
        document = recipe()
        self.assertEqual(set(document['files']), {'go.mod', 'go.sum'})

    def test_uncommitted_recipe_cannot_redefine_custody(self):
        self.document['files']['go.mod']['after'] = 'b'*64
        (self.directory / 'dependency-recipe.json').write_text(json.dumps(self.document))
        with self.assertRaisesRegex(SystemExit, 'committed wrapper'):
            recipe(self.root)


if __name__ == '__main__':
    unittest.main()
