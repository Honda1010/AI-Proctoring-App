---
description: "Task list for 002-login-page — Student Login & Session Management"
---

# Tasks: Login Page — Student Login & Session Management

**Input**: Design documents from `specs/002-login-page/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: No automated test tasks (not requested in spec). Verification is by manual inspection
per the Independent Test criteria defined in each user story, using mock JSON fixtures in
`specs/002-login-page/mocks/`.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the `requests` dependency that the Python bridge needs to make outbound HTTP
calls to the LMS. No user story work can begin on the Python side until this is in place.

- [x] T001 Add `requests>=2.32` to `python_bridge/requirements.txt` (append below existing flask-cors line)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Flask Blueprint scaffold for the auth module and blueprint registration in the
server. Every user story that touches `python_bridge/auth.py` (US2, US3) depends on this
structure existing first.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Create `python_bridge/auth.py` — define `auth_bp = Blueprint('auth', __name__)`; add stub `POST /login` route that returns `{"code": "BRIDGE_ERROR", "message": "not implemented"}` with 503; add a placeholder `map_lms_error(status_code, error_message)` function that returns `{"code": "BRIDGE_ERROR", "message": "Unknown error"}` (to be completed in US3 phase)
- [x] T003 Modify `python_bridge/server.py` — import `auth_bp` from `auth`; call `app.register_blueprint(auth_bp)` after the Flask app and CORS setup; no other changes

**Checkpoint**: Flask bridge now registers the `/login` route (returns stub 503). Structure is in place for user story phases.

---

## Phase 3: User Story 1 — Login Form Renders (Priority: P1) 🎯 MVP

**Goal**: The login page renders with a pixel-faithful "Ethereal Authority" design matching
`Designs/Login_Page/screen.png` — shield icon card, email/password inputs, "Remember this
device" checkbox, LOGIN button, progress pills, FAB, nav bar, and footer — all using CSS
custom properties only, zero hardcoded hex values.

**Independent Test**: Open `frontend/pages/login/index.html` directly in a browser (no
Electron, no network required). Verify the design visually matches
`Designs/Login_Page/screen.png` at 1280×800.

- [x] T004 [P] [US1] Create `frontend/pages/login/login.css` — page background gradient (`--color-surface` to `--color-surface-container-low`); top nav bar (flex, `--color-surface`, Lumina wordmark left, "Login" label + ? + ⓘ icon buttons right); centered login card (`--color-surface-container-lowest`, `--radius-xl`, `--shadow-ambient`, padding `2rem`); shield SVG icon in `--color-primary`; headline 1.75rem Manrope 700 `--color-on-surface`; subtitle Inter 400 `--color-on-surface-variant`; input labels Inter 0.75rem ALL-CAPS 0.05em tracking `--color-on-surface-variant`; "Forgot password?" link `--color-primary`; "Remember this device" checkbox accent `--color-primary`; LOGIN button full-width using `.btn.btn-primary`; single error `<p>` styled with `--color-error` Inter 0.875rem; 3 progress pills at card bottom (active: `--color-primary`, inactive: `--color-outline-variant` 40% opacity); circular FAB fixed bottom-right `--color-primary`; footer Inter 0.75rem `--color-on-surface-variant` — NO hardcoded hex values anywhere in this file
- [x] T005 [US1] Replace `frontend/pages/login/index.html` with the full Ethereal Authority login page — `<link>` to `../../assets/design-tokens.css`, `../../assets/components.css`, `./login.css`; top `<nav>` with Lumina wordmark and icon buttons; centered `<main>` with login card containing: shield inline SVG, `<h1>Welcome Back</h1>`, `<p>The Digital Sanctuary of Integrity</p>`, `<form id="login-form">` with field `#email-input` (type email, placeholder "name@institution.edu"), field `#password-input` (type password), `<a id="forgot-link">Forgot password?</a>`, `<label><input type="checkbox" id="remember-checkbox" unchecked> Remember this device</label>`, `<button id="login-btn" type="submit">LOGIN →</button>` with a `<span class="spinner" id="login-spinner" hidden></span>` inside, `<p class="form-error" id="login-error" aria-live="polite"></p>`; 3 `<div class="progress-pill">` elements (first has `active` class); floating `<button id="fab-info">ⓘ</button>`; footer with copyright left and policy links right; `<script type="module" src="./login.js"></script>` at end of body

**Checkpoint**: US1 independently testable — open `index.html` in browser, confirm all elements present and design matches `Designs/Login_Page/screen.png`. No JavaScript execution required.

---

