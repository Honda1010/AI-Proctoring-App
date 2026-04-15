# Contract: POST /login (Bridge Endpoint)

**Bridge Route**: `POST http://127.0.0.1:5050/login`
**Consumer**: Electron main process (`frontend/main.js`)
**Provider**: Python Flask bridge (`python_bridge/server.py`)
**Spec**: `specs/002-login-page/spec.md` FR-005, FR-006
**Date**: 2026-04-15

---

## Purpose

This endpoint is the only way the Electron process can authenticate a student against
the LMS. The bridge proxies the call, maps LMS errors to typed codes, and sanitises
the LMS response before returning it. The renderer never calls this endpoint directly.

---

## Request

**Method**: `POST`
**Content-Type**: `application/json`

```json
{
  "email": "student@institution.edu",
  "password": "P@ssword123"
}
```

| Field      | Type   | Required | Validation                              |
|------------|--------|----------|-----------------------------------------|
| `email`    | string | Yes      | Non-empty string                        |
| `password` | string | Yes      | Non-empty string                        |

---

## Response — Success

**HTTP Status**: `200 OK`
**Content-Type**: `application/json`

The full LMS `LoginResponse` payload is forwarded as-is:

```json
{
  "id": "a3f1c2d4-0000-0000-0000-000000000000",
  "email": "student@institution.edu",
  "firstName": "John",
  "lastName": "Doe",
  "profilePictureUrl": "https://cdn.example.com/pics/john.jpg",
  "token": "<JWT access token>",
  "expinresIn": 3600,
  "refreshToken": "<refresh token>",
  "refreshTokenExpiration": "2026-04-29T10:00:00Z"
}
```

| Field                    | Type            | Notes                                    |
|--------------------------|-----------------|------------------------------------------|
| `id`                     | string          | Student's unique user ID                 |
| `email`                  | string          | Student's email                          |
| `firstName`              | string          | Student's first name                     |
| `lastName`               | string          | Student's last name                      |
| `profilePictureUrl`      | string \| null  | CDN URL; may be `null`                   |
| `token`                  | string          | JWT access token (3600s TTL)             |
| `expinresIn`             | number          | Access token TTL in seconds              |
| `refreshToken`           | string          | Refresh token for silent re-auth         |
| `refreshTokenExpiration` | string          | ISO 8601 UTC; 14-day TTL                 |

---

## Response — Error

**HTTP Status**: `400 Bad Request` (validation) or `401 Unauthorized` / `500 Internal Server Error` (LMS error)
**Content-Type**: `application/json`

All errors use this envelope. The `message` field contains ONLY a safe static string —
never a raw LMS `errorMessage` with email addresses or student-identifiable info.

```json
{
  "code": "INVALID_CREDENTIALS",
  "message": "Invalid email or password"
}
```

| `code`                | HTTP status | Trigger condition                          | `message` (exact)                                                           |
|-----------------------|-------------|---------------------------------------------|-----------------------------------------------------------------------------|
| `INVALID_CREDENTIALS` | 401         | LMS `errorMessage` contains `"Invalid Email/password"` | "Invalid email or password" |
| `EMAIL_NOT_CONFIRMED` | 401         | LMS `errorMessage` contains `"is not confirmed"`       | "Please confirm your email address before logging in." |
| `LOCKED_OUT`          | 401         | LMS `errorMessage` contains `"is locked out"`          | "Your account is temporarily locked. Please contact your administrator." |
| `ACCOUNT_DISABLED`    | 500         | LMS `errorMessage` contains `"is disabled"`            | "Your account has been disabled. Please contact your administrator." |
| `BRIDGE_ERROR`        | 503         | `requests.exceptions.RequestException` or unexpected   | "Unable to reach the server. Please check your connection and try again." |

---

## Security Constraints

- The `email` and `password` values from the request body MUST NOT appear in any server log,
  `print()` statement, or error response.
- The raw LMS `errorMessage` MUST NOT be forwarded to the consumer. Only the static `message`
  strings above are permitted.
- This endpoint binds to `127.0.0.1` only (loopback). It is not externally accessible.
- CORS policy is restricted to `localhost` origins only (established in spec 001).

---

## Mock Fixtures

| Scenario               | File                                              |
|------------------------|---------------------------------------------------|
| Login success          | `specs/002-login-page/mocks/login-ok.json`        |
| Invalid credentials    | `specs/002-login-page/mocks/login-invalid-creds.json` |
| Email not confirmed    | `specs/002-login-page/mocks/login-not-confirmed.json` |
| Account locked         | `specs/002-login-page/mocks/login-locked.json`    |
| Account disabled       | `specs/002-login-page/mocks/login-disabled.json`  |
| Bridge unreachable     | `specs/002-login-page/mocks/login-bridge-error.json` |
