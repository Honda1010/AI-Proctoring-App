# Quickstart: Exam Access Page

**Branch**: `003-exam-access-page` | **Date**: 2026-04-15

---

## Prerequisites

- Spec 001-foundation and 002-login-page fully implemented and working  
- `npm install` run at project root  
- `py -m pip install -r python_bridge/requirements.txt` run  
- `config.json` at project root with valid `baseUrl` (must start with `https://`)  

---

## Run the app

```powershell
# From project root
npm start
```

The app loads the loading page → starts the Python bridge → restores session (or shows login) → navigates to the Exam Access page for an authenticated student.

---

## Test the Exam Access page in isolation (mock mode)

To develop and test the Exam Access page without a running LMS:

**1. Start the Python bridge directly** (it will serve mock-friendly responses):
```powershell
py python_bridge\server.py --port 5050 --config config.json
```

**2. Test a successful exam start** (curl or PowerShell):
```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:5050/exam-access" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"quizCode": "EXAM2026", "token": "fake-dev-token"}'
```

Expected: 200 with ExamSession JSON (proxied to LMS) or 404 if the LMS rejects the code.

**3. Use the mock fixture directly** for offline UI development:  
Copy `specs/003-exam-access-page/mocks/exam-start-success.json` to drive the UI without any network.

---

## Files modified by this spec

| File | Change |
|------|--------|
| `python_bridge/exam.py` | NEW — `exam_bp` Blueprint, `POST /exam-access` route, `map_lms_exam_error()` |
| `python_bridge/server.py` | Register `exam_bp` |
| `frontend/pages/exam-code/index.html` | Replace placeholder with full Exam Access page |
| `frontend/pages/exam-code/exam-code.css` | NEW — page-specific Ethereal Authority styles |
| `frontend/pages/exam-code/exam-code.js` | NEW — form controller, loading state, IPC, timeout |
| `frontend/main.js` | Add `examSession` var, `bridge:start-exam`, `bridge:get-exam-session` handlers, 401 redirect |
| `frontend/preload.js` | Add `startExam()`, `getExamSession()` to `window.bridge` |

---

## Key IDs and channels

| Symbol | Value |
|--------|-------|
| Form element | `#exam-code-form` |
| Code input | `#code-input` |
| Submit button | `#start-btn` |
| Button text span | `#start-btn-text` |
| Button spinner | `#start-spinner` |
| Error element | `#code-error` |
| Student name | `#student-name` |
| IPC start exam | `bridge:start-exam` |
| IPC get session (exam page) | `bridge:get-exam-session` |
| Bridge HTTP | `POST http://127.0.0.1:5050/exam-access` |

---

## Error scenarios to test

| Scenario | Expected |
|----------|----------|
| Empty code submitted | Inline error: "Please enter your exam code." |
| Code not found (404) | Inline error: "Exam code not found. Please check the code and try again." |
| Already attempted (409) | Inline error: "You have already attempted this exam." |
| Expired token (401) | Silent redirect to Login page; session cleared |
| Network down (503) | Inline error: "Unable to reach the server. Please check your connection and try again." |
| Timeout (15 s elapsed) | Same error as network down; input re-enabled with value preserved |
| Valid code | Navigate to Exam page; ExamSession available via `bridge:get-exam-session` |
