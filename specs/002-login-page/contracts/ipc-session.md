# Contract: Bridge IPC — bridge:login, bridge:get-saved-session, bridge:clear-session

**IPC Channels**: `bridge:login`, `bridge:get-saved-session`, `bridge:clear-session`
**Consumer**: Renderer process (`frontend/pages/login/login.js`)
**Provider**: Main process (`frontend/main.js`) + Preload (`frontend/preload.js`)
**Spec**: `specs/002-login-page/spec.md` FR-005, FR-007, FR-008, FR-012
**Date**: 2026-04-15

---

## Purpose

This contract defines the `window.bridge` API surface added to `preload.js` for the login
feature. The renderer calls these methods; the main process handles them via `ipcMain.handle`.

---

## `window.bridge.login(credentials)`

### Preload exposure
```js
contextBridge.exposeInMainWorld('bridge', {
  // ... existing methods from spec 001 ...
  login: (creds) => ipcRenderer.invoke('bridge:login', creds),
})
```

### Input
```json
{ "email": "student@institution.edu", "password": "P@ssword123" }
```

### Output — Success
```json
{ "ok": true, "data": { /* full LoginResponse payload */ } }
```

### Output — Error
```json
{ "ok": false, "error": { "code": "INVALID_CREDENTIALS", "message": "Invalid email or password" } }
```

| Property      | Type    | Description                                            |
|---------------|---------|--------------------------------------------------------|
| `ok`          | boolean | `true` = login succeeded; `false` = login failed       |
| `data`        | object  | Present when `ok=true`; full `LoginResponse` payload   |
| `error`       | object  | Present when `ok=false`; `BridgeLoginError` `{code, message}` |

**Main process handler responsibilities**:
1. Forward to `POST /127.0.0.1:5050/login` via Node `fetch`
2. If bridge HTTP OK → return `{ok: true, data: response.json()}`
3. If bridge HTTP error → return `{ok: false, error: response.json()}`
4. If `fetch` throws (bridge down) → return `{ok: false, error: {code:'BRIDGE_ERROR', message:'...'}}`
5. After successful login: store session in keytar (if `rememberThis=true`) or memory (if `false`)

---

## `window.bridge.getSavedSession()`

Returns the stored session if valid, or `null` if none/expired.

### Preload exposure
```js
getSavedSession: () => ipcRenderer.invoke('bridge:get-saved-session'),
```

### Output — Valid session
```json
{
  "ok": true,
  "session": {
    "accessToken": "...",
    "refreshToken": "...",
    "tokenExpiry": "2026-04-15T11:00:00Z",
    "refreshExpiry": "2026-04-29T10:00:00Z",
    "userProfile": { "id": "...", "email": "...", "firstName": "...", "lastName": "...", "profilePictureUrl": null }
  }
}
```

### Output — No valid session
```json
{ "ok": false }
```

**Main process handler responsibilities**:
1. Check keytar for `remember-flag` = `"1"`
2. Check `refresh-expiry` is in the future
3. If valid → return `{ok: true, session: {...}}`
4. If expired or missing → clear all keytar keys → return `{ok: false}`
5. If keytar unavailable (native module error) → log to stderr → return `{ok: false}`

---

## `window.bridge.clearSession()`

Clears all stored session data from the keychain (used on logout or expiry).

### Preload exposure
```js
clearSession: () => ipcRenderer.invoke('bridge:clear-session'),
```

### Output
```json
{ "ok": true }
```

**Main process handler responsibilities**:
1. Call `keytar.deletePassword('lumina-ai-proctoring', key)` for all 6 keys
2. Clear the in-memory session object in `main.js`
3. Return `{ok: true}` always (idempotent — deleting a non-existent key is not an error)

---

## Security Constraints

- Credentials (`email`, `password`) MUST NOT be logged, stored to disk, or returned in any
  response from these IPC methods.
- The `password` field is consumed by the `bridge:login` handler and MUST NOT be forwarded
  to `bridge:get-saved-session` or `bridge:clear-session`.
- `window.bridge` properties are enumerated in `contextBridge.exposeInMainWorld` — no dynamic
  property access. No `window.bridge[userInput]` patterns are permitted.
