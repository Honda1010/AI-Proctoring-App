# Data Model: Login Page

**Branch**: `002-login-page` | **Date**: 2026-04-15
**Input**: entities from `spec.md` + research decisions in `research.md`

---

## Entities

### 1. LoginRequest

Credentials submitted by the student from the renderer to the main process via IPC,
then forwarded by the main process to the Python bridge.

| Field      | Type     | Constraints                                              |
|------------|----------|----------------------------------------------------------|
| `email`    | `string` | Non-empty; must contain `@` and at least one `.` after `@` |
| `password` | `string` | Non-empty; no complexity validation client-side          |

**Validation layers**:
- Layer 1 (renderer, pre-IPC): format check + empty check; shows inline error, blocks IPC call
- Layer 2 (Python bridge, pre-LMS): empty check only; returns `BRIDGE_ERROR` if blank
- Layer 3 (LMS): authoritative password and identity validation

---

### 2. LoginResponse

Success payload returned by the LMS `POST /api/Authuantication/login` endpoint, relayed
through the Python bridge and IPC to the main process.

| Field                    | Type            | Notes                                               |
|--------------------------|-----------------|-----------------------------------------------------|
| `id`                     | `string`        | Student's unique user ID (UUID)                     |
| `email`                  | `string`        | Student's institutional email address               |
| `firstName`              | `string`        | Student's first name                                |
| `lastName`               | `string`        | Student's last name                                 |
| `profilePictureUrl`      | `string \| null` | CDN URL; may be `null` — all consumers must guard   |
| `token`                  | `string`        | JWT access token                                    |
| `expinresIn`             | `number`        | Access token TTL in seconds (3600 = 1 hour)         |
| `refreshToken`           | `string`        | Refresh token for silent re-authentication          |
| `refreshTokenExpiration` | `string`        | ISO 8601 UTC datetime; 14-day TTL from login        |

**Computed fields** (derived in main.js, not stored from LMS directly):

| Computed key    | Derivation                                          |
|-----------------|-----------------------------------------------------|
| `token-expiry`  | `new Date(Date.now() + expinresIn * 1000).toISOString()` |
| `refresh-expiry`| `refreshTokenExpiration` (direct copy as ISO string) |

---

### 3. StoredSession

Persisted authentication state in the OS keychain via `keytar`. This is the authoritative
session store. The renderer never reads keytar directly — only via IPC through the main process.

**keytar service name**: `lumina-ai-proctoring`

| keytar account key  | Value type   | Description                                                       |
|---------------------|--------------|-------------------------------------------------------------------|
| `access-token`      | string       | JWT access token                                                  |
| `refresh-token`     | string       | Refresh token                                                     |
| `token-expiry`      | ISO string   | UTC datetime when access token expires                            |
| `refresh-expiry`    | ISO string   | UTC datetime when refresh token expires (drives session restore)  |
| `user-profile`      | JSON string  | `{id, email, firstName, lastName, profilePictureUrl}` serialised  |
| `remember-flag`     | `"1"`        | Present and equal to `"1"` only when "Remember this device" was checked |

**Session lifecycle**:
```
Remember=true  → store all 6 keys → persist across restarts
Remember=false → store in-memory only (JS object in main.js scope) → cleared on app quit
Logout         → delete all 6 keytar entries
Expired        → detected in getSavedSession() → delete all 6 + show login
Corrupt        → JSON.parse failure on user-profile → delete all 6 + show login
```

**Session restore check sequence** (main.js, after bridge is healthy):
1. `keytar.getPassword('lumina-ai-proctoring', 'remember-flag')` → must equal `"1"`
2. `keytar.getPassword('lumina-ai-proctoring', 'refresh-expiry')` → must be in the future
3. Read all remaining 4 keys → build `StoredSession` object
4. Return session → main.js routes to exam-code page

---

### 4. BridgeLoginError