## Phase 4: User Story 2 — Submit Flow & Authentication (Priority: P1)

**Goal**: Student fills form → IPC call to main process → Python bridge proxies `POST
/api/Authuantication/login` → on 200: tokens stored in keytar (if "Remember" checked) or
in-memory (if not) → app navigates to exam-code page. Client-side validation blocks blank or
malformed email before any IPC call.

**Independent Test**: Temporarily patch `python_bridge/auth.py` `POST /login` to return
`specs/002-login-page/mocks/login-ok.json` directly. Run `npm start`, enter any credentials,
click LOGIN, verify navigation to exam-code page and Windows Credential Manager entries (when
"Remember this device" is checked).

- [x] T006 [P] [US2] Implement `POST /login` route body in `python_bridge/auth.py` — replace the 503 stub: read JSON body `{email, password}`; if either is blank/missing return `{"code":"BRIDGE_ERROR","message":"..."}` with 400; call `requests.post(app_config.base_url + '/api/Authuantication/login', json={"email": email, "password": password}, timeout=15)`; on `response.status_code == 200` return `jsonify(response.json()), 200`; on non-200 call `map_lms_error(response.status_code, response.json().get('errorMessage',''))` and return `jsonify(result), response.status_code`; on `requests.exceptions.RequestException` return `jsonify(map_lms_error(0, '')), 503`; password MUST NOT appear in any `print()` or log call
- [x] T007 [P] [US2] Add session helper functions to `frontend/main.js` — `async function storeSession(data, remember)`: if `remember=true` write 6 keytar entries (`access-token`=data.token, `refresh-token`=data.refreshToken, `token-expiry`=computed ISO string, `refresh-expiry`=data.refreshTokenExpiration, `user-profile`=JSON.stringify({id,email,firstName,lastName,profilePictureUrl}), `remember-flag`='1') via `keytar.setPassword('lumina-ai-proctoring', key, value)`, else store `{...}` in module-scope `let sessionMemory` variable only; `async function clearAllKeytarEntries()`: call `keytar.deletePassword('lumina-ai-proctoring', key)` for all 6 keys; wrap both in try/catch that logs to stderr but never throws
- [x] T008 [US2] Add `ipcMain.handle('bridge:login', async (_event, {email, password, remember}) => {...})` to `frontend/main.js` — inside handler: `fetch('http://127.0.0.1:${port}/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email, password})})` using Electron's `net.fetch` or Node global `fetch`; if `response.ok` read JSON, call `await storeSession(data, remember)`, return `{ok:true, data}`; if `!response.ok` read JSON, return `{ok:false, error: parsed}`; catch any throw and return `{ok:false, error:{code:'BRIDGE_ERROR', message:'Unable to reach the server. Please check your connection and try again.'}}`
- [x] T009 [US2] Modify `frontend/preload.js` — add four new methods to the `contextBridge.exposeInMainWorld('bridge', {...})` object: `login: (creds) => ipcRenderer.invoke('bridge:login', creds)`, `getSavedSession: () => ipcRenderer.invoke('bridge:get-saved-session')`, `clearSession: () => ipcRenderer.invoke('bridge:clear-session')`, `openExternal: (url) => ipcRenderer.invoke('bridge:open-external', url)`; add `'bridge:login'`, `'bridge:get-saved-session'`, `'bridge:clear-session'`, `'bridge:open-external'` to the `validInvokeChannels` whitelist array
- [x] T010 [US2] Create `frontend/pages/login/login.js` as an ES module — query DOM: `#email-input`, `#password-input`, `#remember-checkbox`, `#login-btn`, `#login-spinner`, `#login-error`, `#forgot-link`; define `const ERROR_MESSAGES = {INVALID_CREDENTIALS:'Invalid email or password', EMAIL_NOT_CONFIRMED:'Please confirm your email address before logging in.', LOCKED_OUT:'Your account is temporarily locked. Please contact your administrator.', ACCOUNT_DISABLED:'Your account has been disabled. Please contact your administrator.', BRIDGE_ERROR:'Unable to reach the server. Please check your connection and try again.'}`; define `function showError(msg)` sets `#login-error textContent`; `function clearError()` sets it to `''`; define `async function submitForm(e)`: `e.preventDefault()`; `const email = emailInput.value.trim()`, `const password = passwordInput.value`; client validate: if blank show "Please enter your email address", if no `@` or no `.` after `@` show "Please enter a valid email address", if password blank show "Please enter your password", return on any error without IPC call; enter LOADING state: `loginBtn.disabled=true`, `loginBtn.classList.add('loading')`, show spinner, `clearError()`; `const result = await window.bridge.login({email, password, remember: rememberCheckbox.checked})`; exit LOADING state always (re-enable btn, hide spinner); if `result.ok`: `window.location.href = '../exam-code/index.html'`; else `showError(ERROR_MESSAGES[result.error?.code] ?? ERROR_MESSAGES.BRIDGE_ERROR)`; register `loginForm.addEventListener('submit', submitForm)`; register Enter key on both inputs calling `loginForm.requestSubmit()`; register `forgotLink.addEventListener('click', e => { e.preventDefault(); window.bridge.openExternal('') })` (no-op for unconfigured URL)

