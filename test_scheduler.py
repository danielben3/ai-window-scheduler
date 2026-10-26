import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import scheduler as s


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = s.Engine(self.tmp.name)
        self.current = datetime(2026, 10, 26, 8, 0, 20, tzinfo=timezone.utc)

    def test_schedule_once_and_persist_across_restart(self):
        self.engine.config['Codex']['enabled'] = True
        self.assertEqual(len(self.engine.tick(self.current, launch=False)), 1)
        self.assertEqual(self.engine.tick(self.current, launch=False), [])
        restarted = s.Engine(self.tmp.name)
        restarted.config['Codex']['enabled'] = True
        self.assertEqual(restarted.tick(self.current, launch=False), [])

    def test_missed_trigger_not_fired_late(self):
        self.engine.config['Codex']['enabled'] = True
        self.assertEqual(self.engine.tick(self.current.replace(hour=9), launch=False), [])

    def test_multiple_trigger_times(self):
        self.engine.config['Codex'].update(enabled=True, times='08:00, 15:00')
        self.assertEqual(len(self.engine.tick(self.current, launch=False)), 1)
        self.engine.active.clear()
        self.assertEqual(len(self.engine.tick(self.current.replace(hour=15), launch=False)), 1)

    def arm(self, name='Claude Code'):
        cfg = self.engine.config[name]
        cfg.update(session='abcdef-123456', workspace=self.tmp.name, resume_time='13:00')
        with patch.object(s, 'resolve_executable', return_value='native.exe'):
            self.engine.arm(name, cfg, self.current)
        return cfg

    def test_resume_uses_explicit_id(self):
        cfg = self.arm('Codex')
        with patch.object(s, 'resolve_executable', return_value='codex.exe'):
            argv = s.command('Codex', cfg, 'resume')
        self.assertIn('abcdef-123456', argv)
        self.assertNotIn('--last', argv)

    def test_resume_success_is_one_shot(self):
        cfg = self.arm()
        self.engine.runner = lambda *a: (0, json.dumps({'result': 'Done', 'is_error': False}), '')
        due = self.engine.tick(self.current.replace(hour=13), launch=False)
        self.assertEqual(len(due), 1)
        self.engine.execute(*due[0])
        self.assertEqual(self.engine.state['jobs']['Claude Code']['status'], 'completed')
        self.assertEqual(self.engine.tick(self.current.replace(day=27, hour=13), launch=False), [])

    def test_only_quota_retried_and_bounded(self):
        cfg = self.arm()
        cfg['max_attempts'] = 2
        self.engine.state['jobs']['Claude Code']['config']['max_attempts'] = 2
        self.engine.runner = lambda *a: (1, json.dumps({'is_error': True, 'result': '5-hour limit reached'}), '')
        for expected in ['waiting', 'quota']:
            job = self.engine.state['jobs']['Claude Code']
            current = datetime.fromtimestamp(job['due'] + 0.001, timezone.utc)
            due = self.engine.tick(current, launch=False)
            self.engine.execute(*due[0])
            self.assertEqual(job['status'], expected)

    def test_task_prose_cannot_trigger_quota_retry(self):
        text = json.dumps({'result': 'Implemented rate_limit_exceeded handling.', 'is_error': False})
        self.assertEqual(s.decode_result('Claude Code', 0, text, '', 'resume'), 'completed')

    def test_generic_error_and_auth_do_not_retry(self):
        self.assertEqual(s.decode_result('Claude Code', 1, '{}', 'Not authenticated', 'resume'), 'failed')
        self.assertEqual(s.decode_result('Codex', 1, 'invalid', 'connection refused', 'resume'), 'unrecognized-output')

    def test_crash_does_not_replay_running_job(self):
        self.arm()
        self.engine.tick(self.current.replace(hour=13), launch=False)
        restarted = s.Engine(self.tmp.name)
        self.assertTrue(restarted.state['jobs']['Claude Code']['status'].startswith('interrupted'))

    def test_cancel_and_rearm(self):
        self.arm()
        self.engine.cancel('Claude Code')
        self.assertEqual(self.engine.tick(self.current.replace(hour=13), launch=False), [])
        self.arm()
        self.assertNotIn('Claude Code', self.engine.cancelled)

    def test_missed_continuation_requires_rearm(self):
        self.arm()
        self.assertEqual(self.engine.tick(self.current.replace(hour=14), launch=False), [])
        self.assertEqual(self.engine.state['jobs']['Claude Code']['status'], 'missed-rearm-required')

    def test_input_validation_and_ping_response(self):
        with self.assertRaises(ValueError):
            s.parse_times('25:10')
        self.assertEqual(s.parse_times('08:00,08:00, 15:30'), ['08:00', '15:30'])
        self.assertEqual(s.decode_result('Antigravity', 0, '{"status":"SUCCESS","response":"OK"}', '', 'trigger'), 'completed')
        self.assertEqual(s.decode_result('Antigravity', 0, '{"status":"WAITING","response":""}', '', 'resume'), 'failed')

    def test_subprocess_output_logs_and_environment(self):
        code = ('import json,os; assert "CODEX_API_KEY" not in os.environ; '
                'print(json.dumps({"result":"OK","is_error":False}))')
        with patch.object(s, 'command', return_value=[sys.executable, '-c', code]), \
             patch.dict('os.environ', {'CODEX_API_KEY': 'test-only-placeholder'}):
            result = self.engine.run_cli('Claude Code', self.engine.config['Claude Code'], 'trigger')
        self.assertEqual(s.decode_result('Claude Code', *result, 'trigger'), 'completed')
        self.assertEqual(len(list((Path(self.tmp.name) / 'logs').glob('*.txt'))), 2)

    def test_cancel_before_worker_starts_does_not_send(self):
        self.arm()
        due = self.engine.tick(self.current.replace(hour=13), launch=False)
        self.engine.cancel('Claude Code')
        def forbidden(*args):
            self.fail('Cancelled work must not call a provider')
        self.engine.runner = forbidden
        self.engine.execute(*due[0])
        self.assertEqual(self.engine.state['jobs']['Claude Code']['status'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
