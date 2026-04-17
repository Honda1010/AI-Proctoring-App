# Contract: Exam Submission (Bridge + IPC)

**Branch**: `004-exam-page` | **Date**: 2026-04-16  
**Layer**: IPC (Electron renderer ↔ main) + HTTP (main ↔ Python bridge)

---

## Overview

This document specifies all new and modified interface contracts for spec 004. Two new IPC channels are added (mirroring spec 003 style), and one new bridge HTTP endpoint is created.

```
Renderer (exam.js)
  │  window.bridge.submitExam(answers)      [NEW IPC — invoke]
  │  window.bridge.getSubmitResult()        [NEW IPC — invoke]
  │  window.bridge.getExamSession()         [existing — spec 003, read-only]
  ▼
Electron main.js
  │  ipcMain.handle('bridge:submit-exam')   — reads examSession + token; calls bridge; stores result
  │  ipcMain.handle('bridge:get-submit-result') — returns submitResult
  │  ipcMain.handle('bridge:get-exam-session')  — existing, unchanged
  │  On UNAUTHORIZED: clears session, loads Login page (no channel response)
  ▼
Python bridge (Flask, port 5000)
  │  POST /submit-exam                      [NEW HTTP endpoint]
  ▼
LMS HTTP API
     POST /api/QuizAttempts/submit/{attemptId}
```

---

## IPC Contract 1 — `bridge:submit-exam`

### Description

Submits the student's answers for the active exam attempt. main.js enriches the renderer payload with the JWT and attempt ID before proxying to the Python bridge. On success, the `SubmitResult` is cached in `submitResult` and the renderer is instructed to navigate to the result page. On `UNAUTHORIZED`, main.js silently clears the session and loads Login without returning to the renderer.

### Registration (main.js)

```js
ipcMain.handle('bridge:submit-exam', async (_event, { answers }) => {
  // 1. Read token (main.js owns all tokens)
  const token = sessionMemory?.accessToken ?? await keytar.getPassword('AI-Proctoring-App', 'access-token');
  // 2. Read attemptId from examSession
  const attemptId = examSession?.attemptId;
  // 3. Call bridge
  const resp = await net.fetch('http://127.0.0.1:5000/submit-exam', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ attemptId, answers, token })
  });
  const data = await resp.json();
  if (!resp.ok) {
    if (data.code === 'UNAUTHORIZED') {
      await clearAllKeytarEntries();
      BrowserWindow.getFocusedWindow().loadFile(path.join(__dirname, 'pages/login/index.html'));
      return; // renderer invocation never resolves
    }
    return { ok: false, error: data };
  }
  submitResult = data;
  examSession = null;
  return { ok: true, data };
});
```

### Exposure (preload.js)

```js
// ALLOWED_INVOKE_CHANNELS:
'bridge:submit-exam'

// window.bridge:
submitExam: (answers) => ipcRenderer.invoke('bridge:submit-exam', { answers })
```

### Request (renderer → main)

```ts
{
  answers: Array<{
    questionId: number,   // positive integer, matches ExamSession.questions[].id
    choiceId:   number    // positive integer, matches ExamSession.questions[].choices[].id
  }>
}
```

The `answers` array contains only answered questions. Unanswered questions are omitted (not `{ questionId: X, choiceId: null }`).

### Response — Success

HTTP 200 from bridge; main.js returns:

```json
{
  "ok": true,
  "data": {
    "quizCode":       "CS101-MID",
    "quizTitle":      "Midterm Examination",
    "score":          18,
    "totalQuestions": 20,
    "percentage":     90.0,
    "questions": [
      {
        "questionText":  "What is 2 + 2?",
        "studentChoice": "4",
        "correctChoice": "4",
        "isCorrect":     true
      }
    ]
  }
}
```

### Response — Failure

Returns `{ "ok": false, "error": { "code": "...", "message": "..." } }`:

| `error.code`     | HTTP status from bridge | Trigger condition                                 |
|------------------|------------------------|---------------------------------------------------|
| `EXAM_NOT_FOUND` | 404                    | LMS returns 404                                   |
| `UNAUTHORIZED`   | *(no response)*        | LMS returns 401 — main.js loads Login, no reply   |
| `BRIDGE_ERROR`   | 503                    | Any other LMS error, network timeout, or exception |

### Side effects

| Event                        | Effect on main.js state                                                   |
|------------------------------|---------------------------------------------------------------------------|
| Submit success               | `submitResult` ← LMS response; `examSession` ← `null`                   |
| Submit failure (not 401)     | `submitResult` and `examSession` unchanged                               |
| Submit returns UNAUTHORIZED  | session cleared (keytar), Login page loaded, `submitResult` = `null`     |

---

## IPC Contract 2 — `bridge:get-submit-result`

### Description

Used exclusively by the result page (spec 005) to read the `SubmitResult` that was cached by a successful `bridge:submit-exam` call.

### Registration (main.js)

```js
ipcMain.handle('bridge:get-submit-result', async () => {
  if (!submitResult) return { ok: false };
  return { ok: true, result: submitResult };
});
```