**Checkpoint**: US2 independently testable — mock bridge returning `login-ok.json`, verify:
1. Spinner appears on click, 2. Navigation to exam-code page on success, 3. keytar entries appear
in Windows Credential Manager when "Remember" is checked, 4. No keytar entries when unchecked.

---

## Phase 5: User Story 3 — Error Mapping & Display (Priority: P2)

**Goal**: Each of the 5 typed LMS error conditions shows a distinct, sanitised inline message
below the password field. No raw LMS `errorMessage` text, email addresses, or tokens reach
the renderer.

**Independent Test**: Temporarily patch `python_bridge/auth.py` to return each error mock
fixture in turn (`login-invalid-creds.json`, `login-not-confirmed.json`, `login-locked.json`,
`login-disabled.json`, `login-bridge-error.json`). Verify the exact inline message appears
and the console shows no credential data.

- [x] T011 [P] [US3] Complete `map_lms_error()` in `python_bridge/auth.py` — replace the placeholder body with case-insensitive matching on `error_message.lower()`: if `"invalid email/password"` in msg → `{"code":"INVALID_CREDENTIALS","message":"Invalid email or password"}`; elif `"is not confirmed"` in msg → `{"code":"EMAIL_NOT_CONFIRMED","message":"Please confirm your email address before logging in."}`; elif `"is locked out"` in msg → `{"code":"LOCKED_OUT","message":"Your account is temporarily locked. Please contact your administrator."}`; elif `"is disabled"` in msg → `{"code":"ACCOUNT_DISABLED","message":"Your account has been disabled. Please contact your administrator."}`; else → `{"code":"BRIDGE_ERROR","message":"Unable to reach the server. Please check your connection and try again."}`; the raw `error_message` parameter MUST NOT appear anywhere in the returned dict values
- [x] T012 [P] [US3] Verify error display wiring in `frontend/pages/login/login.js` — confirm `ERROR_MESSAGES` constant and `showError()` reference `#login-error` by `id`; the element uses `aria-live="polite"` (already in index.html from T005); confirm `#login-error` is positioned below `#password-input` in the DOM; no email address or raw error string is ever passed to `showError()` — only `ERROR_MESSAGES[code]` lookup values

**Checkpoint**: US3 independently testable — inject all 5 error mock fixtures one at a time,
verify each produces exactly the correct inline string and that `console.log` contains no
student email, password, or raw LMS `errorMessage`.

---

## Phase 6: User Story 4 — Session Restore on Relaunch (Priority: P2)

**Goal**: On app relaunch, if a valid (non-expired) saved session exists in the keychain,
`main.js` skips the login page and routes directly to the exam-code page. If the session is
absent, expired, or corrupt, it is cleared and the login page is shown normally.

**Independent Test**: Use Windows Credential Manager to manually set `lumina-ai-proctoring`
`remember-flag`=`"1"` and `refresh-expiry`= a future ISO date. Verify the app routes to
exam-code on launch. Delete the entries; verify login page is shown.

- [x] T013 [P] [US4] Add `async function getSavedSession()` to `frontend/main.js` — `const keytar = require('keytar')`; `const SVC = 'lumina-ai-proctoring'`; try/catch wrapping the entire function (on any native error: log to stderr, return null); `const flag = await keytar.getPassword(SVC, 'remember-flag')`; if `flag !== '1'` return null; `const refreshExpiry = await keytar.getPassword(SVC, 'refresh-expiry')`; if `!refreshExpiry || new Date(refreshExpiry) <= new Date()` call `await clearAllKeytarEntries()` and return null; read `access-token`, `refresh-token`, `token-expiry`, `user-profile`; parse `user-profile` with try/catch (on JSON.parse error: call `clearAllKeytarEntries()`, return null); return `{accessToken, refreshToken, tokenExpiry, refreshExpiry, userProfile}`
- [x] T014 [US4] Add two IPC handlers to `frontend/main.js` — `ipcMain.handle('bridge:get-saved-session', async () => { const s = await getSavedSession(); return s ? {ok:true, session:s} : {ok:false} })`; `ipcMain.handle('bridge:clear-session', async () => { await clearAllKeytarEntries(); sessionMemory = null; return {ok:true} })`
- [x] T015 [US4] Modify the `app.whenReady()` sequence in `frontend/main.js` — after `pollBridgeReady()` returns true and before loading the login page: `const saved = await getSavedSession()`; if `saved !== null` call `mainWindow.loadFile(path.join(__dirname, 'pages/exam-code/index.html'))` and return early from the ready handler; otherwise continue to `mainWindow.loadFile(path.join(__dirname, 'pages/login/index.html'))` as before

