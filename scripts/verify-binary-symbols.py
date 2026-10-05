"""Inspect actual executable symbols at the standalone packaging boundary."""
import os, sys
sys.dont_write_bytecode = True
from binary_symbols import inspect_symbols, inspect_archive_symbols

env = dict(os.environ, GOENV='off', GOWORK='off', GOTOOLCHAIN='local', GOFLAGS='', GOOS='', GOARCH='')
if sys.argv[1] == '--archive':
    inspect_archive_symbols(sys.argv[2], env)
else:
    inspect_symbols('go', sys.argv[1], env)
