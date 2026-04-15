# Implementation Plan: Login Page

**Branch**: `002-login-page` | **Date**: 2026-04-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-login-page/spec.md`

## Summary

Implement the student login page for Lumina AI, delivering a pixel-faithful "Ethereal
Authority" design (matching `Designs/Login_Page/screen.png`) wired to a secure three-hop
authentication flow: renderer → IPC → Python bridge → LMS `POST /api/Authuantication/login`.
On success, JWT and refresh tokens are stored in the OS keychain via keytar. On subsequent
launches, the main process restores the session before the login UI loads, bypassing the page
for remembered users. Five typed error codes map LMS errors to sanitised inline messages with
no credential leakage.

## Technical Context

**Language/Version**: Node.js 20 LTS (Electron 33+) / Python 3.11+
**Primary Dependencies**: Electron 33, keytar 7.x, Flask 3.x, flask-cors 4.x, requests 2.32+, @fontsource/manrope, @fontsource/inter
**Storage**: OS keychain via keytar (JWT + refresh token + user profile); no database
**Testing**: Manual + mock JSON fixtures in `specs/002-login-page/mocks/`
**Target Platform**: Windows 10+ desktop application (Electron)
**Project Type**: desktop-app
**Performance Goals**: Login round-trip < 5 seconds on standard broadband
**Constraints**: All HTTP to LMS must go through Python bridge; no credentials in renderer; no web storage; keytar for persistence only when "Remember this device" is checked
**Scale/Scope**: Single-user desktop app; one login session at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. Spec-First | `spec.md` complete with 4 user stories, 16 FRs, 5 SCs | ✅ PASS |
| II. Architecture Boundary | All LMS HTTP goes through Python bridge; renderer uses IPC only (`window.bridge.login`); no direct fetch from renderer | ✅ PASS |
| III. Design System Fidelity | Login page uses only CSS custom properties from `design-tokens.css`; no hardcoded hex values; Manrope for headline, Inter for body; ghost borders on inputs; no 1px solid borders | ✅ PASS |
| IV. Security by Default | Tokens stored via keytar only; no localStorage/sessionStorage; raw LMS `errorMessage` never forwarded to renderer; password never logged | ✅ PASS |
| V. Independent Testability | 4 independent test scenarios defined; mock fixtures in `mocks/`; can be tested without live LMS | ✅ PASS |

**Post-Design Re-check**: All five principles pass after Phase 1 design.
- Principle II: Confirmed — `login.js` calls `window.bridge.login()` only; no `fetch()` to any URL.
- Principle IV: Confirmed — `auth.py` maps and sanitises LMS errors; `remember-flag` gates keytar writes.

## Project Structure

### Documentation (this feature)

```text
specs/002-login-page/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── login.md         # POST /login bridge endpoint contract
│   └── ipc-session.md   # IPC channel contract (bridge:login, bridge:get-saved-session, bridge:clear-session)
├── mocks/
│   ├── login-ok.json
│   ├── login-invalid-creds.json
│   ├── login-not-confirmed.json
│   ├── login-locked.json
│   ├── login-disabled.json
│   └── login-bridge-error.json
├── checklists/
│   └── requirements.md  # All 16 items pass
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
python_bridge/
├── auth.py              # NEW — POST /login route + error mapping
├── server.py            # MODIFIED — register auth blueprint
└── requirements.txt     # MODIFIED — add requests>=2.32

frontend/
├── main.js              # MODIFIED — session restore check + 3 ipcMain.handle
├── preload.js           # MODIFIED — 3 new window.bridge methods
└── pages/
    └── login/
        ├── index.html   # REPLACED — full Ethereal Authority login page
        ├── login.js     # NEW — form controller
        └── login.css    # NEW — page-specific styles (tokens only)
```

**Structure Decision**: Two-process desktop app (spec 001 structure extended). Python bridge
gains an `auth.py` module registered as a blueprint. Electron gains IPC handlers and keytar
session management in `main.js`. Login page replaces the spec 001 stub with full implementation.

## Implementation Phases

### Phase 1 — Python Bridge Auth Module

**Files**: `python_bridge/auth.py`, `python_bridge/server.py`, `python_bridge/requirements.txt`

1. Create `python_bridge/auth.py`:
   - Define `auth_bp = Blueprint('auth', __name__)`
   - Implement `POST /login` route:
     - Parse JSON body `{email, password}`
     - Validate non-empty (return `BRIDGE_ERROR` if blank)
     - Call `requests.post(app_config.base_url + '/api/Authuantication/login', json=body, timeout=15)`
     - On `200`: return LMS response as-is with `200 OK`
     - On non-200: call `map_lms_error(status_code, error_message)` → return mapped error with appropriate HTTP status
     - On `RequestException`: return `{code:'BRIDGE_ERROR', message:'...'}` with `503`
   - Implement `map_lms_error(status_code, error_message) -> dict` with case-insensitive matching

2. Modify `python_bridge/server.py`:
   - Import `auth_bp` from `auth.py`
   - Register blueprint: `app.register_blueprint(auth_bp)`

3. Modify `python_bridge/requirements.txt`:
   - Add `requests>=2.32`

### Phase 2 — Electron IPC & Session Management

**Files**: `frontend/main.js`, `frontend/preload.js`

4. Modify `frontend/main.js`:
   - Add `ipcMain.handle('bridge:login', ...)` handler:
     - Forward to `POST http://127.0.0.1:{port}/login`
     - On bridge `200` → call `storeSession(data, rememberThis)` → return `{ok:true, data}`
     - On bridge error → return `{ok:false, error: parsedError}`
     - On `fetch` throw → return `{ok:false, error:{code:'BRIDGE_ERROR', ...}}`
   - Add `ipcMain.handle('bridge:get-saved-session', ...)` handler:
     - Call `getSavedSession()` → return `{ok:true, session}` or `{ok:false}`
   - Add `ipcMain.handle('bridge:clear-session', ...)` handler:
     - Delete all 6 keytar keys → clear in-memory session → return `{ok:true}`
   - Add `getSavedSession()` function (see research.md Task 2)
   - Add `storeSession(data, remember)` function: writes 6 keytar keys if `remember=true`,
     stores object in-memory only if `false`
   - Add `clearAllKeytarEntries()` helper
   - Modify `app.whenReady()` sequence: after `pollBridgeReady`, call `getSavedSession()`;
     if valid session → `mainWindow.loadFile(exam-code/index.html)` → return early

