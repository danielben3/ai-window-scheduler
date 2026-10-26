"""Bilingual Qt desktop interface for the existing local scheduler engine."""
from __future__ import annotations

import copy
from datetime import datetime
import html
import json
import os
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer, QProcess, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QTabWidget, QTextBrowser,
    QTextEdit, QVBoxLayout, QWidget,
)
import scheduler as core

TEXT = {
    'brand': ('מתזמן AI', 'AI Scheduler'),
    'tagline': ('תזמון מקומי. שליטה מלאה.', 'Local scheduling. Your control.'),
    'services': ('סביבות העבודה', 'WORKSPACES'),
    'settings': ('הגדרות', 'Settings'), 'experiment': ('תוכנית הניסוי', 'Experiment plan'),
    'local': ('פועל מקומית במחשב שלך', 'Runs locally on your computer'),
    'subtitle': ('בקשות קצרות וחידוש עבודה בזמן שבחרת', 'Minimal requests and continuations on your schedule'),
    'schedule': ('בקשות יומיות', 'Daily requests'), 'resume': ('חידוש עבודה', 'Continuation'),
    'activity': ('פעילות', 'Activity'), 'detected': ('כלי שורת הפקודה זוהה', 'CLI detected'),
    'missing': ('כלי שורת הפקודה לא נמצא', 'CLI not found'),
    'off': ('התזמון כבוי', 'Schedule off'), 'on': ('התזמון מופעל', 'Schedule enabled'),
    'connection': ('חיבור לכלי', 'CLI connection'),
    'connection_hint': ('בדיקת זיהוי וגרסה מקומית בלבד, ללא בקשת AI.', 'Detection and version checks run locally without an AI request.'),
    'executable': ('נתיב כלי שורת הפקודה', 'CLI executable'),
    'model': ('מזהה מודל', 'Model ID'), 'model_hint': ('ריק = ברירת המחדל של הכלי', 'Blank uses the CLI default'),
    'check': ('בדיקת חיבור', 'Check connection'), 'checking': ('בודק גרסה…', 'Checking version…'),
    'daily_title': ('התחלה בשעה שלך', 'Start at your time'),
    'daily_hint': ('כל שעה מפעילה בקשה קצרה אחת. שמירה מחילה את הבחירה.', 'Each time runs one minimal request. Save to apply your selection.'),
    'enabled': ('הפעלת בקשות יומיות', 'Enable daily requests'),
    'times': ('שעות בקשה', 'Request times'), 'times_hint': ('לדוגמה 08:00, 15:00 — לפי שעון המחשב', 'Example: 08:00, 15:00 — computer local time'),
    'preview': ('תצוגת הפקודה', 'Preview command'), 'save': ('שמירת הגדרות השירות', 'Save service settings'),
    'saved': ('ההגדרות נשמרו', 'Settings saved'),
    'saved_hint': ('הגדרות השירות נשמרו. חידוש עבודה מתוזמן בנפרד.', 'Service settings saved. Continuations are armed separately.'),
    'resume_title': ('לחזור בדיוק לאותה שיחה', 'Pick up the same conversation'),
    'resume_hint': ('חידוש חד־פעמי לשיחה קיימת. זמן האיפוס נקבע על ידי הספק.', 'One continuation for an existing session. Your provider determines the reset time.'),
    'workspace': ('תיקיית הפרויקט', 'Project folder'), 'browse': ('בחירה…', 'Browse…'),
    'session': ('מזהה שיחה מדויק', 'Exact session ID'),
    'resume_time': ('שעת החידוש הבאה', 'Next continuation time'),
    'prompt': ('הנחיה לחידוש העבודה', 'Continuation instruction'),
    'retry': ('מרווח ניסיון חוזר בדקות', 'Retry interval in minutes'),
    'attempts': ('מספר ניסיונות מרבי', 'Maximum attempts'),
    'timeout': ('משך ריצה מרבי בדקות', 'Run timeout in minutes'),
    'arm': ('תזמון חידוש חד־פעמי', 'Arm one continuation'),
    'cancel': ('ביטול / עצירה', 'Cancel / stop'),
    'armed': ('חידוש העבודה תוזמן', 'Continuation armed'),
    'none': ('לא תוזמן חידוש עבודה', 'No continuation armed'),
    'today': ('בקשות היום', 'Requests today'), 'confirmed': ('תשובות OK היום', 'Confirmed OK today'),
    'next': ('חידוש העבודה', 'Continuation'),
    'waiting': ('ממתין', 'Waiting'), 'running': ('פעיל', 'Running'),
    'completed': ('הושלם', 'Completed'), 'cancelled': ('בוטל', 'Cancelled'),
    'quota': ('מגבלת מכסה', 'Quota limit'), 'failed': ('נכשל', 'Failed'),
    'blocked': ('נחסם', 'Blocked'), 'local-error': ('שגיאה מקומית', 'Local error'),
    'unexpected-response': ('תשובה לא צפויה', 'Unexpected response'),
    'unrecognized-output': ('פלט לא מוכר', 'Unrecognized output'),
    'missed-rearm-required': ('המועד הוחמץ — יש לתזמן מחדש', 'Missed — rearm required'),
    'interrupted-check-project-before-rearming': ('הריצה נקטעה — יש לבדוק את הפרויקט', 'Interrupted — inspect the project'),
    'started': ('התחיל', 'Started'), 'trigger': ('בקשה יומית', 'Daily request'),
    'activity_hint': ('האירועים האחרונים נשמרים מקומית. פלט מלא נמצא בתיקיית היומנים.', 'Recent events are stored locally. Full output is in the logs folder.'),
    'empty': ('עדיין אין פעילות. בקשות מתוזמנות יופיעו כאן.', 'No activity yet. Scheduled runs will appear here.'),
    'logs': ('פתיחת תיקיית היומנים', 'Open logs folder'),
    'settings_hint': ('התאמה אישית של הממשק והחלון', 'Make the interface and window work for you'),
    'appearance': ('שפה ומראה', 'Language & appearance'),
    'language': ('שפת התצוגה', 'Display language'), 'theme': ('ערכת צבעים', 'Theme'),
    'dark': ('כהה', 'Dark'), 'light': ('בהירה', 'Light'),
    'behavior': ('התנהגות הכלי', 'App behavior'),
    'close_action': ('בעת סגירת החלון', 'When closing the window'),
    'ask': ('בקשת אישור יציאה', 'Ask before quitting'), 'minimize': ('מזעור והמשך תזמון', 'Minimize and keep scheduling'),
    'refresh': ('תדירות עדכון בשניות', 'Refresh interval in seconds'),
    'apply': ('שמירה והחלת ההגדרות', 'Save & apply settings'),
    'settings_note': ('שפת התצוגה אינה משנה הנחיות, שיחות או שעות שנשמרו.', 'Display language never changes saved prompts, sessions, or times.'),
    'startup': ('הפעלה עם הכניסה למחשב', 'Launch at Windows sign-in'),
    'startup_hint': ('ההפעלה תהיה ממוזערת. המחשב והמשתמש צריכים להישאר פעילים.', 'Starts minimized. The computer must be awake and the user signed in.'),
    'startup_on': ('הפעלת כניסה אוטומטית', 'Enable launch at sign-in'),
    'startup_off': ('ביטול הפעלה אוטומטית', 'Disable launch at sign-in'),
    'startup_enabled': ('הפעלה אוטומטית הופעלה', 'Launch at sign-in enabled'),
    'startup_disabled': ('הפעלה אוטומטית בוטלה', 'Launch at sign-in disabled'),
    'storage': ('נתונים מקומיים', 'Local data'),
    'error': ('יש לבדוק את ההגדרות', 'Check settings'),
    'invalid_times': ('יש להזין שעות תקינות בפורמט HH:MM, מופרדות בפסיקים.', 'Enter valid HH:MM times, separated by commas.'),
    'one_time': ('יש להזין שעת חידוש אחת.', 'Enter one continuation time.'),
    'no_prompt': ('יש להזין הנחיה לחידוש העבודה.', 'Enter a continuation instruction.'),
    'no_project': ('יש לבחור תיקיית פרויקט קיימת.', 'Choose an existing project folder.'),
    'no_session': ('יש להזין מזהה שיחה מדויק באורך 6 תווים לפחות.', 'Enter the exact session ID, at least 6 characters.'),
    'preview_title': ('תצוגה מקדימה — לא נשלחה בקשה', 'Command preview — no request sent'),
    'close_title': ('לצאת מהמתזמן?', 'Quit scheduler?'),
    'close_hint': ('יציאה מפסיקה תזמונים ועוצרת ריצות שהכלי הפעיל. לצאת?', 'Quitting stops future schedules and active runs started by this app. Quit?'),
    'experiment_hint': ('ניסוי מדורג לפני שמסתמכים על תזמון אוטומטי', 'A staged trial before relying on unattended scheduling'),
    'planned': ('השלבים המקוונים מתוכננים בלבד — טרם בוצעו', 'Online stages are planned — not yet executed'),
    'quit': ('יציאה', 'Quit'), 'keep': ('המשך עבודה', 'Keep running'),
    'unsaved': ('יש שינויים שלא נשמרו. יציאה תאבד אותם.', 'There are unsaved changes. Quitting will discard them.'),
}