**Checkpoint**: US4 independently testable — manipulate Windows Credential Manager entries
and verify routing: valid remember-flag + future refresh-expiry → exam-code page; missing or
expired entries → login page; corrupt user-profile JSON → login page (no crash).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: "Forgot password?" safe browser open, final security audit, visual verification.

- [x] T016 [P] Add `ipcMain.handle('bridge:open-external', async (_event, url) => { if (typeof url === 'string' && url.startsWith('https://')) { await shell.openExternal(url) } })` to `frontend/main.js`; import `shell` from `'electron'` at the top of the file (add to existing destructure if already imported); URLs that do not start with `https://` are silently ignored — this prevents open-redirect abuse
- [x] T017 [P] Visual verification: run `npm start`, confirm login page renders at 1280×800 matching `Designs/Login_Page/screen.png` — check card border-radius, headline typeface (Manrope), input ghost-border style, LOGIN gradient button, 3 progress pills (first active), FAB bottom-right, footer links; open DevTools and confirm zero hardcoded hex values exist in `login.css` or `index.html` style attributes
- [x] T018 Security audit: inspect all modified/created files (`python_bridge/auth.py`, `frontend/main.js`, `frontend/pages/login/login.js`) and confirm: (a) password value is never passed to `console.log`, `print()`, Flask logger, or any error response; (b) JWT token strings are never passed to `console.log`; (c) raw LMS `errorMessage` strings are never forwarded to the renderer; (d) `localStorage`/`sessionStorage` are never written with credential data; record any violation found and fix it before marking complete

---

## Dependencies

```
T001 (requirements.txt)
  └─ T002 (auth.py scaffold)
       └─ T003 (server.py blueprint registration)
            ├─ T006 [US2] (POST /login implementation)
            │    └─ T011 [US3] (map_lms_error complete)
            └─ (unblocked)

T004 [US1] (login.css)         — parallel with T006, T007
  └─ T005 [US1] (index.html)
       └─ T010 [US2] (login.js form controller)
            └─ T012 [US3] (error display verify)

T007 [US2] (storeSession helper)  — parallel with T004, T006
  └─ T008 [US2] (ipcMain handle bridge:login)

T009 [US2] (preload.js methods)   — parallel with T008
  └─ T010 [US2] (login.js form controller — needs window.bridge.login)

T013 [US4] (getSavedSession fn)   — parallel with T011, T012
  └─ T014 [US4] (ipcMain handles get-saved-session + clear-session)
       └─ T015 [US4] (app.whenReady session restore check)

T015 → T016 → T017 → T018 (polish, sequential)
```

## Parallel Execution Examples

**During Phase 3 + Phase 4 start**:
- Agent A: T004 (login.css) → T005 (index.html)
- Agent B: T006 (auth.py POST /login) → T007 (storeSession helper) in parallel with A

**During Phase 5 + Phase 6 start**:
- Agent A: T011 (map_lms_error)
- Agent B: T012 (error display verify)
- Agent C: T013 (getSavedSession fn) — all three in parallel

## Implementation Strategy (MVP First)

1. **MVP** (US1 + US2 — P1 stories only): T001 → T002 → T003 → T004+T006+T007 (parallel) → T005 → T008 → T009 → T010
   — Delivers: login page renders + happy-path authentication + token storage + exam-code navigation.
   — Independently testable without live LMS using `login-ok.json` mock.

2. **Error handling** (US3 — P2): T011 → T012
   — Delivers: all 5 typed error messages correctly displayed.

3. **Session restore** (US4 — P2): T013 → T014 → T015
   — Delivers: remembered sessions bypass login on relaunch.

4. **Polish** (cross-cutting): T016 → T017 → T018
   — Delivers: safe external link open, visual match confirmed, credential leak audit passed.
