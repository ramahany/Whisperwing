# Whisperwing — Floating Dictation Companion

A cute floating desktop mascot for Windows that records your speech and types
the transcription into whatever app you're using — 100% locally, fully
offline. No APIs, no accounts, no cloud, no telemetry.

Built with Python + PySide6, Faster-Whisper, sounddevice and keyboard.

## Features

- Floating, draggable mascot with four states: idle / awake / listening / typing
- Global hotkey (default `Ctrl + Alt + Space`) to start and stop dictation
- Click the mascot to start/stop as well; right-click for a quick menu
- Local transcription with Faster-Whisper — English, Arabic or auto-detect
- Text is typed into the focused app (browsers, editors, chat apps, Office…)
- Polished dark settings window: General / Speech / Appearance / Hotkeys
- System tray icon: Show mascot / Hide mascot / Settings / Restart / Exit
- Auto-stop after ~2 seconds of silence, plus a 120 s recording cap
- Local rotating log file, no analytics

## Requirements

- Windows 10/11
- Python 3.10+ (64-bit)
- A microphone

## Setup

```bat
cd "voice dictation"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### First run & offline note

Whisper models are downloaded **once** (about 460 MB for the default `small`
model) into the Hugging Face cache (`%USERPROFILE%\.cache\huggingface`).
After that the app is fully offline. To pre-download without launching the
app:

```bat
python -c "from faster_whisper import WhisperModel; WhisperModel('small')"
```

The application itself never contacts any server.

## Mascot images

Drop your PNGs into `images/` (transparent background recommended):

| File            | State    | Shown when…                    |
| --------------- | -------- | ------------------------------ |
| `idle.png`      | Idle     | Default, sleeping              |
| `awake.png`     | Awake    | Hovered / recently interacted  |
| `listening.png` | Listening | Recording microphone input    |
| `typing.png`    | Typing   | Transcribing & inserting text  |

Missing files are handled gracefully — the mascot falls back to a built-in
glowing orb until you add the images. The tray icon is `assets/tray_icon.png`
(optional; falls back to the orb too).

## Usage

- `Ctrl + Alt + Space` (or click the mascot): start dictation
- Speak; recording stops automatically after ~2 s of silence, or stop sooner
  by pressing the hotkey / clicking again
- The transcribed text is typed into whatever app currently has focus — the
  mascot never steals keyboard focus
- Drag the mascot anywhere; its position is remembered
- Right-click the mascot: Settings / Hide mascot / Exit

## Settings

Stored in `config/settings.json`, created and updated automatically:
hotkey, language (`auto` / `en` / `ar`), Whisper model
(`tiny` / `base` / `small` / `medium` / `large-v3`), mascot scale,
always-on-top, launch on startup, and last mascot position.

## Packaging with PyInstaller

```bat
pyinstaller --noconfirm --windowed --name Whisperwing ^
  --add-data "images;images" --add-data "assets;assets" main.py
```

`config/` and `logs/` are created next to the executable when it runs.

## Troubleshooting

- **Hotkey doesn't trigger** — another app may own that shortcut; pick a new
  one in Settings → Hotkeys. Windows blocks global hooks into elevated (admin)
  windows unless the app also runs as admin.
- **No transcription** — check the microphone (Windows Settings → Privacy →
  Microphone) and that the default input device works. Errors also appear as
  tray notifications.
- **Arabic text looks wrong** — make sure the target app supports Arabic
  input; text is injected as Unicode keystrokes.
- **First dictation is slow** — the model loads in the background at startup;
  the very first transcription may still wait a few seconds. Bigger models
  are slower.
- Logs: `logs/whisperwing.log`

## Project structure

```
main.py                     entry point & application controller
ui/mascot_window.py         floating mascot window + state system
ui/settings_window.py       settings UI (General / Speech / Appearance / Hotkeys)
ui/style.py                 purple/black theme, global stylesheet, dark title bars
services/speech_service.py  microphone capture + Faster-Whisper transcription
services/typing_service.py  text injection into the focused app
services/hotkey_service.py  global hotkey + shortcut recorder
services/tray_service.py    system tray icon and menu
services/startup_service.py launch-on-startup (HKCU Run key)
config/settings_manager.py  settings persistence + asset lookup
config/settings.json        stored settings
images/                     mascot PNGs (provided manually)
assets/                     tray icon (optional)
logs/                       local rotating log (created at runtime)
```
"# Whisperwing" 
