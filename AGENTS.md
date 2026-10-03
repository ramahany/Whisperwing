# AGENTS.md

## Project Overview

This project is a Windows desktop floating dictation assistant built with Python.

The application displays a floating mascot that can record speech, transcribe it locally using Faster-Whisper, and insert text into whichever application currently has keyboard focus.

The mascot acts as the primary interface.

The application must run completely offline and require no API keys or cloud services.

---

# Core Goals

1. Floating mascot desktop companion.
2. Local speech-to-text using Faster-Whisper.
3. Global hotkey activation.
4. Text insertion into focused applications.
5. Elegant settings window.
6. Purple/black feminine developer aesthetic.
7. Modular and maintainable codebase.
8. Offline-first architecture.

---

# Technology Stack

Language:
- Python 3.10+

UI:
- PySide6

Speech Recognition:
- Faster-Whisper

Audio:
- sounddevice

Keyboard Injection:
- keyboard

Configuration:
- JSON

Packaging:
- PyInstaller

Threading:
- QThread

---

# Project Structure

project/
│
├── main.py
│
├── images/
│   ├── idle.png
│   ├── awake.png
│   ├── listening.png
│   └── typing.png
│
├── ui/
│   ├── mascot_window.py
│   └── settings_window.py
│
├── services/
│   ├── speech_service.py
│   ├── typing_service.py
│   ├── hotkey_service.py
│   └── tray_service.py
│
├── config/
│   └── settings.json
│
├── assets/
│   └── tray_icon.png
│
├── requirements.txt
│
├── README.md
│
└── AGENTS.md

---

# Mascot Image Rules

All mascot assets are provided manually.

Load assets only from:

images/

Required assets:

- idle.png
- awake.png
- listening.png
- typing.png

Do not generate placeholders.

Do not hardcode image data.

Gracefully handle missing files.

---

# Mascot States

## Idle

Image:
idle.png

Purpose:
Default sleeping state.

---

## Awake

Image:
awake.png

Purpose:
Ready state.

Displayed when user interacts with the mascot.

---

## Listening

Image:
listening.png

Purpose:
Recording microphone input.

---

## Typing

Image:
typing.png

Purpose:
Transcribing speech and injecting text.

---

# UI Guidelines

Theme:

- Dark mode
- Purple and black
- Soft gradients
- Elegant
- Slightly futuristic
- Clean
- Cozy
- Feminine but professional

The mascot should be the visual focus.

The settings window should feel modern and polished.

Avoid:

- Corporate dashboards
- Excessive animations
- Bright colors
- Overly playful UI
- Heavy visual effects

---

# Dictation Flow

Application starts

↓

Load settings

↓

Load mascot

↓

Register hotkey

↓

Wait for activation

↓

User activates dictation

↓

Switch to listening state

↓

Record audio

↓

Transcribe audio

↓

Switch to typing state

↓

Insert text

↓

Return to idle

---

# Speech Recognition Rules

Use:

Faster-Whisper

Default model:

small

Supported languages:

- English
- Arabic
- Auto Detect

All transcription must happen locally.

No external APIs.

No cloud processing.

---

# Text Injection Rules

Insert text into the currently focused application.

Use keyboard event simulation.

Must work with:

- Browsers
- Editors
- Messaging apps
- Office apps
- AI chat applications

Avoid application-specific integrations.

Use generic system-level typing.

---

# Settings Rules

Store settings in:

config/settings.json

Support:

- Hotkey
- Language
- Whisper model
- Mascot scale
- Launch on startup
- Always on top

Settings must persist between launches.

---

# Architecture Rules

Keep services separated.

UI components must not contain transcription logic.

Speech services must not contain UI logic.

Avoid giant files.

Prefer focused modules.

Keep code easy to extend.

---

# Performance Rules

Keep idle CPU usage low.

Run transcription in background threads.

Prevent UI freezes.

Load assets only once.

Avoid unnecessary polling.

---

# Logging Rules

Create lightweight local logging.

Log:

- Startup
- Model loading
- Recording start
- Recording stop
- Transcription events
- Errors

Do not collect analytics.

Do not send telemetry.

Do not track users.

---

# Development Rules

Prefer simplicity over complexity.

Prefer maintainability over cleverness.

Avoid premature optimization.

Avoid unnecessary abstractions.

Avoid creating infrastructure that is not currently needed.

Build the MVP first.

Future features can be added later.

---

# Testing Rules

Do not create:

- UI tests
- Selenium tests
- Playwright tests
- Visual regression tests
- End-to-end testing frameworks
- Mock environments

No dedicated testing folder should be created.

No automated UI testing should be implemented.

Only basic syntax validation is allowed during generation.

The user will manually test the application and request future fixes.

---

# Future Features (Not MVP)

Possible future additions:

- Voice commands
- Grammar correction
- AI rewriting
- Custom mascot packs
- GIF/Lottie mascot animations
- Smart editable-field detection
- Multiple mascot themes

These should not be implemented unless explicitly requested.

---

# Success Criteria

A successful implementation:

- Runs locally
- Uses Faster-Whisper
- Loads mascot images from the images folder
- Supports global hotkeys
- Records microphone input
- Transcribes speech
- Inserts text into focused applications
- Provides a polished settings UI
- Uses a purple/black aesthetic
- Requires no API keys
- Requires no paid services
- Requires no cloud infrastructure