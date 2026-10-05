"""Outputs of the pinned upstream Nx/Buf/tsup generators, shared by both guards.

Contracts: apps/api/project.json, buf.gen.yaml, console/project.json,
console/buf.gen.yaml, packages/zitadel-proto/{project.json,buf.gen.yaml},
packages/zitadel-client/{project.json,tsup.config.ts}. These source files are
authenticated against upstream.tar.gz by verify_source, not exempted outputs.
"""
import hashlib
import pathlib
import tarfile
import sys
sys.dont_write_bytecode = True
from macos11_dependency_recipe import recipe

EXCLUDED = {'node_modules', '.nx', '.angular', '.artifacts', '.git'}
EXACT = {
    'internal/api/ui/login/statik/statik.go',
    'internal/notification/statik/statik.go', 'internal/statik/statik.go',
    'internal/api/assets/authz.go', 'internal/api/assets/router.go',
    'apps/docs/content/apis/assets/assets.mdx',
    'internal/api/ui/login/static/resources/themes/zitadel/css/zitadel.css',
    'internal/api/ui/login/static/resources/themes/zitadel/css/zitadel.css.map',
}
OUTPUTS = {
    # Buf's pinned Go plugins, including the two upstream custom generators.
    # Nx's directory copy/output glob also contains handwritten Go helpers.
    'pkg/grpc/': ('.pb.go', '_grpc.pb.go', '.pb.gw.go', '.pb.validate.go',
                  '.pb.authoptions.go', '.pb.zitadel.go', '.connect.go'),
    'openapi/v2/zitadel/': ('.json',),
    'console/src/app/proto/generated/': ('.js', '.ts', '.json'),
    'packages/zitadel-proto/cjs/': ('.js',),
    'packages/zitadel-proto/es/': ('.js',),
    'packages/zitadel-proto/types/': ('.d.ts',),
    'packages/zitadel-client/dist/': ('.js', '.cjs', '.d.ts', '.d.cts', '.js.map', '.cjs.map', '.d.ts.map', '.d.cts.map'),
    # Angular copies its complete dist tree, including fonts/images/LICENSE.
    'console/dist/': None,
    'internal/api/ui/console/static/': None,
}

def generated(relative):
    p = pathlib.PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or '\\' in relative:
        return False
    # The immutable upstream tree tracks this input beside copied Angular files.
    if relative == 'internal/api/ui/console/static/gitkeep':
        return False
    return relative in EXACT or any(
        relative.startswith(root) and (extensions is None or relative.endswith(extensions))
        for root, extensions in OUTPUTS.items())

def digest(path):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise SystemExit('Linked input refused: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_inventory(source):
    result = {}
    for p in sorted(source.rglob('*')):
        relative = p.relative_to(source)
        if EXCLUDED.intersection(relative.parts):
            continue
        if p.is_symlink():
            raise SystemExit('Linked source refused: ' + str(p))
        if p.is_file():
            result[relative.as_posix()] = digest(p)
    return result

def generated_inventory(inventory):
    return {relative: sha for relative, sha in inventory.items() if generated(relative)}

def verify_generated(inventory, recorded):
    if generated_inventory(inventory) != recorded:
        raise SystemExit('Complete generated asset inventory disagreement')

def verify_source(archive_path, inventory):
    dependencies = recipe()['files']
    original_paths = set()
    with tarfile.open(archive_path) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            relative = member.name.split('/', 1)[1]
            original_paths.add(relative)
            original = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            if relative in dependencies:
                if original != dependencies[relative]['before'] or inventory.get(relative) != dependencies[relative]['after']:
                    raise SystemExit('Authenticated dependency source drift: ' + relative)
                continue
            if inventory.get(relative) != original and not generated(relative):
                raise SystemExit('Ungenerated upstream source drift: ' + relative)
    for relative in sorted(inventory.keys() - original_paths):
        if not generated(relative):
            raise SystemExit('Unexpected non-generated source addition: ' + relative)