UI_DEFAULTS = {'language': 'he', 'theme': 'dark', 'close_action': 'ask', 'refresh_seconds': 10}


def load_ui_settings(path):
    raw = core.load_json(Path(path), UI_DEFAULTS)
    result = {**UI_DEFAULTS, **raw}
    for key, options in [('language', ('he', 'en')), ('theme', ('dark', 'light')), ('close_action', ('ask', 'minimize'))]:
        if result[key] not in options:
            result[key] = UI_DEFAULTS[key]
    if type(result['refresh_seconds']) is not int or not 5 <= result['refresh_seconds'] <= 60:
        result['refresh_seconds'] = 10
    return result


def experiment_html(language='he'):
    rtl = language == 'he'
    rows = [
        ('ממשק והגדרות · ללא שימוש במכסה', 'Interface & settings · no quota usage',
         'החלף בין עברית לאנגלית ובין כהה לבהיר. הזן טיוטה בשירות אחד, החלף שפה וחזור. סגור ופתח מחדש.',
         'Switch Hebrew/English and dark/light. Edit a service draft, change language, then return. Close and reopen.',
         'השפה והמראה נשמרים, הטיוטה שורדת החלפת שפה, ההגדרות שנשמרו שורדות הפעלה מחדש; שעות, הנחיות ותזמונים לא משתנים מעצמם.',
         'Language and theme persist; drafts survive language changes; saved settings survive restart. Prompts, times and schedules do not change by themselves.'),
        ('זיהוי שלושת הכלים · ללא שימוש במכסה', 'Detect all three CLIs · no quota usage',
         'לחץ על בדיקת חיבור בכל שירות. לאחר מכן הצג את הפקודה ובדוק את הנתיב והמודל.',
         'Use Check connection for each service. Preview the command and inspect its executable and model.',
         'Codex, Claude Code ו־Antigravity מחזירים גרסה תקינה. אין רשומת בקשת AI חדשה ביומן.',
         'Codex, Claude Code and Antigravity return valid versions. No new AI-request history entry is created.'),
        ('בקשה אחת בשירות אחד · צורך מכסה', 'One request on one service · uses quota',
         'לאחר אישורך: בחר Codex ראשון, ודא ידנית שהחשבון הוא המנוי הרצוי. הגדר שעה אחת לשתי דקות קדימה, הפעל ושמור. לאחר הבקשה כבה ושמור מיד.',
         'After your approval: start with Codex. Manually verify the intended subscription account. Set one time two minutes ahead, enable and save. Disable and save immediately after the request.',
         'בקשה אחת בלבד, תשובת OK אחת, יומן התחלה וסיום ו־completed. בקשה לא אמורה לשנות קובצי פרויקט. אין הבטחה להתחלת חלון מכסה אצל הספק.',
         'Exactly one request, one OK response and started/completed history entries. No project files should change. This does not prove a provider quota window has started.'),
        ('מניעת כפילויות · אותה דקת תזמון', 'Duplicate prevention · same scheduled minute',
         'לאחר אותה בקשה, כבה ושמור. שמור צילום של היומן. הפעל מחדש באותה דקה ובדוק שאין בקשה נוספת. אין להפעיל שוב את התזמון לצורך הבדיקה.',
         'After that request, disable and save. Capture the history. Restart in the same minute and confirm no extra request. Do not re-enable the schedule for this check.',
         'מזהה התזמון נשמר ב־state.json וההיסטוריה מכילה בקשה אחת. מניעת כפילות עם תזמון פעיל נבדקת בבדיקת מנוע מקומית.',
         'The fired key remains in state.json and history contains one request. Duplicate prevention with enabled schedules is covered by a local engine test.'),
        ('חידוש שיחת ניסוי · צורך מכסה', 'Resume a trial session · uses quota',
         'באישורך: צור ידנית שיחת CLI בתיקיית ניסוי ריקה. בקש לזכור מחרוזת ייחודית, ללא יצירת קבצים עדיין. העתק מזהה שיחה מדויק. תזמן חידוש לשתי דקות קדימה עם הוראה לכתוב את המחרוזת שנזכרה ל־proof.txt ולעצור.',
         'With your approval: manually create a CLI session in an empty trial folder. Ask it to remember a unique marker without writing any files yet. Copy its exact session ID. Arm a continuation two minutes ahead, instructing it to write the remembered marker to proof.txt and stop.',
         'אותו מזהה שיחה, קובץ יחיד בתיקיית הניסוי, completed, וחידוש חד־פעמי שאינו חוזר למחרת. אין להשתמש בפרויקט עבודה אמיתי.',
         'The same session ID, one file inside the trial folder, completed, and a one-shot job that does not repeat tomorrow. Use no real working project.'),
        ('שגיאות, ביטול והרחבה', 'Failures, cancellation & rollout',
         'בדוק מקומית שגיאות מכסה מדומות, התחברות, ביטול ומועד שהוחמץ. אין לנסות למצות מכסה אמיתית. לאחר הצלחת Codex חזור על הבקשה הבודדת ועל החידוש בכל אחד משני השירותים האחרים.',
         'Locally simulate quota errors, authentication failures, cancellation and missed times. Do not exhaust a real quota. After Codex passes, repeat the single request and continuation separately on the other two services.',
         'רק שגיאת מכסה מזוהה גורמת לניסיון חוזר, עד התקרה. ביטול עוצר משימת ניסוי בלבד. תזמון שהוחמץ מחייב תזמון מחדש. לכל שירות תיעוד נפרד.',
         'Only a recognized quota error retries, up to its limit. Cancellation affects only the trial job. Missed continuations require rearming. Keep separate evidence for each provider.'),
    ]
    title = 'תוכנית ניסוי לכלי' if rtl else 'Scheduler trial plan'
    intro = ('האחריות לביצוע: המשתמש מאמת את החשבון ומאשר בקשות אמיתיות. זו תוכנית אימות למחשב שלך; השלבים המקוונים טרם בוצעו במחשב שלך. יעד: שש בקשות מתוכננות לכל היותר — בקשה וחידוש לכל שירות — בנוסף להקמת שיחות הניסוי. ייתכנו ניסיונות חוזרים רק אם הופעלו במפורש.' if rtl else
             'You verify your account and approve live requests. This plan validates your own computer; online stages have not run on your computer. Target: at most six planned runs — one request and one continuation per provider — plus trial-session setup. Additional retries only if explicitly enabled.')
    parts = [f'<html dir="{"rtl" if rtl else "ltr"}"><body><h1>{title}</h1><p>{intro}</p>']
    for i, row in enumerate(rows, 1):
        label, action, success = (row[0], row[2], row[4]) if rtl else (row[1], row[3], row[5])
        parts.append(f'<h2>{i:02d} · {label}</h2><p>{action}</p><p><b>{"תנאי הצלחה" if rtl else "Pass criteria"}:</b> {success}</p>')
    parts.append('<hr><p>' + ('תיעוד נדרש: גרסאות, שעה ואזור זמן, מזהה שיחת ניסוי, פקודה ללא סודות, תוצאת הריצה ומצב הקבצים. עצירה: שגיאת התחברות, פורמט פלט לא מוכר, חריגה מתיקיית הניסוי או בקשה כפולה. בסיום מכבים תזמוני ניסוי ושומרים.' if rtl else 'Evidence: versions, timestamp/time zone, trial session ID, command without secrets, run result and file changes. Stop on auth errors, unrecognized output, changes outside the trial folder or duplicate requests. Disable and save trial schedules when finished.') + '</p></body></html>')
    return ''.join(parts)


