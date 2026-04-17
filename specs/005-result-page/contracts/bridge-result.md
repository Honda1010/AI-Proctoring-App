# Contract: Result IPC Channels

**Branch**: `005-result-page` | **Date**: 2026-04-17  
**Input**: FR-004, FR-005, FR-009 from `spec.md`

---

## Overview

Three IPC channels are involved in the Result page flow:

| Channel | Direction | Status |
|---------|-----------|--------|
| `bridge:get-submit-result` | renderer → main | Already implemented (spec 004) |
| `bridge:get-result` | renderer → main → bridge → LMS | **NEW** (this spec) |
| `bridge:clear-submit-result` | renderer → main | **NEW** (this spec) |

---

## 1. `bridge:get-submit-result` *(existing — unchanged)*

**Purpose**: Retrieve the `SubmitResult` stored in main.js after a successful exam submission.  
**Invoked by**: `result.js` first on `DOMContentLoaded`.

### Request
No arguments.

### Response

#### Success (submitResult is set)
```json
{ "ok": true, "data": { "quizCode": "string", "quizTitle": "string", "score": 7, "totalQuestions": 10, "percentage": 70.0, "questions": [ { "questionText": "string", "studentChoice": "string", "correctChoice": "string", "isCorrect": true } ] } }
```

#### Not available (submitResult is null)
```json
{ "ok": false }
```

**Result page behaviour on `{ ok: false }`**: fall through to `bridge:get-result` recovery path (FR-004).

---

## 2. `bridge:get-result` *(new)*

**Purpose**: Recover a result from the LMS when `submitResult` is absent in memory but `examSession.attemptId` is known. Calls `GET /api/QuizAttempts/result/{attemptId}` via the Python bridge.

**Python bridge route**: `POST /result` (main.js sends a POST with body `{ attemptId, token }`)  
**LMS endpoint**: `GET /api/QuizAttempts/result/{attemptId}` 🔒

### Renderer invocation (result.js)
```javascript
const recovery = await window.bridge.getResult();
```

### main.js behaviour
1. Read `accessToken` from `sessionMemory?.accessToken` or `keytar.getPassword(KEYTAR_SERVICE, 'access-token')`.
2. Read `attemptId` from `examSession?.attemptId`.
3. If `attemptId` is undefined/null → return `{ ok: false, redirect: 'login' }`.
4. POST `{ attemptId, token }` to `http://127.0.0.1:${bridgePort}/result`.
5. On HTTP 200 → cache response body as `submitResult` → return `{ ok: true, data: body }`.
6. On `code === 'UNAUTHORIZED'` → clear keytar + sessionMemory → navigate to Login → return (renderer IPC call never resolves).
7. On other error → return `{ ok: false, error: body }`.

### Request
No renderer arguments. Token and attemptId sourced from main.js module scope.

### Response

#### Success (LMS 200)
```json
{ "ok": true, "data": { "quizCode": "string", "quizTitle": "string", "score": 7, "totalQuestions": 10, "percentage": 70.0, "questions": [ { "questionText": "string", "studentChoice": "string", "correctChoice": "string", "isCorrect": true } ] } }
```

#### No attemptId available
```json
{ "ok": false, "redirect": "login" }
```

#### Expired / invalid token (LMS 401)
main.js navigates to Login. IPC call never resolves.

#### Other failure
```json
{ "ok": false, "error": { "code": "BRIDGE_ERROR", "message": "Unable to reach the server. Please check your connection and try again." } }
```

---

## 3. `bridge:clear-submit-result` *(new)*

**Purpose**: Clear both `submitResult` and `examSession` in main.js and navigate the Electron window to the Exam Access page. Called when the student clicks "Back to Home".

### Renderer invocation (result.js)
```javascript
await window.bridge.clearSubmitResult();
// renderer navigation is handled by main.js — this call may not resolve
// if main.js navigates before the IPC reply is sent
```

### main.js behaviour
1. Set `submitResult = null`.
2. Set `examSession = null`.
3. Call `mainWindow?.loadFile(path.join(__dirname, 'pages/exam-code/index.html'))`.
4. Return `{ ok: true }` (may not reach renderer if navigation happens first).

### Request
No arguments.

### Response
```json
{ "ok": true }
```

---

## Python Bridge Route: `POST /result`

**File**: `python_bridge/exam.py` (add to `exam_bp`)  
**Route**: `POST /result`  
**LMS call**: `GET /api/QuizAttempts/result/{attempt_id}` with `Authorization: Bearer {token}`

### Request body (from main.js)
```json
{ "attemptId": 8, "token": "<access_token>" }
```

### Success response (200 OK — relay LMS body directly)
```json
{ "quizCode": "EXAM2026", "quizTitle": "Midterm Exam — Introduction to AI", "score": 7, "totalQuestions": 10, "percentage": 70.0, "questions": [ { "questionText": "...", "studentChoice": "...", "correctChoice": "...", "isCorrect": true } ] }
```

### Error responses

| LMS Status | Bridge response code | HTTP | Message |
|------------|---------------------|------|---------|
| 401 | `UNAUTHORIZED` | 401 | "Your session has expired. Please log in again." |
| 400 (not submitted) | `NOT_SUBMITTED` | 400 | "The exam has not been submitted yet." |
| 404 | `BRIDGE_ERROR` | 503 | "Unable to reach the server. Please check your connection and try again." |
| Network error | `BRIDGE_ERROR` | 503 | "Unable to reach the server. Please check your connection and try again." |
