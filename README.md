# GlucoWidget

A desktop widget (Windows and Linux) that shows your **FreeStyle Libre** glucose in real time via **LibreLinkUp**, with optional AI analysis using your own API key (OpenAI, Claude, Gemini, OpenRouter, Groq, DeepSeek, Mistral, Ollama, or any OpenAI-compatible API).

> ⚠️ Not a medical device. Always confirm on your official reader/app before making any treatment decision. Not affiliated with Abbott.

## Features

- Frameless floating window: draggable, always on top, translucent ("glass" style), light/dark theme (follows the system)
- Large value with trend arrow, time since the reading, change, mini chart (3/6/12 h) with target range and tooltip
- Meaningful colors (low / in range / high / outdated) **and** a text label — never color alone
- Compact mode (double-click), adjustable size and opacity
- **mg/dL** (default) or **mmol/L**
- **English** (default) and **Portuguese (Brazil)** interface — switch in Settings → Appearance → Language (or on the first screen of the setup assistant); AI analyses also answer in the chosen language
- Tray icon showing the current value; notifications when leaving the target range
- Setup assistant on first run, plus a demo mode
- AI analysis on demand (or automatic), with local metrics: mean, time in range, CV, GMI
- Password and API keys stored in the system keyring (Windows Credential Manager / Secret Service)

## Prerequisite: a LibreLinkUp account

LibreView has no public API. The widget uses the (unofficial) API of the **LibreLinkUp** app:

1. Install the **LibreLinkUp** app on your phone and create an account (it can use a different email than the patient's).
2. In the patient's **LibreLink** app: *Share → Connect LibreLinkUp app* → invite that email.
3. Accept the invitation in LibreLinkUp and finish the terms of use.
4. Use that email/password in the widget.

## Run from source

Requires Python 3.11+.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -e .
```

```bash
.venv/bin/glucowidget
```

On Windows, use `.venv\Scripts\pip` and `.venv\Scripts\glucowidget`.

Options:

- `--demo [normal|low|high|stale|offline|auth|nopatient]` — synthetic data to try the interface without an account
- `--onboarding` — reopen the setup assistant
- `--debug` — verbose logging

### Linux

- Qt needs the `libxcb-cursor0` package (Debian/Ubuntu: `sudo apt install libxcb-cursor0`).
- On **Wayland** sessions, the widget runs through XWayland automatically when `libxcb-cursor0` is installed, so that "always on top" and the saved position work. Without it, it runs on native Wayland, where the compositor may ignore those two options.
- The tray icon on GNOME needs the *AppIndicator* extension (included in Ubuntu).

## Build an executable

```bash
.venv/bin/pip install pyinstaller
```

```bash
.venv/bin/pyinstaller packaging/glucowidget.spec
```

The result is in `dist/GlucoWidget` (Linux) or `dist\GlucoWidget.exe` (Windows). PyInstaller cannot cross-build: build the `.exe` on a Windows machine. On Linux, PyInstaller also needs `binutils` (`sudo apt install binutils`).

Check that a build bundled everything it needs (SVG plugin, translations, icons, keyring backend). It writes a report and exits with code 0 when everything is fine:

```bash
dist/GlucoWidget --selftest report.txt
```

### Continuous integration

`.github/workflows/ci.yml` runs the tests on Linux and Windows for every push and pull request, then builds the executable on both systems, runs `--selftest` on it, and uploads the result as a downloadable artifact (Actions → latest run → Artifacts). On Windows it also checks that the Windows Credential Manager backend is the one in use.

## Font

The interface uses **Inter** if it is installed or if you drop the `.ttf` files into `src/glucowidget/assets/fonts/` (OFL license). Without it, it falls back to Segoe UI (Windows) or the system font.

## Tests

```bash
.venv/bin/pip install pytest
```

```bash
.venv/bin/python -m pytest
```

## Project layout

```
src/glucowidget/
  app.py            controller: polling, tray, alerts, AI
  i18n.py, locales/ translations (English source strings; catalog in locales/pt.py)
  config.py         settings (JSON) and secrets (keyring)
  libre/            LibreLinkUp client and models
  ai/               AI providers and prompt
  metrics.py        CGM metrics (TIR, CV, GMI)
  ui/               widget, chart, components, dialogs, theme (design tokens)
```

Settings are stored in `~/.config/glucowidget/` (Linux) or `%LOCALAPPDATA%\glucowidget\` (Windows).

## Translations

Strings in the code are written in English and marked with `tr("...")` (or `N_("...")` for constants). To add or change a language, edit `src/glucowidget/locales/pt.py`; `tests/test_i18n.py` fails if any string is missing a translation or has mismatched placeholders.
