"""Local Windows scheduler engine; Qt interface in scheduler_ui.py."""
from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('LOCALAPPDATA', str(ROOT))) / 'AIWindowScheduler'
PING = 'Reply with exactly OK. Do not use tools, read files, or take any other action.'
CONTINUE = ('המשך את המשימה שכבר אושרה מההתקדמות השמורה. בדוק את המצב הנוכחי לפני עריכה. '
            'עצור כשהמשימה הושלמה או כשנדרש קלט מהמשתמש. '
            'אין לפרסם, לפרוס, לשלוח הודעות או להתחיל משימות שאינן קשורות.')
PROVIDERS = {'Codex': 'codex', 'Claude Code': 'claude', 'Antigravity': 'agy'}
QUOTA = re.compile(r'(usage limit (?:has been )?(?:reached|exceeded)|'
                   r'(?:5|five)[ -]hour limit|hit your usage limit|'
                   r'quota (?:has been )?(?:exhausted|exceeded)|'
                   r'rate_limit_exceeded|insufficient_quota|weekly limit reached)', re.I)


def now():
    return datetime.now().astimezone()


def stamp():
    return now().isoformat(timespec='seconds')


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)


def load_json(path, default):
    if not path.exists():
        return copy.deepcopy(default)
    # Fail visibly rather than silently resetting an invalid existing state.
    return json.loads(path.read_text(encoding='utf-8'))


