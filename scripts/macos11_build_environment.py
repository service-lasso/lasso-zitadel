"""Record the requested disabling control and Go's effective environment separately."""
import json
import os
import subprocess

ENVIRONMENT = ('GOENV', 'GOWORK', 'GOTOOLCHAIN', 'GOFLAGS', 'GOOS', 'GOARCH',
               'GOAMD64', 'CGO_ENABLED', 'GOROOT', 'GOCACHE', 'GOMODCACHE',
               'GOPROXY', 'GOSUMDB', 'GOPRIVATE', 'GONOPROXY', 'GONOSUMDB')


def record_environment():
    if os.environ.get('GOENV') != 'off':
        raise ValueError('Compatibility build requires requested GOENV=off')
    effective = json.loads(subprocess.check_output(['go', 'env', '-json', *ENVIRONMENT], text=True))
    if effective.get('GOENV') != '':
        raise ValueError('Compatibility build requires disabled effective GOENV')
    return {'requestedEnvironment': {'GOENV': 'off'}, 'environment': effective}
