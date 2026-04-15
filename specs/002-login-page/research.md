# Research: Login Page — Authentication Flow & Session Management

**Branch**: `002-login-page` | **Date**: 2026-04-15
**Input**: Unknowns extracted from Technical Context in plan.md

---

## Research Task 1 — IPC Pattern: Electron ↔ Python Bridge for Login

**Question**: What is the cleanest pattern for sending login credentials from the Electron
renderer to the Python bridge and receiving a typed success/error response?

### Decision
Use a **two-hop IPC** pattern:
1. Renderer → `ipcRenderer.invoke('bridge:login', {email, password})` → Main process
2. Main process → `fetch('http://127.0.0.1:5050/login', {method:'POST', body: JSON.stringify(...)})` → Python bridge
3. Python bridge → `requests.post(baseUrl + '/api/Authuantication/login', ...)` → LMS

The main process returns either `{ok: true, data: {...}}` or `{ok: false, error: {code, message}}` to the renderer.

### Rationale
- Keeps the renderer strictly without direct HTTP access (Constitution Principle II)
- `ipcMain.handle` / `ipcRenderer.invoke` is the idiomatic Electron 20+ two-way IPC pattern
- Credentials leave the renderer process only once, inside one structured payload
- The main process can apply `contextIsolation: true` + `sandbox: true` so the renderer cannot
  reach `net` or `fetch` directly
- Python bridge remains the single source of truth for LMS communication

### Pattern: Renderer Side
```js
// login/login.js
async function submitLogin(email, password) {
  const result = await window.bridge.login({ email, password })
  if (result.ok) { /* navigate */ }
  else { showError(result.error.code) }
}
```

### Pattern: Preload
```js
contextBridge.exposeInMainWorld('bridge', {
  login: (creds) => ipcRenderer.invoke('bridge:login', creds),
  getSavedSession: () => ipcRenderer.invoke('bridge:get-saved-session'),
  clearSession: () => ipcRenderer.invoke('bridge:clear-session'),
})
```

### Pattern: Main Process
```js
ipcMain.handle('bridge:login', async (_event, { email, password }) => {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (res.ok) return { ok: true, data: await res.json() }
    const err = await res.json()
    return { ok: false, error: err }
  } catch (e) {
    return { ok: false, error: { code: 'BRIDGE_ERROR', message: 'bridge unreachable' } }
  }
})
```

### Alternatives Considered
- **Renderer direct fetch to Python bridge**: Rejected — violates Constitution Principle II
  (renderer MUST NOT make HTTP calls to LMS or bridge endpoints directly).
- **stdin/stdout piping**: Rejected — Constitution Principle II explicitly forbids it.
- **WebSocket**: Rejected — overkill for a single-request login; HTTP POST is sufficient.

---

## Research Task 2 — Secure Session Storage with keytar

**Question**: How should JWT access tokens, refresh tokens, expiry metadata, and user profile
be stored in the OS keychain via keytar, and how should they be read back reliably?

### Decision
Use a **single keytar service name** (`lumina-ai-proctoring`) with **six distinct account
keys** per session entry. Store user profile as a JSON-serialised string.

### Rationale
- keytar stores one credential per (service, account) pair — multiple keys under one service
  is idiomatic
- Serialising user profile to JSON avoids binary encoding issues
- A single service name keeps credential manager UI tidy for the user
- Separating `token-expiry` and `refresh-expiry` as ISO strings avoids integer overflow in
  32-bit environments and is human-readable in credential managers

### Storage Schema
| keytar account key     | Value type      | Contents                                  |
|------------------------|-----------------|-------------------------------------------|
| `access-token`         | string          | JWT bearer token (3600s TTL)              |
| `refresh-token`        | string          | Refresh token (14-day TTL)                |
| `token-expiry`         | ISO UTC string  | `new Date(Date.now() + expinresIn*1000)`  |
| `refresh-expiry`       | ISO UTC string  | `refreshTokenExpiration` from LMS         |
| `user-profile`         | JSON string     | `{id, email, firstName, lastName, profilePictureUrl}` |
| `remember-flag`        | string `"1"`    | Presence signals "remember this device"   |

### Session Check Algorithm (main.js, before loading login page)
```js
async function getSavedSession() {
  const keytar = require('keytar')
  const SVC = 'lumina-ai-proctoring'
  const rememberFlag = await keytar.getPassword(SVC, 'remember-flag')
  if (rememberFlag !== '1') return null

  const refreshExpiry = await keytar.getPassword(SVC, 'refresh-expiry')
  if (!refreshExpiry || new Date(refreshExpiry) <= new Date()) {
    await clearAllKeytarEntries()
    return null
  }
  const accessToken  = await keytar.getPassword(SVC, 'access-token')
  const refreshToken = await keytar.getPassword(SVC, 'refresh-token')
  const tokenExpiry  = await keytar.getPassword(SVC, 'token-expiry')
  let   userProfile  = null
  try { userProfile = JSON.parse(await keytar.getPassword(SVC, 'user-profile')) } catch (_) {}
  return { accessToken, refreshToken, tokenExpiry, refreshExpiry, userProfile }
}
```

### Rationale for storing `remember-flag` separately
- Allows quick "does user want persistence?" check without reading all keys
- Makes logout trivial: delete only `remember-flag` to invalidate session check