def parse_times(value):
    values = [s.strip() for s in value.split(',') if s.strip()]
    if not values or any(not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', s) for s in values):
        raise ValueError('יש להזין HH:MM, לדוגמה 08:00 או 08:00, 15:00')
    return sorted(set(values))


def next_time(value, current):
    hour, minute = map(int, parse_times(value)[0].split(':'))
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return target.timestamp()


def defaults():
    return {name: {'enabled': False, 'times': '08:00', 'executable': exe,
                   'model': '', 'workspace': '', 'session': '',
                   'resume_time': '13:00', 'prompt': CONTINUE,
                   'retry_minutes': 30, 'max_attempts': 3,
                   'timeout_minutes': 60} for name, exe in PROVIDERS.items()}


def resolve_executable(value):
    found = shutil.which(value)
    if not found and Path(value).is_file():
        found = str(Path(value).resolve())
    if not found:
        raise ValueError(f'כלי CLI לא נמצא: {value}. יש להתקין אותו ולהתחבר תחילה.')
    return found


def command(name, cfg, kind):
    exe = resolve_executable(cfg['executable'])
    prompt = PING if kind == 'trigger' else cfg['prompt']
    if kind == 'resume' and not re.fullmatch(r'[A-Za-z0-9_-]{6,200}', cfg['session']):
        raise ValueError('יש להזין מזהה שיחה מדויק; אין בחירה אוטומטית של השיחה האחרונה.')
    model = ['--model', cfg['model']] if cfg['model'].strip() else []
    if name == 'Codex':
        base = [exe, '--ask-for-approval', 'never', 'exec',
                '--sandbox', 'read-only' if kind == 'trigger' else 'workspace-write']
        if kind == 'trigger':
            return base + ['--json', '--ephemeral', '--skip-git-repo-check'] + model + [prompt]
        return base + ['resume', '--json'] + model + [cfg['session'], prompt]
    if name == 'Claude Code':
        base = [exe, '-p', prompt, '--output-format', 'json'] + model
        if kind == 'trigger':
            return base + ['--max-turns', '1', '--tools', '', '--disallowedTools', 'mcp__*']
        return base + ['--resume', cfg['session'], '--max-turns', '30']
    base = [exe, '-p', prompt, '--output-format', 'json'] + model
    return base + (['--mode', 'plan'] if kind == 'trigger' else
                   ['--conversation', cfg['session'], '--print-timeout',
                    str(cfg['timeout_minutes']) + 'm'])


def windows_wrapper(argv):
    """Avoid cmd.exe interpolation for npm .cmd shims and arbitrary prompts."""
    if os.name != 'nt' or Path(argv[0]).suffix.lower() not in ('.cmd', '.bat', '.ps1'):
        return argv
    if Path(argv[0]).suffix.lower() in ('.cmd', '.bat'):
        ps1 = Path(argv[0]).with_suffix('.ps1')
        if not ps1.exists():
            raise ValueError('יש להשתמש בקובץ exe מקורי או במעטפת ps1; אין תמיכה ישירה בקובצי cmd או bat.')
        argv = [str(ps1)] + argv[1:]
    payload = base64.b64encode(json.dumps(argv).encode('utf-8')).decode('ascii')
    script = ("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); "
              "$a=ConvertFrom-Json ([Text.Encoding]::UTF8.GetString("
              "[Convert]::FromBase64String('" + payload + "'))); "
              "$e=$a[0]; $r=@($a | Select-Object -Skip 1); & $e @r; exit $LASTEXITCODE")
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    return ['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded]


def decode_result(name, rc, stdout, stderr, kind):
    """Only error channels/envelopes can trigger quota retries, never task prose."""
    error_text = stderr if rc != 0 else ''
    response = ''
    bad = rc != 0
    try:
        if name == 'Codex':
            for line in stdout.splitlines():
                event = json.loads(line)
                if event.get('type') in ('error', 'turn.failed'):
                    bad = True
                    error_text += json.dumps(event)
                item = event.get('item', {})
                if item.get('type') == 'agent_message':
                    response = item.get('text', '')
        else:
            event = json.loads(stdout)
            response = event.get('result', event.get('response', ''))
            if event.get('is_error') or (name == 'Antigravity' and event.get('status') != 'SUCCESS'):
                bad = True
                error_text += json.dumps(event)
            if event.get('permission_denials'):
                return 'blocked'
    except (ValueError, TypeError, AttributeError):
        return 'quota' if QUOTA.search(error_text) else 'unrecognized-output'
    if QUOTA.search(error_text):
        return 'quota'
    if bad:
        return 'failed'
    if not response or (kind == 'trigger' and str(response).strip() != 'OK'):
        return 'unexpected-response'
    return 'completed'


class Engine:
    def __init__(self, directory=DATA, runner=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.config = load_json(self.directory / 'config.json', defaults())
        self.state = load_json(self.directory / 'state.json', {'fired': {}, 'jobs': {}})
        self.events = queue.Queue()
        self.lock = threading.RLock()
        self.active = {}
        self.cancelled = set()
        self.runner = runner or self.run_cli
        # A process crash leaves work uncertain: never automatically replay it.
        for job in self.state['jobs'].values():
            if job['status'] == 'running':
                job['status'] = 'interrupted-check-project-before-rearming'
        self.save_state()

    def save_state(self):
        atomic_json(self.directory / 'state.json', self.state)

    def record(self, name, kind, status, **extra):
        row = dict(at=stamp(), service=name, kind=kind, status=status, **extra)
        with self.lock:
            with (self.directory / 'history.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
        self.events.put(row)

    def save_config(self, config):
        with self.lock:
            atomic_json(self.directory / 'config.json', config)
            self.config = copy.deepcopy(config)

    def arm(self, name, cfg, current=None):
        current = current or now()
        command(name, cfg, 'resume')  # Validate before arming, without sending a request.
        if not Path(cfg['workspace']).is_dir():
            raise ValueError('יש לבחור תיקיית פרויקט קיימת.')
        if len(parse_times(cfg['resume_time'])) != 1:
            raise ValueError('יש לבחור שעת חידוש אחת.')
        with self.lock:
            if name in self.active:
                raise ValueError('שירות זה כבר רץ במתזמן.')
            self.cancelled.discard(name)
            self.state['jobs'][name] = dict(status='waiting', attempts=0,
                due=next_time(cfg['resume_time'], current), config=copy.deepcopy(cfg))
            self.save_state()
        self.record(name, 'resume', 'armed', due=self.state['jobs'][name]['due'])

    def cancel(self, name):
        with self.lock:
            job = self.state['jobs'].get(name)
            if job:
                job['status'] = 'cancelled'
                self.save_state()
            self.cancelled.add(name)
            process = self.active.get(name)
            if isinstance(process, subprocess.Popen):
                self.kill(process)
        self.record(name, 'resume', 'cancelled')

    @staticmethod
    def kill(process):
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            process.kill()

    def tick(self, current=None, launch=True):
        current = current or now()
        due = []
        with self.lock:
            for name, cfg in self.config.items():
                job = self.state['jobs'].get(name)
                if name in self.active:
                    continue
                # Continuation takes precedence over a trigger in the same minute.
                if job and job['status'] == 'waiting' and current.timestamp() >= job['due']:
                    if current.timestamp() - job['due'] > 600:
                        job['status'] = 'missed-rearm-required'
                        self.record(name, 'resume', job['status'])
                    else:
                        job['attempts'] += 1
                        job['status'] = 'running'
                        due.append((name, copy.deepcopy(job['config']), 'resume'))
                        self.active[name] = True
                if name in self.active or not cfg['enabled']:
                    continue
                for hhmm in parse_times(cfg['times']):
                    key = f'{current.date()}|{name}|{hhmm}'
                    hour, minute = map(int, hhmm.split(':'))
                    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if 0 <= (current - target).total_seconds() < 90 and key not in self.state['fired']:
                        self.state['fired'][key] = stamp()
                        self.cancelled.discard(name)
                        due.append((name, copy.deepcopy(cfg), 'trigger'))
                        self.active[name] = True
                        break
            # Keep duplicate protection for recent dates only.
            cutoff = str(current.date() - timedelta(days=14))
            self.state['fired'] = {k: v for k, v in self.state['fired'].items() if k[:10] >= cutoff}
            self.save_state()
        if launch:
            for task in due:
                threading.Thread(target=self.execute, args=task, daemon=True).start()
        return due

    def execute(self, name, cfg, kind):
        self.record(name, kind, 'started', model=cfg['model'] or 'CLI default')
        try:
            if name in self.cancelled:
                status = 'cancelled'
            else:
                rc, out, err = self.runner(name, cfg, kind)
                status = decode_result(name, rc, out, err, kind)
        except Exception as exc:
            status = 'local-error'
            self.record(name, kind, status, detail=str(exc))
        with self.lock:
            if name in self.cancelled:
                status = 'cancelled'
            if kind == 'resume':
                job = self.state['jobs'][name]
                if status == 'quota' and job['attempts'] < cfg['max_attempts']:
                    job['status'] = 'waiting'
                    job['due'] = time.time() + cfg['retry_minutes'] * 60
                else:
                    job['status'] = status  # Terminal: successful work is never repeated daily.
                self.save_state()
            elif status == 'completed':
                counts = self.state.setdefault('confirmed_triggers', {})
                key = str(now().date()) + '|' + name
                counts[key] = counts.get(key, 0) + 1
                self.save_state()
            self.active.pop(name, None)
        self.record(name, kind, status)

    def run_cli(self, name, cfg, kind):
        argv = command(name, cfg, kind)
        cwd = Path(cfg['workspace']) if kind == 'resume' else self.directory / 'empty' / name
        cwd.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        # Never route these subscription requests through inherited API keys.
        for key in ('OPENAI_API_KEY', 'CODEX_API_KEY', 'ANTHROPIC_API_KEY',
                    'ANTHROPIC_AUTH_TOKEN', 'GEMINI_API_KEY', 'GOOGLE_API_KEY',
                    'GOOGLE_APPLICATION_CREDENTIALS'):
            env.pop(key, None)
        logs = self.directory / 'logs'
        logs.mkdir(exist_ok=True)
        prefix = f'{time.time_ns()}-{PROVIDERS[name]}-{kind}'
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with (logs / (prefix + '.stdout.txt')).open('wb') as out, \
             (logs / (prefix + '.stderr.txt')).open('wb') as err:
            process = subprocess.Popen(windows_wrapper(argv), cwd=str(cwd), env=env,
                stdin=subprocess.DEVNULL, stdout=out, stderr=err, creationflags=flags)
            with self.lock:
                self.active[name] = process
                if name in self.cancelled:
                    self.kill(process)
            try:
                rc = process.wait(timeout=120 if kind == 'trigger' else cfg['timeout_minutes'] * 60)
            except subprocess.TimeoutExpired:
                self.kill(process)
                process.wait()
                raise RuntimeError('זמן הריצה המרבי חלף. יש לבדוק את היומנים והפרויקט לפני תזמון נוסף.')
        # Bound parsing memory; full output remains on disk.
        def tail(path):
            with path.open('rb') as f:
                f.seek(max(0, path.stat().st_size - 2_000_000))
                return f.read().decode('utf-8', errors='replace')
        return rc, tail(logs / (prefix + '.stdout.txt')), tail(logs / (prefix + '.stderr.txt'))


def acquire_lock():
    DATA.mkdir(parents=True, exist_ok=True)
    handle = (DATA / 'scheduler.lock').open('a+b')
    handle.seek(0)
    if os.name == 'nt':
        import msvcrt
        if handle.read(1) == b'':
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return handle


def startup_shortcut(enable):
    if os.name != 'nt':
        raise ValueError('הפעלה אוטומטית זמינה ב־Windows בלבד.')
    shortcut = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Startup/AIWindowScheduler.lnk'
    if not enable:
        shortcut.unlink(missing_ok=True)
        return
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.exists():
        raise ValueError('pythonw.exe לא נמצא. יש להתקין Python רגיל עבור Windows.')
    payload = base64.b64encode(json.dumps([str(shortcut), str(pythonw),
        '"' + str(ROOT / 'scheduler.py') + '" --minimized', str(ROOT)]).encode()).decode()
    script = ("$a=ConvertFrom-Json ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"
              + payload + "'))); $w=New-Object -ComObject WScript.Shell; "
              "$s=$w.CreateShortcut($a[0]); $s.TargetPath=$a[1]; $s.Arguments=$a[2]; "
              "$s.WorkingDirectory=$a[3]; $s.Save()")
    encoded = base64.b64encode(script.encode('utf-16le')).decode()
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                   check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)


def main():
    from scheduler_ui import run
    return run()


if __name__ == '__main__':
    sys.exit(main())