Typed error object returned by the Python bridge (and forwarded by the main process
to the renderer) when login fails. Replaces raw LMS error envelopes.

| Field     | Type     | Allowed values                                                                  |
|-----------|----------|---------------------------------------------------------------------------------|
| `code`    | `string` | `INVALID_CREDENTIALS`, `EMAIL_NOT_CONFIRMED`, `LOCKED_OUT`, `ACCOUNT_DISABLED`, `BRIDGE_ERROR` |
| `message` | `string` | Safe, sanitised human-readable string (no email addresses, no LMS internals)   |

**Static message map** — these exact strings are what the renderer displays:

| `code`                | Display message                                                           |
|------------------------|---------------------------------------------------------------------------|
| `INVALID_CREDENTIALS`  | "Invalid email or password"                                               |
| `EMAIL_NOT_CONFIRMED`  | "Please confirm your email address before logging in."                    |
| `LOCKED_OUT`           | "Your account is temporarily locked. Please contact your administrator."  |
| `ACCOUNT_DISABLED`     | "Your account has been disabled. Please contact your administrator."      |
| `BRIDGE_ERROR`         | "Unable to reach the server. Please check your connection and try again." |

**Mapping logic (Python bridge)**:
```python
def map_lms_error(status_code: int, error_message: str) -> dict:
    msg = error_message.lower()
    if "invalid email/password" in msg:
        return {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}
    if "is not confirmed" in msg:
        return {"code": "EMAIL_NOT_CONFIRMED", "message": "Please confirm your email address before logging in."}
    if "is locked out" in msg:
        return {"code": "LOCKED_OUT", "message": "Your account is temporarily locked. Please contact your administrator."}
    if "is disabled" in msg:
        return {"code": "ACCOUNT_DISABLED", "message": "Your account has been disabled. Please contact your administrator."}
    return {"code": "BRIDGE_ERROR", "message": "Unable to reach the server. Please check your connection and try again."}
```

---

## Design Tokens (Login Page Specific)

The following tokens from `frontend/assets/design-tokens.css` are directly referenced by
the login page. No new tokens are added — all values come from spec 001.

| Token                        | Login Page Usage                                      |
|------------------------------|-------------------------------------------------------|
| `--color-primary`            | LOGIN button gradient start; FAB background           |
| `--color-primary-container`  | LOGIN button gradient end                             |
| `--color-on-primary`         | LOGIN button text                                     |
| `--color-surface`            | Page background (canvas level)                        |
| `--color-surface-container-low` | Page background gradient second stop               |
| `--color-surface-container-lowest` | Card background (`#ffffff`)                   |
| `--color-on-surface`         | Card headline "Welcome Back"                          |
| `--color-on-surface-variant` | Subtitle text, label text, footer text                |
| `--color-outline-variant`    | Input ghost border at 20% opacity                     |
| `--color-error`              | Inline error message text                             |
| `--shadow-ambient`           | Card drop shadow                                      |
| `--radius-xl`                | Card corner radius (1.5rem)                           |
| `--radius-default`           | Button and input corner radius (0.5rem)               |
| `--font-display`             | "Welcome Back" headline font (Manrope 700)            |
| `--font-body`                | Subtitle and form label font (Inter 400/500)          |

---

## State Machine: Login Form

```
IDLE
  → [user types] → IDLE (live validation only for email format hint)
  → [submit with invalid] → VALIDATION_ERROR → IDLE (user edits)
  → [submit valid] → LOADING
      → [bridge success] → NAVIGATING (main.js routes to exam-code)
      → [bridge error] → ERROR (show inline message) → IDLE (user retries)

IDLE: form enabled, button enabled, no spinner, no error
LOADING: form disabled, button disabled, spinner visible, no error
VALIDATION_ERROR: form enabled, button enabled, no spinner, error visible
ERROR: form enabled, button enabled, no spinner, error visible (bridge error)
NAVIGATING: window.location.href = exam-code page (renderer no longer active)
```
