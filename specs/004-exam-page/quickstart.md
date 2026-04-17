# Quickstart: Exam Page

**Branch**: `004-exam-page` | **Date**: 2026-04-16

---

## Prerequisites

Complete specs 001–003 are implemented and passing before starting spec 004 development.

- Node.js 20 LTS installed — verify: `node -v`
- Python 3.11+ installed — verify: `python --version`
- Electron dependencies installed — verify: `package.json` has `electron: "^33.0.0"`
- Python bridge dependencies installed — see step below

---

## One-Time Setup

### 1. Install Python bridge dependencies (if not already done)

```powershell
cd python_bridge
pip install -r requirements.txt
cd ..
```

### 2. Verify config.json exists at project root

```powershell
Test-Path config.json   # must return True
```

Config should have `base_url` pointing to the LMS. Example:

```json
{
  "base_url": "https://your-lms.example.com",
  "flask_port": 5000
}
```

---

## Starting the App

### Terminal 1 — Python bridge

```powershell
cd python_bridge
python server.py
```

Expected output: `* Running on http://127.0.0.1:5000`

### Terminal 2 — Electron app

```powershell
npm start
```

The Electron window opens on the Login page.

---

## Reaching the Exam Page

The Exam page is accessed after a successful exam code flow:

1. Log in with valid credentials (spec 002)
2. Enter a valid exam code on the Exam Code page (spec 003)
3. Exam page loads showing questions and the countdown timer

For development/testing without a live LMS, use the mock flow in the section below.

---

## Mock Testing (Offline Dev)

Use the mock JSON files in `specs/004-exam-page/mocks/` to test renderer logic without a live LMS.

### Mock: exam session (populated from spec 003 handoff)

`mocks/exam-session.json` — a sample `ExamSession` object. Populate `examSession` in main.js during dev:

```js
// TEMP DEV ONLY — remove before shipping
examSession = require('./specs/004-exam-page/mocks/exam-session.json');
```

### Mock: successful submit

Load `mocks/submit-success.json` as the bridge response. To inject without a running LMS:

```js
// In main.js ipcMain.handle('bridge:submit-exam', ...), replace net.fetch with:
// const data = require('./specs/004-exam-page/mocks/submit-success.json');
// submitResult = data; examSession = null; return { ok: true, data };
```

### Mock: bridge error

Inject `mocks/submit-bridge-error.json` in the same handler for error path testing:

```js
// return { ok: false, error: require('./specs/004-exam-page/mocks/submit-bridge-error.json') };
```

---

## Manual Test Scenarios

These scenarios map directly to the spec SCs (SC-001–SC-006) and FRs.

### Scenario 1 — Page loads from valid exam session (SC-001, FR-001)

**Pre-condition**: `examSession` contains a valid session (use mock or real LMS flow).  
**Steps**:
1. Navigate to `frontend/pages/exam/index.html`
2. Observe full-page loading skeleton while IPC resolves
3. Confirm exam title is shown in the fixed header
4. Confirm first question text and its choices are rendered

**Expected**: Page loads in < 2 seconds; title and first question are visible. Loading skeleton never persists more than 2 seconds.

---

### Scenario 2 — Answer selection persists across navigation (SC-002, FR-008)

**Steps**:
1. Select an answer for Question 1
2. Navigate to Question 2 using the "Next" button
3. Navigate back to Question 1 using the "Prev" button

**Expected**: The answer selected in step 1 is still visually selected (radio-style). Navigator pill for Question 1 shows "answered" state (primary colour fill).

---

### Scenario 3 — Submit exam (success) (SC-003, FR-012, FR-013, FR-014)

**Pre-condition**: Bridge is running and returning `submit-success.json` shape (or use live LMS).  
**Steps**:
1. Complete at least one question
2. Click "Submit Exam" button
3. Confirm modal appears with unanswered-count message
4. Click "Submit" in the modal
5. Observe loading state on button
6. Confirm navigation to result page