5. Modify `frontend/preload.js`:
   - Add to `contextBridge.exposeInMainWorld('bridge', {...})`:
     - `login: (creds) => ipcRenderer.invoke('bridge:login', creds)`
     - `getSavedSession: () => ipcRenderer.invoke('bridge:get-saved-session')`
     - `clearSession: () => ipcRenderer.invoke('bridge:clear-session')`
   - Add `'bridge:login'`, `'bridge:get-saved-session'`, `'bridge:clear-session'` to the
     allowed `validInvokeChannels` whitelist

### Phase 3 — Login Page UI

**Files**: `frontend/pages/login/index.html`, `frontend/pages/login/login.js`, `frontend/pages/login/login.css`

6. Create `frontend/pages/login/login.css`:
   - Page background: gradient from `--color-surface` to `--color-surface-container-low`
   - Navigation bar: flex row, `--color-surface`, Lumina wordmark left, icon buttons right
   - Card: `--color-surface-container-lowest`, `--radius-xl`, `--shadow-ambient`, centered
   - Shield icon: SVG in `--color-primary`
   - Headline: `headline-md` size (1.75rem), Manrope 700, `--color-on-surface`
   - Subtitle: Inter 400, `--color-on-surface-variant`
   - Input labels: Inter, 0.75rem, ALL CAPS, 0.05em tracking, `--color-on-surface-variant`
   - Input fields: `.input-field` from `components.css` (no extra rules needed beyond tokens)
   - Forgot password link: Inter, `--color-primary`
   - Remember checkbox: styled checkbox with `--color-primary` accent
   - LOGIN button: `.btn.btn-primary` full-width
   - Error message: `--color-error`, Inter 0.875rem
   - Progress pills: 3 pills, pill 1 active (`--color-primary`), pills 2-3 `--color-outline-variant`
   - FAB: circular, `--color-primary`, fixed bottom-right
   - Footer: Inter 0.75rem, `--color-on-surface-variant`

7. Replace `frontend/pages/login/index.html`:
   - Full HTML matching `Designs/Login_Page/screen.png`
   - Links `design-tokens.css`, `components.css`, `login.css`
   - Scripts: `login.js` as module
   - All interactive elements have `id` attributes for `login.js` to bind

8. Create `frontend/pages/login/login.js`:
   - Bind references: email input, password input, remember checkbox, login button,
     error paragraph, spinner
   - `submitForm()`:
     1. Read email + password values
     2. Client-side validate: non-empty + email format → show inline error if invalid
     3. Enter LOADING state: disable form + button, show spinner, clear error
     4. `const result = await window.bridge.login({email, password})`
     5. On `result.ok`: `window.location.href = '../exam-code/index.html'`
     6. On `!result.ok`: exit LOADING state, show `ERROR_MESSAGES[result.error.code]`
   - `forgotPasswordClick()`: `window.bridge.openExternal(forgotPasswordUrl)` if configured
   - `form.addEventListener('submit', ...)` + `password.addEventListener('keydown', Enter)` +
     `email.addEventListener('keydown', Enter)`
   - `const ERROR_MESSAGES = { INVALID_CREDENTIALS: '...', EMAIL_NOT_CONFIRMED: '...', ... }` map

### Phase 4 — Bridge `openExternal` IPC

**Files**: `frontend/main.js`, `frontend/preload.js`

9. Modify `frontend/main.js`:
   - Add `ipcMain.handle('bridge:open-external', async (_event, url) => shell.openExternal(url))`
   - Validate URL is `https://` before calling `shell.openExternal`

10. Modify `frontend/preload.js`:
    - Add `openExternal: (url) => ipcRenderer.invoke('bridge:open-external', url)` to `window.bridge`

### Phase 5 — Verification & Mocks

11. Verify all 5 acceptance scenarios from US2 and US3 pass using mock fixtures
12. Verify login page renders at 1280×800 matching `Designs/Login_Page/screen.png`
13. Verify zero credential leakage (console.log audit)

## Complexity Tracking

No Constitution violations. No complexity justification required.

