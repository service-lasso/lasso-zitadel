"""AC-015-2: execute the producer's actual preflight with Python defaults."""
import os
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent.parent
workflow = (root / '.github/workflows/release-development.yml').read_text()
step = workflow.split('      - name: Refuse forged receipts and publication inventory drift\n', 1)[1]
block = step.split('        run: |\n', 1)[1].split('      - name:', 1)[0]
commands = [line.strip() for line in block.splitlines() if line.strip()]
assert commands, 'Producer preflight must contain commands'
environment = dict(os.environ)
environment.pop('PYTHONDONTWRITEBYTECODE', None)
environment.pop('PYTHONPYCACHEPREFIX', None)


def assert_pristine():
    status = subprocess.check_output(
        ['git', 'status', '--porcelain', '--untracked-files=all'], cwd=root, text=True)
    assert not status, f'Producer checkout contaminated:\n{status}'


assert_pristine()
for command in commands:
    print(f'Producer preflight: {command}', flush=True)
    subprocess.run(['bash', '-euo', 'pipefail', '-c', command], cwd=root,
                   env=environment, check=True)
    assert_pristine()
print('All exact producer preflight commands preserved the pristine checkout')
