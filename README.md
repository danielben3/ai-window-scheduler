# AI Window Scheduler

A Windows desktop scheduler for Codex, Claude Code, and Antigravity CLI.
Schedule a small daily request or a one-time continuation of an exact CLI
conversation. Includes Hebrew (RTL), English, dark and light themes, and
local activity logs.

**Experimental preview, v0.1.0.** Start with a disposable trial folder.
All daily schedules are disabled by default. This is an independent community
project, not an official OpenAI, Anthropic, or Google product.

[מדריך בעברית](README_HE.md) · [Download](https://github.com/danielben3/ai-window-scheduler/releases)
· [Report a bug](https://github.com/danielben3/ai-window-scheduler/issues)

## Install and launch

Use Windows 10 or 11 with 64-bit Python 3.11–3.15 and the Python launcher
(`py`). Local verification used Python 3.14. The only direct Python dependency
is `PySide6-Essentials==6.12.0`, installed separately by setup.

1. Download the release ZIP or clone this repository, and extract it to a
   permanent folder. Don't run it inside the ZIP.
2. Run `Setup.cmd`. It creates `.venv` and installs the pinned dependencies.
3. Install the official CLI for each provider you want to use, then sign in
   through that CLI. You don't need all three providers.
4. Run `Start.cmd`. The initial language is Hebrew. Open **הגדרות** (Settings),
   choose **English**, and save to switch the interface.
5. Select a provider and use **Check connection**. This only runs `--version`;
   it does not validate your account or send an AI request. If the command isn't
   found, enter its full native `.exe` path or supported PowerShell shim path.

The commands are `codex`, `claude`, and `agy`. A standalone desktop AI app is
not a substitute for its CLI. Raw `.cmd`/`.bat` shims require a sibling `.ps1`
shim; native executables are preferred. No administrator access is needed.

## Daily requests

On the provider's daily request tab, enter one or more local times, such as
`08:00, 15:00`, enable daily requests, and save that provider's settings.
An empty model field uses the CLI's default model.

Each request asks for exactly `OK`, in a separate working folder. Codex uses
read-only mode, Claude's trigger disables tools and MCP tools, and Antigravity
uses plan mode. Existing CLI rules, hooks, and plugins can still affect behavior
and token usage. Plan mode is not a filesystem sandbox guarantee.

**A tiny prompt can load a large context.** In initial live trials, Codex used
24,498 input tokens (13,440 cached), and Antigravity used 30,136 input tokens.
Context reduction remains open work. Review provider usage before enabling
daily runs. The app does not measure tokens or determine a provider's reset
time. It does not bypass limits or guarantee that a request starts a usage
window. Check that your CLI uses the intended account and billing arrangement.

## Continue a conversation once

Use a disposable project first; live continuation has not yet been verified.
The continuation can edit files with the permissions available to its CLI.

1. Create a conversation in the relevant CLI, and copy its exact session ID.
2. Enter that ID, its project folder, a precise continuation instruction, and
   the next local continuation time.
3. Inspect **Preview command**, then choose **Arm one continuation**. If the
   time has passed today, the job is scheduled for tomorrow; check the date.
4. After completion, review the project and activity log. A successful job
   does not repeat the next day.

The app never selects the latest conversation automatically. Desktop or cloud
conversations may not be accessible to the local CLI. Only recognized usage
limit errors retry, within the configured attempt count. Other failures stop
for inspection. Codex continuation uses workspace-write with interactive
approvals disabled; the other providers retain their CLI permission policy.
No provider's permission-bypass flag is added.

**Cancel / stop** affects the provider process started by this scheduler.
Cancellation does not undo file edits. After a crash, interrupted continuation
jobs require inspection and rearming instead of automatic replay.

## Settings and local data

Settings include language, theme, close behavior, refresh interval (5–60
seconds), and optional launch at Windows sign-in. Saving interface settings
preserves provider drafts; saving a provider commits only that provider.
The sidebar **Quit** command exits even when close behavior is set to minimize.

Data is stored in `%LOCALAPPDATA%\AIWindowScheduler`: `config.json`,
`ui_settings.json`, `state.json`, `history.jsonl`, and CLI stdout/stderr in
`logs/`. Logs and saved continuation instructions may contain private project
content. Review and redact them before sharing. Credentials remain managed by
the provider CLIs; common inherited API-key environment variables are removed
from launched processes, which does not independently verify billing mode.

The app must remain running, with Windows awake and signed in. It does not wake
the computer or run as a Windows service. Daily requests more than 90 seconds
late are skipped; continuations more than 10 minutes late need rearming.
Times use your Windows timezone. Only one scheduler instance runs per user.
If you move the app, recreate its optional sign-in shortcut.

To uninstall, cancel pending work, disable launch at sign-in, quit the app,
and remove its folder. Keep or remove the local data separately as needed.

## Verification status

The initial release has 20 offline engine/UI tests. These use temporary data
and mocked provider responses; they send no AI requests. They cover duplicate
prevention, bounded retries, cancellation, crash handling, and preservation of
settings and drafts across language changes.

| Provider | CLI version probed | Real daily request | Real continuation |
| --- | --- | --- | --- |
| Codex | 0.164.0-alpha.11.1 | OK, one request | Not tested |
| Claude Code | 2.1.177 | Not tested | Not tested |
| Antigravity | 1.1.22 | OK, one request | Not tested |

These observations are from October 26, 2026, on one Windows computer.
Version detection alone is not end-to-end compatibility. Provider CLI flags
and output formats may change. Reset behavior, every permission scenario,
and the Windows sign-in shortcut have not been validated end to end.
Use the built-in trial plan to validate your own environment.

Run local tests from the repository folder:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.venv\Scripts\python.exe -m unittest -v
```

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md) for development and bug reports.
Useful next work includes reducing trigger context, verifying disposable
session continuations, and testing more CLI versions. No live requests run
in CI. Report reproducible problems with redacted logs and CLI versions.

## License

Project source is available under the [MIT license](LICENSE). Qt for Python
and other separately installed dependencies keep their own licenses; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