### Exposure (preload.js)

```js
// ALLOWED_INVOKE_CHANNELS:
'bridge:get-submit-result'

// window.bridge:
getSubmitResult: () => ipcRenderer.invoke('bridge:get-submit-result')
```

### Request

None.

### Response — Success

```json
{
  "ok": true,
  "result": {
    "quizCode":       "CS101-MID",
    "quizTitle":      "Midterm Examination",
    "score":          18,
    "totalQuestions": 20,
    "percentage":     90.0,
    "questions": [ { ... } ]
  }
}
```

### Response — No result available

```json
{ "ok": false }
```

Renderer action: redirect to Login page.

---

## HTTP Contract — `POST /submit-exam` (Python bridge)

**File**: `python_bridge/exam.py` (added to existing `exam_bp` Blueprint)

### URL

```
POST http://127.0.0.1:5000/submit-exam
Content-Type: application/json
```

### Request body

```json
{
  "attemptId": 42,
  "answers": [
    { "questionId": 101, "choiceId": 205 },
    { "questionId": 102, "choiceId": 210 }
  ],
  "token": "<JWT — not logged, not stored, not reflected>"
}
```

| Field       | Type              | Constraints                                |
|-------------|-------------------|--------------------------------------------|
| `attemptId` | positive integer  | Required. Bridge validates > 0.            |
| `answers`   | array             | Required. May be empty (`[]`).             |
| `token`     | string            | Required. Used only for outbound Auth header. |

### Outbound LMS call

```
POST {BASE_URL}/api/QuizAttempts/submit/{attemptId}
Authorization: Bearer {token}
Content-Type: application/json

{
  "answers": [
    { "questionId": 101, "choiceId": 205 },
    { "questionId": 102, "choiceId": 210 }
  ]
}
```

Note: `token` is NOT forwarded in the LMS body — it is used as the `Authorization` header only.

### Response — Success (LMS 200)

HTTP 200. Bridge relays LMS JSON body verbatim:

```json
{
  "quizCode":       "CS101-MID",
  "quizTitle":      "Midterm Examination",
  "score":          18,
  "totalQuestions": 20,
  "percentage":     90.0,
  "questions": [
    {
      "questionText":  "What is 2 + 2?",
      "studentChoice": "4",
      "correctChoice": "4",
      "isCorrect":     true
    }
  ]
}
```

### Response — Failure

| Scenario                     | Bridge HTTP | Response body                                                                        |
|------------------------------|-------------|--------------------------------------------------------------------------------------|
| `attemptId` not integer > 0  | 400         | `{"code":"BRIDGE_ERROR","message":"Unable to reach the server. Please check your connection and try again."}` |
| LMS returns 401              | 401         | `{"code":"UNAUTHORIZED","message":"Your session has expired. Please log in again."}` |
| LMS returns 404              | 404         | `{"code":"EXAM_NOT_FOUND","message":"This exam could not be found. Please contact your instructor."}` |
| LMS returns any other error  | 503         | `{"code":"BRIDGE_ERROR","message":"Unable to reach the server. Please check your connection and try again."}` |
| Network timeout / exception  | 503         | `{"code":"BRIDGE_ERROR","message":"Unable to reach the server. Please check your connection and try again."}` |

### Python implementation sketch

```python
@exam_bp.route('/submit-exam', methods=['POST'])
def submit_exam():
    body = request.get_json(force=True, silent=True) or {}
    attempt_id = body.get('attemptId')
    answers    = body.get('answers', [])
    token      = body.get('token', '')

    if not isinstance(attempt_id, int) or attempt_id <= 0:
        return jsonify(map_lms_submit_error(400, {})), 400

    try:
        resp = requests.post(
            f"{BASE_URL}/api/QuizAttempts/submit/{attempt_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"answers": answers},
            timeout=10
        )
    except requests.RequestException:
        return jsonify(map_lms_submit_error(0, {})), 503

    if resp.status_code == 200:
        return jsonify(resp.json()), 200
    return jsonify(map_lms_submit_error(resp.status_code, {})), _bridge_status(resp.status_code)


def map_lms_submit_error(status, _body):
    if status == 401:
        return {"code": "UNAUTHORIZED",   "message": "Your session has expired. Please log in again."}
    if status == 404:
        return {"code": "EXAM_NOT_FOUND", "message": "This exam could not be found. Please contact your instructor."}
    return         {"code": "BRIDGE_ERROR","message": "Unable to reach the server. Please check your connection and try again."}


def _bridge_status(lms_status):
    """Map LMS HTTP status to bridge HTTP status."""
    return {401: 401, 404: 404}.get(lms_status, 503)
```

---

## Security Notes

1. `token` is extracted from the request body, used as the `Authorization` header value, and immediately discarded. It is never stored, logged, cached, or reflected in any response body.
2. `attemptId` is validated as a positive integer before being interpolated into the URL path, preventing path injection.
3. `answers` is forwarded verbatim; content validation is delegated to the LMS (authoritative source).
4. All error messages are static strings — no raw LMS response body is forwarded.
