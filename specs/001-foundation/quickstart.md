# Quickstart: Foundation — Running the App Locally

**Feature**: `001-foundation`
**Date**: 2026-04-15

---

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Node.js | 20 LTS or later | `node --version` |
| npm | 10+ | `npm --version` |
| Python | 3.11 or later | `python --version` |
| Git | any | `git --version` |

---

## Step 1 — Clone and Install Node Dependencies

```bash
git clone <repo-url>
cd AI-Proctoring-App
npm install
```

This installs Electron and all frontend dependencies including `@fontsource/manrope`,
`@fontsource/inter`, and `keytar`.

> **Note**: `keytar` is a native Node module. It requires a C++ build toolchain. If `npm install`
> fails with a node-gyp error, run: `npm install --global windows-build-tools` (Windows) or
> install Xcode Command Line Tools (macOS).

---

## Step 2 — Install Python Dependencies

```bash
cd python_bridge
pip install -r requirements.txt
cd ..
```

`requirements.txt` includes at minimum:
```
flask>=3.0.0
flask-cors>=4.0.0
```

---

## Step 3 — Create config.json

Copy the example configuration to the project root:

```bash
copy config.example.json config.json
```

Edit `config.json` to point to your LMS instance:

```json
{
  "baseUrl": "https://your-lms-domain.edu/api",
  "pythonPort": 5050
}
```

> ⚠️ **The `baseUrl` must start with `https://`.** The app will refuse to start with an HTTP URL.

---

## Step 4 — Start the App

```bash
npm start
```

This runs the Electron app. Electron will automatically spawn the Python bridge as a subprocess.
The loading screen will appear while the bridge starts, then the Login page will load.

---

## Step 5 — Verify the Setup

Open a second terminal while the app is running and test the bridge health endpoint:

```bash
curl http://127.0.0.1:5050/ping
```

Expected response:
```json
{"status": "ok", "version": "1.0.0", "timestamp": "2026-04-15T10:30:00.000Z"}
```

To verify design tokens are loading correctly:
1. In the running app, press `Ctrl+Shift+I` to open DevTools
2. In the Console tab, run:
   ```js
   getComputedStyle(document.documentElement).getPropertyValue('--color-primary')
   ```
3. Expected output: `#006687` (or similar with whitespace)

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| "Python not found" error screen | Python not on PATH | Add Python to system PATH and restart |
| "Port already in use" error screen | Port 5050 occupied | Change `pythonPort` in `config.json` or kill the conflicting process |
| "Configuration file not found" | `config.json` missing | Run Step 3 above |
| "Must use HTTPS" error | `baseUrl` uses `http://` | Update `config.json` `baseUrl` to `https://` |
| App opens a second window | Single-instance lock failed | Restart machine; check for ghost processes |
| Fonts rendering as system default | Build tools issue / asar | Run `npm run rebuild` then `npm start` |

---

## npm Scripts Reference

| Command | Description |
|---------|-------------|
| `npm start` | Launch the app in development mode |
| `npm run rebuild` | Rebuild native modules (keytar) for current Electron version |
| `npm run pack` | Package the app for Windows (electron-builder) |

---

## Development Tips

- The Python bridge logs are visible in the Electron main process console (terminal where you ran `npm start`).
- Use `Ctrl+Shift+I` in the Electron window to open Chromium DevTools for UI debugging.
- `config.json` is gitignored — never commit it. `config.example.json` is the committed template.
