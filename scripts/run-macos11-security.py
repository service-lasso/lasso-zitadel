"""Run unchanged mandatory scans with isolated Go budgets and streamed diagnostics."""
import json
import os
import pathlib
import signal
import subprocess
import sys
import time


def resources():
    result = {}
    # Only numerical, nonsecret resource files. No environment/process dumps.
    meminfo = pathlib.Path('/proc/meminfo')
    if meminfo.exists():
        result['hostMemory'] = {k: v.strip() for k, v in
                                (line.split(':', 1) for line in meminfo.read_text().splitlines())
                                if k in ('MemTotal', 'MemAvailable', 'SwapFree')}
    cgroup = pathlib.Path('/proc/self/cgroup')
    if cgroup.exists():
        for line in cgroup.read_text().splitlines():
            if line.startswith('0::'):
                root = pathlib.Path('/sys/fs/cgroup') / line[3:].lstrip('/')
                for name in ('memory.current', 'memory.max', 'memory.peak', 'memory.events'):
                    path = root / name
                    if path.is_file():
                        result[name] = path.read_text().strip()
    return result


def run_stage(name, command, cwd, env, owned, seconds, interval=10, timed=True):
    log = owned / 'security-resources.log'

    def emit(event, **fields):
        try:
            metrics = resources()
        except OSError as error:
            metrics = {'resourceReadError': type(error).__name__}
        line = json.dumps({'stage': name, 'event': event, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                           **fields, **metrics}, sort_keys=True)
        print(line, flush=True)
        with log.open('a', encoding='utf-8') as handle:
            handle.write(line + '\n')

    emit('start', deadlineSeconds=seconds)
    if timed:
        command = ['/usr/bin/time', '-v', '-o', str(owned / f'security-{name}-time.log'), *command]
    report = owned / ({'source': 'source-vulnerabilities.txt', 'binary': 'binary-vulnerabilities.txt'}.get(name, f'security-{name}.log'))
    with report.open('w') as stdout, (owned / f'security-{name}-stderr.log').open('w') as stderr:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                                   start_new_session=os.name == 'posix')
        deadline = time.monotonic() + seconds
        while process.poll() is None:
            if time.monotonic() >= deadline:
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait()
                # Descendants can survive the wrapper's TERM; close the owned group.
                if os.name == 'posix':
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                emit('timeout', exitCode=124)
                raise subprocess.CalledProcessError(124, command)
            emit('running')
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
        emit('end', exitCode=process.returncode)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command)


def run(owned, workspace, stage=run_stage):
    owned, workspace = pathlib.Path(owned).resolve(), pathlib.Path(workspace).resolve()
    # Never leave an earlier successful receipt beside a new failed attempt.
    (owned / 'security-scan.json').unlink(missing_ok=True)
    env = dict(os.environ, GOENV='off', GOWORK='off', GOTOOLCHAIN='local', GOFLAGS='-p=2',
               GOOS='linux', GOARCH='amd64', GOAMD64='v1', CGO_ENABLED='0',
               GOMEMLIMIT='3GiB', GOMAXPROCS='2', GOROOT=str(owned / 'go'),
               GOCACHE=str(owned / 'cache'), GOMODCACHE=str(owned / 'modcache'),
               PATH=f'{owned}/go/bin:/usr/bin:/bin', GOBIN=str(owned / 'security-tools'))
    (owned / 'security-tools').mkdir(exist_ok=True)
    stage('install', [str(owned / 'go/bin/go'), 'install', 'golang.org/x/vuln/cmd/govulncheck@v1.7.0'],
          workspace, env, owned, 600)
    source = owned / 'zitadel-10b1af91d68700707d41e820545e478cf267511b'
    scanner = str(owned / 'security-tools/govulncheck')
    # Default TEXT mode preserves mandatory nonzero exits for findings.
    stage('source', [scanner, './...'], source, dict(env, GOOS='darwin'), owned, 2700)
    stage('binary', [scanner, '-mode=binary', str(owned / 'artifacts/zitadel')], source, env, owned, 900)
    # Original linked authentication and receipt binding remain mandatory.
    subprocess.run([sys.executable, str(workspace / 'scripts/verify-macos11-inputs.py'), str(workspace), str(owned), 'linked'], check=True)
    subprocess.run([sys.executable, str(workspace / 'scripts/record-macos11-security.py'), str(owned)], check=True)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
