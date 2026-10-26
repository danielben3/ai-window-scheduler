import copy
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
import scheduler as core
from scheduler_ui import SchedulerWindow, load_ui_settings, experiment_html


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = core.Engine(self.tmp.name)
        self.engine.save_config(self.engine.config)
        self.window = SchedulerWindow(self.engine, start_timer=False)
        self.addCleanup(self.dispose)

    def dispose(self):
        self.window.timer.stop()
        self.window.hide()
        self.window.deleteLater()
        self.app.processEvents()

    def test_language_switch_preserves_drafts_and_saved_provider_data(self):
        original = (Path(self.tmp.name) / 'config.json').read_bytes()
        self.window.fields['Codex']['model'].setText('draft-model')
        self.window.fields['Claude Code']['session'].setText('draft-session')
        prompt = self.window.fields['Codex']['prompt'].toPlainText()
        self.window.navigate(3)
        self.window.language_combo.setCurrentIndex(1)
        self.window.theme_combo.setCurrentIndex(1)
        self.window.save_ui_settings()
        self.assertEqual(self.window.layoutDirection(), Qt.LayoutDirection.LeftToRight)
        self.assertEqual(self.window.nav_buttons[3].text(), 'Settings')
        self.assertEqual(self.window.fields['Codex']['model'].text(), 'draft-model')
        self.assertEqual(self.window.fields['Claude Code']['session'].text(), 'draft-session')
        self.assertEqual(self.window.fields['Codex']['prompt'].toPlainText(), prompt)
        self.assertEqual((Path(self.tmp.name) / 'config.json').read_bytes(), original)
        saved = load_ui_settings(Path(self.tmp.name) / 'ui_settings.json')
        self.assertEqual((saved['language'], saved['theme']), ('en', 'light'))
        self.window.language_combo.setCurrentIndex(0)
        self.window.save_ui_settings()
        self.assertEqual(self.window.layoutDirection(), Qt.LayoutDirection.RightToLeft)
        self.assertEqual(self.window.fields['Codex']['model'].text(), 'draft-model')

    def test_save_one_provider_does_not_commit_other_drafts(self):
        self.window.fields['Codex']['model'].setText('codex-draft')
        self.window.fields['Claude Code']['model'].setText('claude-draft')
        self.window.save_provider('Codex')
        saved = core.load_json(Path(self.tmp.name) / 'config.json', {})
        self.assertEqual(saved['Codex']['model'], 'codex-draft')
        self.assertEqual(saved['Claude Code']['model'], '')
        self.assertFalse(any(value['enabled'] for value in saved.values()))

    def test_invalid_schedule_is_rejected_without_writing(self):
        before = copy.deepcopy(self.engine.config)
        self.window.fields['Codex']['times'].setText('25:99')
        with patch.object(self.window, 'error') as error:
            self.window.save_provider('Codex')
        error.assert_called_once()
        self.assertEqual(self.engine.config, before)

    def test_connection_probe_only_requests_version(self):
        self.window.fields['Codex']['executable'].setText(sys.executable)
        with patch.object(core, 'command', side_effect=AssertionError('AI command must not be built')):
            self.window.check_cli('Codex')
            until = time.monotonic() + 10
            while self.window.probes and time.monotonic() < until:
                self.app.processEvents()
                time.sleep(0.01)
        self.assertFalse(self.window.probes)
        self.assertIn('Python', self.window.checks['Codex'][1])
        self.assertEqual(self.engine.state['fired'], {})
        self.assertFalse((Path(self.tmp.name) / 'history.jsonl').exists())

    def test_settings_restore_after_restart_and_invalid_values_are_bounded(self):
        core.atomic_json(self.window.settings_path, dict(language='en', theme='light', close_action='minimize', refresh_seconds=60))
        other = SchedulerWindow(core.Engine(self.tmp.name), start_timer=False)
        try:
            self.assertEqual(other.settings['language'], 'en')
            self.assertEqual(other.close_combo.currentData(), 'minimize')
            self.assertEqual(other.refresh_spin.value(), 60)
            self.assertEqual(other.fields['Codex']['prompt'].toPlainText(), self.engine.config['Codex']['prompt'])
        finally:
            other.deleteLater()
            self.app.processEvents()
        core.atomic_json(self.window.settings_path, dict(language='invalid', theme='invalid', refresh_seconds=-1))
        settings = load_ui_settings(self.window.settings_path)
        self.assertEqual(settings['language'], 'he')
        self.assertEqual(settings['refresh_seconds'], 10)

    def test_plan_is_bilingual_and_marks_live_steps_unexecuted(self):
        self.assertIn('טרם בוצעו', experiment_html('he'))
        self.assertIn('not run', experiment_html('en'))
        self.assertIn('proof.txt', experiment_html('en'))
        self.assertIn('dir="rtl"', experiment_html('he'))


if __name__ == '__main__':
    unittest.main()
