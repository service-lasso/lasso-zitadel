"""Exact wrapper-owned two-lockfile security overlay; never generated source."""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
sys.dont_write_bytecode = True

FILES = {'go.mod', 'go.sum'}
ROOT = pathlib.Path(__file__).resolve().parent.parent


def digest(path):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise SystemExit('Linked dependency recipe/input refused: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recipe(root=ROOT):
    directory = root / 'toolchains/macos11'
    manifest = directory / 'dependency-recipe.json'
    digest(manifest)
    document = json.loads(manifest.read_text())
    if set(document) != {'upstreamSHA', 'patchSHA256', 'files'} or set(document['files']) != FILES:
        raise SystemExit('Dependency recipe requires exactly go.mod and go.sum')
    pins = json.loads((directory / 'input-pins.json').read_text())
    if document['upstreamSHA'] != pins['upstreamSHA']:
        raise SystemExit('Dependency recipe upstream disagreement')
    for hashes in document['files'].values():
        if set(hashes) != {'before', 'after'} or any(not re.fullmatch('[a-f0-9]{64}', v) for v in hashes.values()):
            raise SystemExit('Invalid dependency before/after digest')
    patch = directory / 'dependencies.patch'
    if digest(patch) != document['patchSHA256']:
        raise SystemExit('Dependency patch digest disagreement')
    headers = [line for line in patch.read_text().splitlines() if line.startswith(('--- ', '+++ '))]
    if headers != ['--- a/go.mod', '+++ b/go.mod', '--- a/go.sum', '+++ b/go.sum']:
        raise SystemExit('Dependency patch file inventory disagreement')
    for path in (manifest, patch):
        relative = path.relative_to(root).as_posix()
        committed = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:' + relative])
        if path.read_bytes() != committed:
            raise SystemExit('Dependency recipe differs from committed wrapper: ' + relative)
    return document


def identity(root=ROOT):
    document = recipe(root)
    return {'recipeSHA256': digest(root / 'toolchains/macos11/dependency-recipe.json'),
            'patchSHA256': document['patchSHA256'], 'files': document['files']}


def apply(source, root=ROOT):
    document = recipe(root)
    for relative, hashes in document['files'].items():
        if digest(source / relative) != hashes['before']:
            raise SystemExit('Dependency original digest disagreement: ' + relative)
    subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source),
                    '-i', str(root / 'toolchains/macos11/dependencies.patch')], check=True)
    for relative, hashes in document['files'].items():
        if digest(source / relative) != hashes['after']:
            raise SystemExit('Dependency patched digest disagreement: ' + relative)


if __name__ == '__main__':
    apply(pathlib.Path(sys.argv[1]))
