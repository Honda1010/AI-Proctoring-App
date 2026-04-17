# Quickstart: Result Page

**Branch**: `005-result-page` | **Date**: 2026-04-17

---

## Prerequisites

Specs 001–004 are implemented and passing before starting spec 005 development.

- Node.js 20 LTS installed — verify: `node -v`
- Python 3.11+ installed — verify: `python --version`
- npm dependencies installed — verify: `Test-Path node_modules`
- Python bridge dependencies installed — verify `python_bridge/requirements.txt` is installed

---

## One-Time Setup

### 1. Install Python bridge dependencies (if not already done)

```powershell
cd python_bridge
pip install -r requirements.txt
cd ..
```

### 2. Install npm dependencies (if not already done)

```powershell
npm install
```

### 3. Verify config.json exists at project root

```powershell
Test-Path config.json   # must return True
```

---

## Starting the App

### Terminal 1 — Electron app (spawns Python bridge automatically)

```powershell
npm start
```

The Electron window opens on the Login page. The app will:
1. Spawn the Python bridge on port 5050
2. Show the loading page while the bridge starts
3. Navigate to Login (if no saved session) or Exam Code (if saved session exists)

---

## Reaching the Result Page

The Result page is the final screen in the exam workflow:

1. Log in with valid credentials (spec 002)
2. Enter a valid exam code on the Exam Code page (spec 003)
3. Complete the exam on the Exam Page — answer questions (spec 004)
4. Click "Submit Exam" (or let the timer expire) — spec 004 submits answers
5. The Result page loads automatically after a successful submission

---

## Mock Testing (Offline Dev)

### Scenario 1 — Normal flow: submitResult is already in memory

Inject a mock `submitResult` directly in `main.js` during development. In `app.whenReady()`, before loading any page, temporarily add:

```javascript
// DEV ONLY — remove before shipping
submitResult = require('./path/to/specs/005-result-page/mocks/result-success.json');
mainWindow.loadFile(path.join(__dirname, 'pages/result/index.html'));
```

This bypasses the full exam flow and goes straight to the Result page.

### Scenario 2 — Recovery flow: submitResult absent, attemptId known

Inject a mock `examSession` only:

```javascript
// DEV ONLY — remove before shipping
examSession = { attemptId: 8, title: 'Test Exam', duration: '00:30:00', questions: [] };
// leave submitResult = null
mainWindow.loadFile(path.join(__dirname, 'pages/result/index.html'));
```

The Result page should detect `submitResult === null`, call `bridge:get-result`, and attempt `GET /api/QuizAttempts/result/8` on the LMS.

### Scenario 3 — Redirect: no submitResult, no attemptId

```javascript
// DEV ONLY — remove before shipping
// leave both submitResult = null AND examSession = null (defaults)
mainWindow.loadFile(path.join(__dirname, 'pages/result/index.html'));
```

The page should redirect immediately to the Login page.

### Scenario 4 — Failed exam (percentage < 50%)

Use `specs/005-result-page/mocks/result-failed.json` in Scenario 1 above. Verify the pass/fail chip shows "Failed" styling.

---

## Key Files for This Spec

| File | Change |
|------|--------|
| `python_bridge/exam.py` | ADD `map_lms_result_error()` + `POST /result` route |
| `frontend/main.js` | MODIFY `bridge:submit-exam` (remove `examSession = null`); ADD `bridge:get-result`; ADD `bridge:clear-submit-result` |
| `frontend/preload.js` | ADD 2 channels + 2 methods |
| `frontend/pages/result/index.html` | REPLACE placeholder with full Result page HTML |
| `frontend/pages/result/result.css` | NEW |
| `frontend/pages/result/result.js` | NEW |

---

## Quick Smoke Test Checklist

After implementing all tasks, verify these scenarios manually:

- [ ] **Score summary renders**: exam title, exam code, score fraction, percentage, pass/fail chip all visible
- [ ] **Passed style** (≥50%): chip shows "Passed" in accent/success colour
- [ ] **Failed style** (<50%): chip shows "Failed" in destructive colour
- [ ] **Question breakdown**: all rows show questionText, studentChoice, correctChoice, isCorrect indicator
- [ ] **No submitResult + no attemptId**: redirects to Login (no result content flashed)
- [ ] **Recovery path**: with only `examSession.attemptId` set, page fetches and renders result from LMS
- [ ] **Back to Home**: navigates to Exam Code page; revisiting Result page immediately redirects to Login
- [ ] **Empty questions array**: breakdown section hidden; score summary shown alone
- [ ] **50+ questions**: breakdown scrolls without layout overflow