### Alternatives Considered
- **localStorage / sessionStorage**: Rejected — Constitution Principle IV explicitly forbids it.
- **Single JSON blob in one keytar entry**: Rejected — harder to clear individual fields,
  and some OS keychains have payload size limits (~2 KB on macOS Keychain).
- **Electron's `safeStorage`**: Rejected — encrypts to file, not OS keychain; different threat
  model than keytar. Constitution mandates keytar specifically.

---

## Research Task 3 — Python Bridge Login Endpoint Design

**Question**: How should `python_bridge/server.py` implement `POST /login` to proxy the LMS
login call, translate errors, and return a structured typed response?

### Decision
Add a `POST /login` endpoint that:
1. Accepts `{email, password}` JSON body
2. Calls `requests.post(app_config.base_url + '/api/Authuantication/login', json=body, timeout=15)`
3. On 200: returns the full LMS payload as-is with `200 OK`
4. On 4xx/5xx: parses `errorMessage` from the LMS envelope and maps to a typed error code
5. On `requests.exceptions.RequestException`: returns `{code: "BRIDGE_ERROR", message: "network error"}`

### Error Mapping Table
| LMS HTTP | `errorMessage` substring        | Bridge `code`        |
|----------|---------------------------------|----------------------|
| 401      | `"Invalid Email/password"`      | `INVALID_CREDENTIALS` |
| 401      | `"is not confirmed"`            | `EMAIL_NOT_CONFIRMED` |
| 401      | `"is locked out"`               | `LOCKED_OUT`          |
| 500      | `"is disabled"`                 | `ACCOUNT_DISABLED`    |
| any      | *(network/unexpected)*          | `BRIDGE_ERROR`        |

### Bridge Response Shapes
**Success (200):**
```json
{
  "id": "...", "email": "...", "firstName": "...", "lastName": "...",
  "profilePictureUrl": "...", "token": "...", "expinresIn": 3600,
  "refreshToken": "...", "refreshTokenExpiration": "2026-04-29T..."
}
```
**Error (non-200):**
```json
{ "code": "INVALID_CREDENTIALS", "message": "Invalid email or password" }
```

### Sanitisation Rule
The raw `errorMessage` from the LMS MUST NOT be forwarded directly. Strip all email
addresses and student-identifiable information before mapping. Only the mapped `code` and
a static safe `message` string reach the main process.

### Alternatives Considered
- **Forward raw LMS JSON unchanged**: Rejected — Constitution Security Requirements and FR-011
  forbid surfacing raw LMS error messages with email addresses.
- **Flask abort() with HTTP error codes**: Rejected — would require the Electron side to
  read HTTP status codes instead of a typed `code` field; less robust to bridge restarts.

---

## Research Task 4 — Client-Side Form Validation Strategy

**Question**: What is the right balance between client-side validation pre-submit and
bridge-side validation, and how should inline error messages be managed in the DOM?

### Decision
**Two-layer validation:**
1. **Client-side (renderer, before IPC call)**: Format checks only — email contains "@" and
   at least one "." after "@"; password is non-empty. Show inline errors immediately without
   any IPC round-trip.
2. **Bridge-side (Python)**: Non-empty email and password check before forwarding to LMS.
   Returns `BRIDGE_ERROR` if either is missing (defence-in-depth; the renderer should never
   allow a blank submission through).

### Inline Error DOM Pattern
The renderer uses a *single* `<p class="form-error" aria-live="polite" id="login-error"></p>`
element positioned below the password field. On error: `element.textContent = safeMessage`;
on success/load: `element.textContent = ''`. This prevents layout shift from adding/removing
elements.

### No Password Complexity Validation
FR-003 explicitly states password complexity is NOT validated client-side. Only non-empty
check is performed. The LMS is authoritative for complexity requirements.

### Alternatives Considered
- **HTML5 `required` + `type="email"`**: Partially adopted — `type="email"` is used for
  progressive enhancement, but custom JS validation runs in parallel to control the exact
  error message text (the browser's built-in bubble cannot be styled to match the design).
- **Validate on blur**: Rejected for password field — disrupts UX during copy-paste.
  Validation triggers only on the submit action.

---

## Research Task 5 — Session Restore: Check Before or After Page Load?

**Question**: Should the main process check for a saved session before loading the login
HTML page, or after the page is visible?

### Decision
**Before loading the login page.** The main process runs `getSavedSession()` immediately after
the bridge is healthy (i.e., after `pollBridgeReady` returns true), and routes to exam-code
directly if a valid session exists. The login page HTML is never loaded in this case.

### Rationale
- Avoids a flash of the login form before redirect (FOUC-like issue)
- Simpler renderer logic: the login page never needs to check for a saved session itself
- The main process already owns the routing logic (`loadFile`) — session gating belongs there
- If the session check itself throws (e.g., keytar unavailable), falls back gracefully to
  showing the login page

### Keytar Unavailability Handling
If `require('keytar')` throws (e.g., native module rebuild needed), catch the error, log to
stderr, and show the login page normally. Do NOT crash the app — keytar is a convenience
feature, not a hard dependency for first-time login.

### Alternatives Considered
- **Renderer-side session check via IPC after page load**: Rejected — causes visible flash
  of login UI before navigation. Inconsistent with the "pre-load routing" pattern established
  in spec 001 (loading page → route decision before any user-facing page is shown).
- **Dedicated splash/redirect page**: Rejected — unnecessary extra page; main.js already
  handles routing after the loading screen.
