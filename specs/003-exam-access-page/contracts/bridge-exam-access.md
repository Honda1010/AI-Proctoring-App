# Contract: Bridge Exam Access Endpoint

**Route**: `POST /exam-access`  
**Owner**: Python bridge (`python_bridge/exam.py`)  
**Consumer**: Electron main process (`frontend/main.js`, `bridge:start-exam` IPC handler)  
**Date**: 2026-04-15

---

## Request

**Method**: `POST`  
**URL**: `http://127.0.0.1:{pythonPort}/exam-access`  
**Content-Type**: `application/json`

```json
{
  "quizCode": "LMN-492-XQ",
  "token": "<JWT access token>"
}
```

| Field      | Type     | Required | Description                                          |
|------------|----------|----------|------------------------------------------------------|
| `quizCode` | `string` | Yes      | Exam code entered by the student (whitespace trimmed)|
| `token`    | `string` | Yes      | JWT access token from the student's stored session   |

**Security note**: The `token` field is supplied by main.js only. The renderer never holds tokens and never calls this endpoint directly.

---

## Responses

### 200 OK — Exam started successfully

```json
{
  "attemptId": 42,
  "title": "Midterm Exam — Introduction to AI",
  "duration": "01:30:00",
  "questions": [
    {
      "questionText": "What is supervised learning?",
      "choices": [
        { "choiceText": "Learning with labelled data" },
        { "choiceText": "Learning without labelled data" },
        { "choiceText": "Reinforcement from an environment" },
        { "choiceText": "None of the above" }
      ]
    }
  ]
}
```

### 400 Bad Request — Empty quizCode or token

```json
{
  "code": "BRIDGE_ERROR",
  "message": "Unable to reach the server. Please check your connection and try again."
}
```

### 401 Unauthorized — Expired or invalid token

```json
{
  "code": "UNAUTHORIZED",
  "message": "Your session has expired. Please log in again."
}
```

### 404 Not Found — Exam code does not exist

```json
{
  "code": "EXAM_NOT_FOUND",
  "message": "Exam code not found. Please check the code and try again."
}
```

### 409 Conflict — Student has already attempted this exam

```json
{
  "code": "ALREADY_ATTEMPTED",
  "message": "You have already attempted this exam."
}
```

### 503 Service Unavailable — LMS unreachable (network failure, timeout)

```json
{
  "code": "BRIDGE_ERROR",
  "message": "Unable to reach the server. Please check your connection and try again."
}
```

---

## IPC Channel: `bridge:start-exam`

**Direction**: renderer → main.js (ipcMain.handle) → bridge HTTP → LMS → bridge → main.js → renderer  
**Invoke**: `window.bridge.startExam({ quizCode })`

**Input**:
```json
{ "quizCode": "LMN-492-XQ" }
```

**Output (success)**:
```json
{
  "ok": true,
  "data": { "attemptId": 42, "title": "...", "duration": "01:30:00", "questions": [...] }
}
```

**Output (failure)**:
```json
{
  "ok": false,
  "error": { "code": "EXAM_NOT_FOUND", "message": "Exam code not found. Please check the code and try again." }
}
```

**Special case — 401**: main.js clears the session (`clearAllKeytarEntries()`) and navigates to the Login page. The IPC call is not resolved to the renderer with `{ ok: false }` in this case.

---

## IPC Channel: `bridge:get-exam-session`

**Direction**: renderer (Exam page, on load) → main.js (ipcMain.handle)  
**Invoke**: `window.bridge.getExamSession()`

**Output (session present)**:
```json
{
  "ok": true,
  "session": { "attemptId": 42, "title": "...", "duration": "01:30:00", "questions": [...] }
}
```

**Output (no session)**:
```json
{ "ok": false }
```

If `ok: false` is returned by the Exam page, the page should navigate back to the Exam Access page.