class SchedulerWindow(QMainWindow):
    def __init__(self, engine=None, settings_path=None, start_timer=True):
        super().__init__()
        self.engine = engine or core.Engine()
        self.settings_path = Path(settings_path or self.engine.directory / 'ui_settings.json')
        self.settings = load_ui_settings(self.settings_path)
        self.drafts = copy.deepcopy(self.engine.config)
        self.fields = {}
        self.history = []
        self.checks = {}
        self.probes = []
        self.selected_page = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.resize(1120, 760)
        self.setMinimumSize(900, 580)
        history = self.engine.directory / 'history.jsonl'
        if history.exists():
            with history.open('rb') as f:
                f.seek(max(0, history.stat().st_size - 64000))
                for line in f.read().decode('utf-8', errors='replace').splitlines():
                    try:
                        self.history.append(json.loads(line))
                    except ValueError:
                        pass
        self.build()
        self.refresh(tick=False)
        if start_timer:
            self.timer.start(self.settings['refresh_seconds'] * 1000)

    def tr(self, key):
        return TEXT.get(key, (key, key))[self.settings['language'] == 'en']

    def label(self, key, role=None):
        widget = QLabel(self.tr(key))
        widget.setWordWrap(True)
        if role:
            widget.setObjectName(role)
        return widget

    def button(self, key, callback, primary=False):
        widget = QPushButton(self.tr(key))
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setMinimumHeight(38)
        widget.setObjectName('primary' if primary else 'secondary')
        widget.clicked.connect(callback)
        return widget

    def card(self, parent, title, hint=None):
        card = QFrame()
        card.setObjectName('card')
        box = QVBoxLayout(card)
        box.setContentsMargins(22, 20, 22, 20)
        box.setSpacing(12)
        box.addWidget(self.label(title, 'cardTitle'))
        if hint:
            box.addWidget(self.label(hint, 'muted'))
        parent.addWidget(card)
        return box

    def field(self, box, key, widget, hint=None):
        box.addWidget(self.label(key, 'fieldLabel'))
        box.addWidget(widget)
        if hint:
            box.addWidget(self.label(hint, 'muted'))
        return widget

    def edit(self, value='', ltr=True):
        widget = QLineEdit(str(value))
        widget.setMinimumHeight(38)
        if ltr:
            widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            widget.setAlignment(Qt.AlignmentFlag.AlignLeft)
        return widget

    def page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        box = QVBoxLayout(content)
        box.setContentsMargins(24, 22, 24, 24)
        box.setSpacing(18)
        scroll.setWidget(content)
        return scroll, box

    def build(self):
        old = self.takeCentralWidget()
        if old:
            old.deleteLater()
        self.fields = {}
        self.status_widgets = {}
        self.log_widgets = {}
        self.check_widgets = {}
        self.tabs = {}
        self.setWindowTitle('AI Window Scheduler · ' + self.tr('brand'))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.settings['language'] == 'he' else Qt.LayoutDirection.LeftToRight)
        base = QWidget()
        row = QHBoxLayout(base)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(210)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(20, 28, 20, 22)
        nav.setSpacing(10)
        nav.addWidget(self.label('brand', 'brand'))
        nav.addWidget(self.label('tagline', 'muted'))
        nav.addSpacing(26)
        nav.addWidget(self.label('services', 'eyebrow'))
        self.nav_buttons = []
        for index, name in enumerate([*core.PROVIDERS, 'settings', 'experiment']):
            if index == 3:
                nav.addSpacing(24)
            text = name if index < 3 else self.tr(name)
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setObjectName('nav')
            btn.setMinimumHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            nav.addWidget(btn)
            self.nav_buttons.append(btn)
        nav.addStretch()
        nav.addWidget(self.label('local', 'muted'))
        self.clock = QLabel()
        self.clock.setObjectName('muted')
        self.clock.setWordWrap(True)
        nav.addWidget(self.clock)
        nav.addWidget(self.button('quit', self.explicit_quit))
        row.addWidget(sidebar)
        self.stack = QStackedWidget()
        row.addWidget(self.stack, 1)
        for name in core.PROVIDERS:
            self.stack.addWidget(self.provider_page(name))
        self.stack.addWidget(self.settings_page())
        self.stack.addWidget(self.experiment_page())
        self.setCentralWidget(base)
        self.navigate(self.selected_page)
        self.apply_theme()

    def navigate(self, index):
        self.selected_page = index
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)

    def provider_page(self, name):
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(26, 24, 26, 20)
        layout.setSpacing(14)
        title = QLabel(name)
        title.setObjectName('title')
        layout.addWidget(title)
        layout.addWidget(self.label('subtitle', 'muted'))
        badges = QHBoxLayout()
        detected = QLabel()
        detected.setObjectName('badge')
        schedule = QLabel()
        schedule.setObjectName('badge')
        badges.addWidget(detected)
        badges.addWidget(schedule)
        badges.addStretch()
        layout.addLayout(badges)
        stats = QHBoxLayout()
        values = []
        for key in ['today', 'confirmed', 'next']:
            frame = QFrame()
            frame.setObjectName('stat')
            stat_box = QVBoxLayout(frame)
            stat_box.addWidget(self.label(key, 'muted'))
            value = QLabel('0')
            value.setObjectName('statValue')
            value.setWordWrap(True)
            stat_box.addWidget(value)
            stats.addWidget(frame, 1)
            values.append(value)
        layout.addLayout(stats)
        self.status_widgets[name] = (detected, schedule, *values)
        tabs = QTabWidget()
        self.tabs[name] = tabs
        layout.addWidget(tabs, 1)
        cfg = self.drafts[name]
        fields = {}
        self.fields[name] = fields
        page, box = self.page()
        columns = QHBoxLayout()
        columns.setSpacing(18)
        box.addLayout(columns)
        card = self.card(columns, 'connection', 'connection_hint')
        fields['executable'] = self.field(card, 'executable', self.edit(cfg['executable']))
        fields['model'] = self.field(card, 'model', self.edit(cfg['model']), 'model_hint')
        check = self.button('check', lambda: self.check_cli(name))
        self.check_widgets[name] = check
        card.addWidget(check)
        card = self.card(columns, 'daily_title', 'daily_hint')
        enabled = QCheckBox(self.tr('enabled'))
        enabled.setChecked(cfg['enabled'])
        fields['enabled'] = enabled
        card.addWidget(enabled)
        fields['times'] = self.field(card, 'times', self.edit(cfg['times']), 'times_hint')
        card.addWidget(self.button('preview', lambda: self.preview(name)))
        box.addStretch()
        tabs.addTab(page, self.tr('schedule'))
        page, box = self.page()
        card = self.card(box, 'resume_title', 'resume_hint')
        fields['workspace'] = self.field(card, 'workspace', self.edit(cfg['workspace']))
        card.addWidget(self.button('browse', lambda: self.choose_project(name)))
        fields['session'] = self.field(card, 'session', self.edit(cfg['session']))
        fields['resume_time'] = self.field(card, 'resume_time', self.edit(cfg['resume_time']))
        prompt = QTextEdit()
        prompt.setAcceptRichText(False)
        prompt.setPlainText(cfg['prompt'])
        prompt.setMinimumHeight(110)
        fields['prompt'] = self.field(card, 'prompt', prompt)
        numbers = QHBoxLayout()
        for key, label, low, high in [('retry_minutes', 'retry', 5, 240), ('max_attempts', 'attempts', 1, 10), ('timeout_minutes', 'timeout', 1, 240)]:
            group = QVBoxLayout()
            spin = QSpinBox()
            spin.setRange(low, high)
            spin.setValue(cfg[key])
            spin.setMinimumHeight(38)
            fields[key] = spin
            self.field(group, label, spin)
            numbers.addLayout(group)
        card.addLayout(numbers)
        actions = QHBoxLayout()
        actions.addWidget(self.button('arm', lambda: self.arm(name), True))
        actions.addWidget(self.button('cancel', lambda: self.cancel(name)))
        card.addLayout(actions)
        box.addStretch()
        tabs.addTab(page, self.tr('resume'))
        page, box = self.page()
        box.addWidget(self.label('activity_hint', 'muted'))
        log = QTextBrowser()
        log.setMinimumHeight(220)
        self.log_widgets[name] = log
        box.addWidget(log, 1)
        box.addWidget(self.button('logs', self.open_logs))
        tabs.addTab(page, self.tr('activity'))
        self.banner = getattr(self, 'banner', {})
        banner = QLabel()
        banner.setObjectName('muted')
        banner.setWordWrap(True)
        self.banner[name] = banner
        layout.addWidget(banner)
        layout.addWidget(self.button('save', lambda: self.save_provider(name), True))
        return outer

    def settings_page(self):
        page, box = self.page()
        box.addWidget(self.label('settings', 'title'))
        box.addWidget(self.label('settings_hint', 'muted'))
        card = self.card(box, 'appearance')
        self.language_combo = QComboBox()
        self.language_combo.addItem('עברית', 'he')
        self.language_combo.addItem('English', 'en')
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.settings['language']))
        self.field(card, 'language', self.language_combo)
        self.theme_combo = QComboBox()
        for key in ['dark', 'light']:
            self.theme_combo.addItem(self.tr(key), key)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(self.settings['theme']))
        self.field(card, 'theme', self.theme_combo)
        card.addWidget(self.label('settings_note', 'muted'))
        card = self.card(box, 'behavior')
        self.close_combo = QComboBox()
        for key in ['ask', 'minimize']:
            self.close_combo.addItem(self.tr(key), key)
        self.close_combo.setCurrentIndex(self.close_combo.findData(self.settings['close_action']))
        self.field(card, 'close_action', self.close_combo)
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(5, 60)
        self.refresh_spin.setValue(self.settings['refresh_seconds'])
        self.field(card, 'refresh', self.refresh_spin)
        box.addWidget(self.button('apply', self.save_ui_settings, True))
        card = self.card(box, 'startup', 'startup_hint')
        startup_actions = QHBoxLayout()
        startup_actions.addWidget(self.button('startup_on', lambda: self.startup(True)))
        startup_actions.addWidget(self.button('startup_off', lambda: self.startup(False)))
        card.addLayout(startup_actions)
        card = self.card(box, 'storage')
        path = self.edit(str(self.engine.directory))
        path.setReadOnly(True)
        card.addWidget(path)
        card.addWidget(self.button('logs', self.open_logs))
        box.addStretch()
        return page

    def experiment_page(self):
        page, box = self.page()
        box.addWidget(self.label('experiment', 'title'))
        box.addWidget(self.label('experiment_hint', 'muted'))
        badge = self.label('planned', 'badge')
        box.addWidget(badge)
        browser = QTextBrowser()
        browser.setHtml(experiment_html(self.settings['language']))
        browser.setMinimumHeight(430)
        box.addWidget(browser, 1)
        return page

    def capture(self):
        for name, fields in self.fields.items():
            for key, widget in fields.items():
                if isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    value = widget.value()
                elif isinstance(widget, QTextEdit):
                    value = widget.toPlainText()
                else:
                    value = widget.text()
                self.drafts[name][key] = value

    def config(self, name):
        self.capture()
        cfg = copy.deepcopy(self.drafts[name])
        try:
            core.parse_times(cfg['times'])
            times = core.parse_times(cfg['resume_time'])
        except ValueError:
            raise ValueError(self.tr('invalid_times')) from None
        if len(times) != 1:
            raise ValueError(self.tr('one_time'))
        if not cfg['prompt'].strip():
            raise ValueError(self.tr('no_prompt'))
        return cfg

    def error(self, exc):
        message = str(exc)
        if self.settings['language'] == 'en':
            engine_messages = {
                'יש לבחור תיקיית פרויקט קיימת.': self.tr('no_project'),
                'יש להזין מזהה שיחה מדויק; אין בחירה אוטומטית של השיחה האחרונה.': self.tr('no_session'),
                'שירות זה כבר רץ במתזמן.': 'This service is already running in this scheduler.',
            }
            message = engine_messages.get(message, message)
        QMessageBox.warning(self, self.tr('error'), message)

    def save_provider(self, name):
        try:
            cfg = self.config(name)
            values = copy.deepcopy(self.engine.config)
            values[name] = cfg
            self.engine.save_config(values)
            self.banner[name].setText(self.tr('saved_hint'))
            self.refresh(tick=False)
        except Exception as exc:
            self.error(exc)

    def save_ui_settings(self):
        self.capture()
        settings = {**self.settings, 'language': self.language_combo.currentData(),
                    'theme': self.theme_combo.currentData(), 'close_action': self.close_combo.currentData(),
                    'refresh_seconds': self.refresh_spin.value()}
        try:
            core.atomic_json(self.settings_path, settings)
        except Exception as exc:
            self.error(exc)
            return
        self.settings = settings
        running = self.timer.isActive()
        self.build()
        self.refresh(tick=False)
        if running:
            self.timer.start(settings['refresh_seconds'] * 1000)

    def choose_project(self, name):
        path = QFileDialog.getExistingDirectory(self, self.tr('workspace'), self.fields[name]['workspace'].text())
        if path:
            self.fields[name]['workspace'].setText(path)

    def check_cli(self, name):
        try:
            value = self.fields[name]['executable'].text().strip()
            try:
                exe = core.resolve_executable(value)
            except ValueError:
                raise ValueError(self.tr('missing') + ': ' + value) from None
            argv = core.windows_wrapper([exe, '--version'])
            process = QProcess(self)
            self.probes.append(process)
            self.check_widgets[name].setEnabled(False)
            self.banner[name].setText(self.tr('checking'))
            def finished(code, status):
                if process not in self.probes:
                    return
                output = bytes(process.readAllStandardOutput()).decode('utf-8', errors='replace').strip()
                error = bytes(process.readAllStandardError()).decode('utf-8', errors='replace').strip()
                success = code == 0 and bool(output)
                self.checks[name] = (value, output if success else error or 'Version check failed')
                self.check_widgets[name].setEnabled(True)
                self.banner[name].setText((self.tr('detected') + ' · ' + output) if success else self.tr('error') + ' · ' + (error or 'Version check failed'))
                self.probes.remove(process)
                process.deleteLater()
            process.finished.connect(finished)
            def failed(error):
                if error != QProcess.ProcessError.FailedToStart:
                    return
                self.check_widgets[name].setEnabled(True)
                self.banner[name].setText(self.tr('error') + ' · ' + process.errorString())
                if process in self.probes:
                    self.probes.remove(process)
                process.deleteLater()
            process.errorOccurred.connect(failed)
            process.start(argv[0], argv[1:])
            def timeout():
                if process in self.probes and process.state() != QProcess.ProcessState.NotRunning:
                    process.kill()
            QTimer.singleShot(20000, self, timeout)
        except Exception as exc:
            self.error(exc)

    def preview(self, name):
        try:
            self.capture()
            cfg = self.drafts[name]
            try:
                core.resolve_executable(cfg['executable'])
            except ValueError:
                raise ValueError(self.tr('missing') + ': ' + cfg['executable']) from None
            command = core.command(name, cfg, 'trigger')
            dialog = QDialog(self)
            dialog.setWindowTitle(self.tr('preview_title'))
            dialog.resize(720, 360)
            box = QVBoxLayout(dialog)
            box.addWidget(self.label('preview_title', 'cardTitle'))
            text = QTextEdit()
            text.setReadOnly(True)
            text.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            text.setPlainText(json.dumps(command, ensure_ascii=False, indent=2))
            box.addWidget(text)
            dialog.exec()
        except Exception as exc:
            self.error(exc)

    def arm(self, name):
        try:
            cfg = self.config(name)
            if not Path(cfg['workspace']).is_dir():
                raise ValueError(self.tr('no_project'))
            import re
            if not re.fullmatch(r'[A-Za-z0-9_-]{6,200}', cfg['session']):
                raise ValueError(self.tr('no_session'))
            self.engine.arm(name, cfg)
            due = self.engine.state['jobs'][name]['due']
            when = datetime.fromtimestamp(due).astimezone().strftime('%Y-%m-%d %H:%M %Z')
            self.banner[name].setText(self.tr('armed') + ' · ' + when)
            self.refresh(tick=False)
        except Exception as exc:
            self.error(exc)

    def cancel(self, name):
        self.engine.cancel(name)
        self.banner[name].setText(self.tr('cancelled'))
        self.refresh(tick=False)

    def startup(self, enabled):
        try:
            core.startup_shortcut(enabled)
            QMessageBox.information(self, self.tr('startup'), self.tr('startup_enabled' if enabled else 'startup_disabled'))
        except Exception as exc:
            self.error(exc)

    def open_logs(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.engine.directory)))

    def refresh(self, tick=True):
        self.clock.setText(core.now().strftime('%d %b %Y\n%H:%M:%S %Z'))
        if tick:
            try:
                self.engine.tick()
            except Exception as exc:
                self.timer.stop()
                self.error(exc)
        while not self.engine.events.empty():
            self.history.append(self.engine.events.get_nowait())
        self.history = self.history[-200:]
        with self.engine.lock:
            today = str(core.now().date())
            for name, widgets in self.status_widgets.items():
                detected, enabled, attempted, confirmed, next_job = widgets
                cfg = self.engine.config[name]
                try:
                    core.resolve_executable(self.fields[name]['executable'].text())
                    detected.setText('● ' + self.tr('detected'))
                except ValueError:
                    detected.setText('○ ' + self.tr('missing'))
                enabled.setText(self.tr('on' if cfg['enabled'] else 'off'))
                attempted.setText(str(sum(key.startswith(today + '|' + name + '|') for key in self.engine.state['fired'])))
                confirmed.setText(str(self.engine.state.get('confirmed_triggers', {}).get(today + '|' + name, 0)))
                job = self.engine.state['jobs'].get(name)
                if job:
                    when = datetime.fromtimestamp(job['due']).astimezone().strftime('%d/%m %H:%M')
                    next_job.setText(self.tr(job['status']) + ' · ' + when)
                else:
                    next_job.setText(self.tr('none'))
                events = [event for event in self.history if event.get('service') == name]
                if events:
                    lines = []
                    for event in reversed(events):
                        at = html.escape(event.get('at', ''))
                        label = html.escape(self.tr(event.get('kind', '')) + ' · ' + self.tr(event.get('status', '')))
                        lines.append(f'<p><b>{label}</b><br><small>{at}</small></p>')
                    self.log_widgets[name].setHtml(''.join(lines))
                else:
                    self.log_widgets[name].setPlainText(self.tr('empty'))

    def apply_theme(self):
        dark = self.settings['theme'] == 'dark'
        bg, panel, field, side = ('#101722', '#182230', '#111c29', '#0c121b') if dark else ('#f3f5f9', '#ffffff', '#f7f9fc', '#e9eef5')
        text, muted, border = ('#e9eff8', '#93a5bd', '#2a394c') if dark else ('#14243a', '#5b6d84', '#d9e1ec')
        self.setStyleSheet(f'''
            QWidget {{ color: {text}; font-family: "Segoe UI"; font-size: 10pt; }}
            QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {bg}; }}
            #sidebar {{ background: {side}; border: none; }}
            #brand {{ font-size: 20pt; font-weight: 700; color: #52d4be; }}
            #title {{ font-size: 23pt; font-weight: 700; }}
            #cardTitle {{ font-size: 13pt; font-weight: 600; }}
            #muted, #eyebrow {{ color: {muted}; font-size: 9pt; }}
            #eyebrow {{ font-weight: 600; }}
            #card, #stat {{ background: {panel}; border: 1px solid {border}; border-radius: 14px; }}
            #stat {{ padding: 8px; }}
            #statValue {{ font-size: 13pt; font-weight: 600; }}
            #badge {{ background: {panel}; border: 1px solid {border}; border-radius: 10px; padding: 7px 12px; color: {muted}; font-size: 9pt; }}
            QLineEdit, QTextEdit, QTextBrowser, QSpinBox, QComboBox {{ background: {field}; border: 1px solid {border}; border-radius: 8px; padding: 8px; selection-background-color: #267d75; }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border: 1px solid #4ed3bc; }}
            QPushButton {{ border: 1px solid {border}; border-radius: 8px; background: {panel}; padding: 8px 15px; font-weight: 600; }}
            QPushButton:hover {{ background: {border}; }}
            QPushButton#primary {{ color: #08241f; background: #59dbc2; border: none; }}
            QPushButton#primary:hover {{ background: #7ce8d2; }}
            QPushButton#nav {{ background: transparent; border: none; text-align: {"right" if self.settings['language'] == 'he' else "left"}; padding: 12px; color: {muted}; }}
            QPushButton#nav:checked {{ color: #52d4be; background: {panel}; }}
            QPushButton:disabled {{ color: {muted}; }}
            QTabWidget::pane {{ border: 1px solid {border}; border-radius: 10px; background: {bg}; }}
            QTabBar::tab {{ background: transparent; color: {muted}; padding: 12px 20px; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ color: {text}; border-bottom: 2px solid #52d4be; }}
            QCheckBox {{ spacing: 10px; padding: 5px 0; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {muted}; background: {field}; }}
            QCheckBox::indicator:checked {{ background: #52d4be; border-color: #52d4be; }}
            QScrollBar:vertical {{ background: {bg}; width: 8px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {border}; min-height: 25px; border-radius: 4px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QToolTip {{ background: {panel}; color: {text}; border: 1px solid {border}; }}
            QMessageBox, QDialog {{ background: {bg}; }}
        ''')

    def explicit_quit(self):
        self.force_quit = True
        self.close()
        self.force_quit = False

    def closeEvent(self, event):
        if self.settings['close_action'] == 'minimize' and not getattr(self, 'force_quit', False):
            self.showMinimized()
            event.ignore()
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle(self.tr('close_title'))
        self.capture()
        unsaved = self.drafts != self.engine.config
        dialog.setText(self.tr('close_hint') + ('\n\n' + self.tr('unsaved') if unsaved else ''))
        quit_button = dialog.addButton(self.tr('quit'), QMessageBox.ButtonRole.AcceptRole)
        keep_button = dialog.addButton(self.tr('keep'), QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(keep_button)
        dialog.exec()
        if dialog.clickedButton() != quit_button:
            event.ignore()
            return
        self.timer.stop()
        for name in core.PROVIDERS:
            if name in self.engine.active:
                self.engine.cancel(name)
        for process in self.probes:
            process.kill()
        event.accept()


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('AI Window Scheduler')
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    try:
        lock = core.acquire_lock()
        window = SchedulerWindow()
    except Exception as exc:
        QMessageBox.critical(None, 'AI Window Scheduler', str(exc))
        return 1
    screen = app.primaryScreen().availableGeometry()
    window.resize(min(1120, screen.width() - 40), min(760, screen.height() - 40))
    if '--minimized' in sys.argv:
        window.showMinimized()
    else:
        window.show()
    result = app.exec()
    lock.close()
    return result


if __name__ == '__main__':
    sys.exit(run())
