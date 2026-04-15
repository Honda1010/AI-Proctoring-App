# Quickstart: Login Page (002-login-page)

**Branch**: `002-login-page` | **Date**: 2026-04-15
**Prerequisites**: spec 001-foundation fully implemented (bridge running, design tokens in place)

---

## Overview

This spec adds:
1. **`python_bridge/auth.py`** — `POST /login` endpoint on the Flask bridge
2. **`frontend/main.js`** additions — session restore check + `ipcMain.handle('bridge:login', ...)` + `ipcMain.handle('bridge:get-saved-session', ...)` + `ipcMain.handle('bridge:clear-session', ...)`
3. **`frontend/preload.js`** additions — `window.bridge.login()`, `window.bridge.getSavedSession()`, `window.bridge.clearSession()`
4. **`frontend/pages/login/index.html`** — full replacement of the stub from spec 001
5. **`frontend/pages/login/login.js`** — form controller
6. **`frontend/pages/login/login.css`** — page-specific styles (tokens only, no hex)

---

## Development Setup

Spec 001 must be complete. If not already done:

```powershell
# Install Node dependencies (Electron, keytar, fontsource)
npm install

# Install Python dependencies
pip install -r python_bridge/requirements.txt
```

After spec 002 implementation, add `requests` to Python requirements:
```powershell
pip install requests
```

---

## Running the App

```powershell
# Start Electron (spawns Python bridge automatically)
npm start
```

The app will start on the loading screen, bridge health is confirmed, then the session
restore check runs. If no saved session, the login page appears.

---

## Testing Login Flows Manually

### Happy Path — Live LMS
1. Ensure `config.json` has a valid `baseUrl` pointing to a live LMS instance
2. `npm start`
3. Enter valid student credentials → click LOGIN
4. Verify Electron navigates to the exam-code page stub

### Happy Path — Offline / Stub Mode
The Python bridge has no built-in stub mode in this spec. To test offline:
1. Temporarily modify `python_bridge/auth.py` to return the mock fixture directly
   (`specs/002-login-page/mocks/login-ok.json`) instead of calling requests
2. Run `npm start` and verify navigation to exam-code page

### Error Scenarios
For each error mock in `specs/002-login-page/mocks/`:
1. In `python_bridge/auth.py`, temporarily return the mock fixture for the error case
2. Submit the form and verify the exact inline message appears

| Mock file                  | Expected inline message                                                           |
|----------------------------|-----------------------------------------------------------------------------------|
| `login-invalid-creds.json` | "Invalid email or password"                                                       |
| `login-not-confirmed.json` | "Please confirm your email address before logging in."                            |
| `login-locked.json`        | "Your account is temporarily locked. Please contact your administrator."          |
| `login-disabled.json`      | "Your account has been disabled. Please contact your administrator."              |
| `login-bridge-error.json`  | "Unable to reach the server. Please check your connection and try again."         |

### Session Restore
1. Log in with "Remember this device" checked
2. Close the app
3. Open Windows Credential Manager → verify `lumina-ai-proctoring` entries exist
4. Relaunch the app → verify it bypasses login and goes to exam-code
5. Manually delete keychain entries → relaunch → verify login page appears

---

## Key Files in This Spec

| File | Role |
|------|------|
| `python_bridge/auth.py` | New module — `POST /login` route + error mapping |
| `python_bridge/server.py` | Modified — imports and registers `auth.py` blueprint |
| `python_bridge/requirements.txt` | Modified — adds `requests>=2.32` |
| `frontend/main.js` | Modified — session check + 3 new `ipcMain.handle` calls |
| `frontend/preload.js` | Modified — 3 new `window.bridge` methods |
| `frontend/pages/login/index.html` | Replaced — full Ethereal Authority design |
| `frontend/pages/login/login.js` | New — form controller (validate, submit, error display) |
| `frontend/pages/login/login.css` | New — page-specific styles using design tokens only |

---

## Architecture Boundary Reminder

```
[Renderer: login.js]
  window.bridge.login({ email, password })
        ↓ (ipcRenderer.invoke)
[Main: main.js ipcMain.handle('bridge:login')]
  fetch('http://127.0.0.1:5050/login', POST)
        ↓ (HTTP to loopback)
[Python: auth.py POST /login]
  requests.post(baseUrl + '/api/Authuantication/login')
        ↓ (HTTPS to LMS)
[LMS API: POST /api/Authuantication/login]
```

**NEVER shortcut this chain.** The renderer must not call the bridge or LMS directly.

---

## Credential Security Checklist

Before considering this spec complete, verify:

- [ ] `password` value never appears in any `console.log`, `print()`, or error response
- [ ] Raw LMS `errorMessage` never reaches the renderer — only mapped static messages
- [ ] `localStorage.getItem('token')` returns nothing (no token in web storage)
- [ ] Windows Credential Manager shows entries only when "Remember this device" was checked
- [ ] Closing the app without "Remember this device" → relaunch → login page shown (not bypassed)