**Expected**: Submit payload is `{ answers: [{questionId, choiceId}, ...] }` (only answered questions). Result page loads with score data.

---

### Scenario 4 — Countdown timer display and warning (SC-004, FR-016)

**Steps**:
1. Start exam session with `duration: "00:06:00"` (mock: edit `exam-session.json`)
2. Wait until timer reads `04:59`

**Expected**: Timer ticks down accurately every 1 second. When timer crosses 5 minutes remaining, timer chip text colour changes to `var(--color-error)`.

---

### Scenario 5 — Auto-submit at 00:00:00 (SC-005, FR-020, FR-021)

**Steps**:
1. Start exam session with `duration: "00:00:10"` (10-second exam)
2. Wait for timer to reach `00:00:00`

**Expected (success path)**: Bridge returns success; app navigates to result page automatically, no confirmation modal shown.  
**Expected (failure path)**: Submit button shows error message and "Retry" button; timer stays frozen at `00:00:00`; student can click Retry.

---

### Scenario 6 — Flag question toggle (FR-018, FR-019)

**Steps**:
1. Click the flag button on Question 1
2. Navigate to Question 2, then back to Question 1

**Expected**: Navigator pill for Question 1 shows "flagged" style (tertiary colour, `--color-tertiary`). Clicking the flag button again removes the flag (pill reverts to "answered" or "unanswered" state).

---

### Scenario 7 — Webcam panel (FR-022, FR-023) [FR numbers from design context]

**Steps**:
1. Allow camera access when prompted
2. Observe the proctoring aside panel

**Expected**: Live video renders in the camera feed area. Status rows below the feed show static placeholder values.

**Steps (denial path)**:
1. Deny camera access
2. Observe the proctoring aside panel

**Expected**: Placeholder "Camera unavailable" state shown; exam continues normally; no error overlay on main content.

---

### Scenario 8 — UNAUTHORIZED on submit

**Steps** (requires mock injection or expired token):
1. Set access token to an expired value
2. Attempt to submit

**Expected**: No error shown to user on exam page. Main.js redirects to Login page silently. `submitResult` remains null.

---

## Bridge HTTP Testing (PowerShell)

Test the bridge endpoint directly after `python server.py` is running:

```powershell
# Health check
Invoke-WebRequest -Uri "http://127.0.0.1:5000/ping" -Method GET | Select-Object -ExpandProperty Content

# Submit exam — success path (requires valid token and attemptId)
$body = @{
    attemptId = 42
    answers   = @(
        @{ questionId = 101; choiceId = 205 },
        @{ questionId = 102; choiceId = 210 }
    )
    token     = "YOUR_VALID_JWT_HERE"
} | ConvertTo-Json -Depth 3

Invoke-WebRequest `
    -Uri    "http://127.0.0.1:5000/submit-exam" `
    -Method POST `
    -ContentType "application/json" `
    -Body   $body |
    Select-Object -ExpandProperty Content

# Submit exam — invalid attemptId (expect 400 BRIDGE_ERROR)
$badBody = '{ "attemptId": -1, "answers": [], "token": "t" }'
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:5000/submit-exam" -Method POST -ContentType "application/json" -Body $badBody
} catch {
    $_.Exception.Response.StatusCode
    $_ | Select-Object -ExpandProperty ErrorDetails
}
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Exam page stays on loading skeleton forever | `bridge:get-exam-session` returns `{ ok: false }` | Verify spec 003 ran successfully and `examSession` is non-null in main.js |
| Submit button does nothing | `window.bridge.submitExam` is undefined | Check `preload.js` ALLOWED_INVOKE_CHANNELS includes `'bridge:submit-exam'` |
| Bridge returns 500 for `/submit-exam` | `attempt_id` type check failing on Python side | Verify `attemptId` in body is a number, not a string |
| Camera never streams | Browser security — page served from `file://` protocol | Electron must have `webSecurity: false` or use localhost |
| Timer jumps by 2 seconds | setInterval not running; page backgrounded | Electron `backgroundThrottling: false` must be set in BrowserWindow |
