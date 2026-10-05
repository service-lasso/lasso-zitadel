"""AC-013: real process outcomes plus complete scan/fail-closed orchestration."""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('runner', pathlib.Path(__file__).with_name('run-macos11-security.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class SecurityRunner(unittest.TestCase):
    def test_process_success_nonzero_and_timeout(self):
        for code, expected in [('print("report")', 0), ('raise SystemExit(3)', 3),
                               ('import time; time.sleep(30)', 124)]:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                owned = pathlib.Path(temporary).resolve()
                call = lambda: runner.run_stage('source', [sys.executable, '-c', code], owned,
                                                dict(os.environ), owned, .15 if expected == 124 else 5,
                                                interval=.02, timed=os.name == 'posix')
                if expected:
                    with self.assertRaises(subprocess.CalledProcessError) as caught:
                        call()
                    self.assertEqual(caught.exception.returncode, expected)
                else:
                    call()
                    self.assertEqual((owned / 'source-vulnerabilities.txt').read_text().strip(), 'report')
                records = [json.loads(line) for line in (owned / 'security-resources.log').read_text().splitlines()]
                self.assertEqual(records[0]['event'], 'start')
                self.assertEqual(records[-1]['exitCode'], expected)
                self.assertEqual(records[-1]['event'], 'timeout' if expected == 124 else 'end')
                self.assertTrue((owned / 'security-source-stderr.log').is_file())
                if os.name == 'posix':
                    self.assertTrue((owned / 'security-source-time.log').is_file())

    def test_failed_linked_authentication_cannot_record_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            owned = pathlib.Path(temporary).resolve()
            with patch.object(runner.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['linked'])) as gates:
                with self.assertRaises(subprocess.CalledProcessError):
                    runner.run(owned, owned, lambda *args: None)
                self.assertEqual(gates.call_count, 1)
                self.assertIn('verify-macos11-inputs.py', gates.call_args.args[0][1])

    def test_full_targets_private_budget_and_fail_closed_sequence(self):
        for failure in (None, 'install', 'source', 'binary'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                owned = pathlib.Path(temporary).resolve()
                receipt = owned / 'security-scan.json'
                receipt.write_text('stale pass')
                calls = []

                def stage(name, command, cwd, env, root, seconds):
                    calls.append((name, command, cwd, env, seconds))
                    self.assertFalse(receipt.exists())
                    for key, value in {'GOMEMLIMIT': '3GiB', 'GOMAXPROCS': '2', 'GOFLAGS': '-p=2',
                                       'GOTOOLCHAIN': 'local', 'GOENV': 'off', 'GOWORK': 'off'}.items():
                        self.assertEqual(env[key], value)
                    self.assertEqual(env['GOROOT'], str(owned / 'go'))
                    if name == failure:
                        raise subprocess.CalledProcessError(3, command)

                with patch.object(runner.subprocess, 'run') as gates:
                    if failure:
                        with self.assertRaises(subprocess.CalledProcessError):
                            runner.run(owned, owned, stage)
                        gates.assert_not_called()
                    else:
                        runner.run(owned, owned, stage)
                        self.assertEqual(gates.call_count, 2)
                        self.assertIn('verify-macos11-inputs.py', gates.call_args_list[0].args[0][1])
                        self.assertEqual(gates.call_args_list[0].args[0][-1], 'linked')
                        self.assertIn('record-macos11-security.py', gates.call_args_list[1].args[0][1])
                        self.assertTrue(all(item.kwargs['check'] for item in gates.call_args_list))
                self.assertEqual(calls[0][1][-1], 'golang.org/x/vuln/cmd/govulncheck@v1.7.0')
                if len(calls) > 1:
                    self.assertEqual(calls[1][1], [str(owned / 'security-tools/govulncheck'), './...'])
                    self.assertEqual(calls[1][3]['GOOS'], 'darwin')
                    self.assertEqual(calls[1][4], 2700)
                if len(calls) > 2:
                    self.assertEqual(calls[2][1], [str(owned / 'security-tools/govulncheck'), '-mode=binary', str(owned / 'artifacts/zitadel')])
                    self.assertEqual(calls[2][4], 900)
                self.assertEqual([item[0] for item in calls], ['install', 'source', 'binary'][:{'install': 1, 'source': 2}.get(failure, 3)])


if __name__ == '__main__':
    unittest.main()
