"""Require the function data used by pinned govulncheck v1.7.0.

Its buildinfo/additions_scan.go falls back to all module advisories if symbols
are stripped. Go >=1.20 uses go:func.*; Mach-O also requires runtime.main.
"""
import pathlib, re, subprocess, tarfile, tempfile


def require_symbols(output):
    symbols = {}
    for line in output.splitlines():
        match = re.fullmatch(r'\s*([0-9a-fA-F]+)\s+([A-Za-z?])\s+(\S+)\s*', line)
        if match and int(match[1], 16) != 0:
            symbols.setdefault(match[3], []).append(match[2])
    marker = symbols.get('go:func.*', [])
    main = symbols.get('runtime.main', [])
    if len(marker) != 1 or marker[0] not in 'Rr' or len(main) != 1 or main[0] not in 'Tt':
        raise SystemExit('Actual binary lacks unique Go scanner function symbols')


def inspect_symbols(go, binary, env):
    version = subprocess.check_output([str(go), 'version'], env=env, text=True).strip()
    if not version.startswith('go version go1.26.8 '):
        raise SystemExit('Official maintained Go1.26.8 symbol inspection required')
    require_symbols(subprocess.check_output([str(go), 'tool', 'nm', str(binary)],
                                           env=env, text=True, timeout=120))


def inspect_archive_symbols(path, env, inspector=inspect_symbols):
    with tarfile.open(path) as archive:
        members = {}
        for member in archive.getmembers():
            if member.name in ('.', './'):
                if not member.isdir():
                    raise SystemExit('Compatibility archive root must be a directory')
                continue
            name = member.name.removeprefix('./')
            if not member.isfile() or not name or name in ('.', '..') or '/' in name or '\\' in name or name in members:
                raise SystemExit('Unsafe or duplicate compatibility archive member')
            members[name] = member
        if 'zitadel' not in members:
            raise SystemExit('Compatibility archive requires one regular executable')
        with tempfile.TemporaryDirectory(prefix='zitadel23-archive-symbols-') as temporary:
            binary = pathlib.Path(temporary) / 'zitadel'
            binary.write_bytes(archive.extractfile(members['zitadel']).read())
            inspector('go', binary, env)
