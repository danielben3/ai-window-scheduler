# Contributing

Bug reports, translations, and focused pull requests are welcome.
This project is an experimental Windows desktop app.

## Development

Run `Setup.cmd`, then run the offline suite with
`.venv\Scripts\python.exe -m unittest -v`. For headless execution, set
`QT_QPA_PLATFORM=offscreen`. Tests must use temporary data and mocked provider
responses. Never send real provider requests from automated tests or CI.

`scheduler.py` owns scheduling and CLI execution; `scheduler_ui.py` owns the
PySide6 interface and Hebrew/English strings. Keep behavior changes focused,
add meaningful regression coverage, and update both languages where needed.
Preserve exact conversation IDs, bounded retries, disabled defaults, and
duplicate prevention across reloads. Don't bundle provider executables or Qt.

## Reporting bugs

Open an issue with Windows/Python/CLI versions, steps to reproduce, expected
behavior, actual behavior, and a small redacted output sample if needed.
Do not upload your data folder, complete logs, session IDs, credentials,
private prompts, or personal paths. Use a disposable project for live trials.
State whether the failure is a version probe, daily request, or continuation.
