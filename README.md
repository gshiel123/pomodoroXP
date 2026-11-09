# PomodoroXP

Cross-platform Pomodoro timer for Windows and macOS with optional Telegram notifications.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

On macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

The application runs from the system tray. Open **Settings** to enter a Telegram bot token and chat ID. The bot must receive at least one message from the target chat before **Find chat IDs** can discover it.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The Telegram token is stored in the operating system keyring. The chat ID and selected preset are stored using Qt's per-user application settings.
