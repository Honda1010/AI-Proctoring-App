# Tasks: Exam Access Page

**Input**: Design documents from `/specs/003-exam-access-page/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Feature**: `003-exam-access-page`  
**Branch**: `003-exam-access-page`  
**Date**: 2026-04-15  
**Tests**: Not requested — implementation tasks only.

---

## Format: `[ID] [P?] [Story?] Description — file/path`

- **[P]**: Can run in parallel with other [P] tasks in the same phase (operates on a different file)
- **[Story]**: Which user story this task belongs to (US1 = P1, US2 = P2, US3 = P3)
- Every task includes the exact file path that must be modified or created

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create the Python bridge blueprint skeleton so the server can start with the new route registered.

- [X] T001 Create `python_bridge/exam.py` with `exam_bp` Flask Blueprint, `urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)`, and a stub `POST /exam-access` route that returns HTTP 501 (placeholder only — full implementation in T007)

**Checkpoint**: `python_bridge/exam.py` exists and can be imported without error.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire the IPC plumbing in `main.js` and `preload.js` that all three user stories depend on. Must be complete before any UI work can be tested end-to-end.

**⚠️ CRITICAL**: No user story can be tested against the live app until T002–T004 are complete.

- [X] T002 Register `exam_bp` Blueprint in `python_bridge/server.py` — import `from exam import exam_bp` and call `app.register_blueprint(exam_bp)` before `app.run()`

- [X] T003 Modify `frontend/main.js`:
  - Add `let examSession = null;` as a module-scope variable (alongside existing `sessionMemory`)
  - Add `ipcMain.handle('bridge:start-exam', async (event, { quizCode }) => { ... })` handler: read `accessToken` from `sessionMemory?.token` or via `keytar.getPassword(KEYTAR_SERVICE, 'access-token')`; POST `{ quizCode, token }` to `http://127.0.0.1:${bridgePort}/exam-access`; on HTTP 200 store the response JSON in `examSession` and return `{ ok: true, data: examSession }`; on error return `{ ok: false, error: responseBody }`
  - Add `ipcMain.handle('bridge:get-exam-session', async () => examSession ? { ok: true, session: examSession } : { ok: false })` handler

- [X] T004 [P] Modify `frontend/preload.js`:
  - Add `'bridge:start-exam'` and `'bridge:get-exam-session'` to the `ALLOWED_INVOKE_CHANNELS` array
  - Expose `startExam: (quizCode) => ipcRenderer.invoke('bridge:start-exam', { quizCode })` on `window.bridge`
  - Expose `getExamSession: () => ipcRenderer.invoke('bridge:get-exam-session')` on `window.bridge`

**Checkpoint**: Start the app; Python bridge starts; `window.bridge.startExam` and `window.bridge.getExamSession` are callable from DevTools; exam-code page loads (still shows placeholder HTML).

---

## Phase 3: User Story 1 — Enter Exam Code and Start Exam (Priority: P1) 🎯 MVP

**Goal**: A student can type a valid exam code, click "Join Exam", see a loading state, and navigate to the Exam page with full exam data (attemptId, title, duration, questions) available.

**Independent Test**: Open the app (logged-in session), enter a valid exam code, click Join Exam — app transitions to Exam page with the correct exam title. Verify loading state appears during the request and disappears on navigation.

### Implementation for User Story 1

- [X] T005 [P] [US1] Replace placeholder `frontend/pages/exam-code/index.html` with the full Ethereal Authority Exam Access page matching `Designs/Exam_Code_Page/screen.png`:
  - Page shell: `<!DOCTYPE html>`, charset, viewport, link to `../../styles/design-tokens.css`, link to `exam-code.css`, script defer `exam-code.js`
  - Background: gradient wrapper `<div class="page-background">` using `--gradient-primary`
  - Central white card `<div class="exam-card">` with `--radius-xl` and `--shadow-ambient`
  - Lock icon: `<div class="icon-container">` with SVG lock icon, background `--color-primary-fixed`, color `--color-primary`
  - Wordmark: `<p class="wordmark">Lumina AI</p>` in `--color-primary` (Manrope)
  - Headline: `<h1 class="headline">Secure Exam Access</h1>` (Manrope, 28px, `--color-on-surface`)
  - Subtitle: `<p class="subtitle">Enter your exam code to begin your secure session</p>` (`--color-on-surface-variant`)
  - Student name bar: `<div class="student-bar"><span class="student-name" id="studentName">Loading…</span><button class="logout-btn" id="logoutBtn">Log out</button></div>`
  - Form: `<form id="examForm"><div class="input-group"><label for="examCode">EXAM CODE</label><div class="input-wrapper"><svg class="input-icon"><!-- key icon --></svg><input type="text" id="examCode" name="examCode" placeholder="e.g. EXAM-2026" autocomplete="off" spellcheck="false"></div><p class="error-message" id="errorMessage" aria-live="polite"></p></div><button type="submit" id="submitBtn" class="btn-primary"><span id="btnText">JOIN EXAM</span><svg id="btnArrow" class="btn-arrow"><!-- arrow icon --></svg><svg id="btnSpinner" class="btn-spinner hidden"><!-- spinner --></svg></button></form>`
  - Status chips: `<div class="chips"><span class="chip">🔒 ENCRYPTED FEED</span><span class="chip">👁 AI MONITORING</span></div>`
  - Footer: `<p class="footer-text">Having trouble? <a href="#" id="helpLink">Contact support</a></p>`

- [X] T006 [P] [US1] Create `frontend/pages/exam-code/exam-code.css` with full Ethereal Authority styles:
  - `.page-background`: `min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--gradient-primary)`
  - `.exam-card`: `background: var(--color-surface-container-lowest); border-radius: var(--radius-xl); box-shadow: var(--shadow-ambient); padding: 48px 40px; max-width: 420px; width: 100%; text-align: center`
  - `.icon-container`: `width: 72px; height: 72px; border-radius: 50%; background: var(--color-primary-fixed); color: var(--color-primary); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px`
  - `.wordmark`: `font-family: var(--font-brand); font-size: 14px; font-weight: 700; color: var(--color-primary); letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 8px`
  - `.headline`: `font-family: var(--font-brand); font-size: 28px; font-weight: 700; color: var(--color-on-surface); margin-bottom: 8px`
  - `.subtitle`: `font-size: 14px; color: var(--color-on-surface-variant); margin-bottom: 24px`
  - `.student-bar`: `display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: var(--color-surface-container-low); border-radius: var(--radius-default); margin-bottom: 24px`
  - `.student-name`: `font-size: 14px; color: var(--color-on-surface); font-family: var(--font-body)`
  - `.logout-btn`: `font-size: 12px; color: var(--color-primary); background: none; border: none; cursor: pointer; font-family: var(--font-body); padding: 0`
  - `label`: `display: block; text-align: left; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-on-surface-variant); margin-bottom: 8px; font-family: var(--font-body)`
  - `.input-wrapper`: `position: relative`
  - `.input-icon`: `position: absolute; left: 16px; top: 50%; transform: translateY(-50%); color: var(--color-outline-variant); width: 18px; height: 18px`
  - `input`: `width: 100%; padding: 14px 16px 14px 44px; background: var(--color-surface-container-low); border: none; border-radius: var(--radius-default); font-size: 16px; color: var(--color-on-surface); font-family: var(--font-body); box-sizing: border-box; outline: 2px solid transparent; transition: outline-color 0.15s`
  - `input:focus`: `outline-color: var(--color-primary)`
  - `.error-message`: `font-size: 13px; color: var(--color-error); text-align: left; margin-top: 6px; min-height: 18px; font-family: var(--font-body)`
  - `.btn-primary`: `width: 100%; padding: 16px; background: var(--gradient-primary); color: var(--color-on-primary); border: none; border-radius: var(--radius-button); font-size: 15px; font-weight: 700; letter-spacing: 0.05em; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 20px; font-family: var(--font-brand); transition: opacity 0.15s`
  - `.btn-primary:disabled`: `opacity: 0.6; cursor: not-allowed`
  - `.btn-spinner, .hidden`: `display: none`
  - `.btn-spinner.visible`: `display: inline-block; width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite`
  - `@keyframes spin`: `to { transform: rotate(360deg) }`
  - `.chips`: `display: flex; gap: 8px; justify-content: center; margin-top: 24px; flex-wrap: wrap`
  - `.chip`: `font-size: 11px; font-weight: 600; letter-spacing: 0.06em; padding: 6px 12px; border-radius: var(--radius-chip); background: var(--color-secondary-container); color: var(--color-on-secondary-container); font-family: var(--font-body)`
  - `.footer-text`: `font-size: 12px; color: var(--color-on-surface-variant); margin-top: 16px`
  - `.footer-text a`: `color: var(--color-primary); text-decoration: none`

- [X] T007 [P] [US1] Implement full `POST /exam-access` route in `python_bridge/exam.py` (replace the 501 stub from T001):
  - Parse `quizCode` and `token` from `request.get_json()`; return 400 `BRIDGE_ERROR` if either is missing/blank
  - Read `base_url` from `current_app.config['BASE_URL']`
  - Call `requests.get(f"{base_url}/api/QuizAttempts/attempt/{quizCode}", headers={"Authorization": f"Bearer {token}"}, timeout=15, verify=False)`
  - On HTTP 200: return `jsonify(response.json()), 200`
  - On HTTP 404/409/401: delegate to `map_lms_exam_error(response.status_code)` (stub returns generic BRIDGE_ERROR for now — full map added in T009)
  - On `requests.exceptions.RequestException`: return `jsonify({"code": "BRIDGE_ERROR", "message": "Unable to reach the server. Please check your connection and try again."}), 503`
  - **Security**: `token` is never logged, never echoed in any response, used only for the Authorization header

- [X] T008 [US1] Create `frontend/pages/exam-code/exam-code.js` with full form controller (happy path + timeout):
  - `DOMContentLoaded` handler: get references to `#examCode`, `#submitBtn`, `#btnText`, `#btnArrow`, `#btnSpinner`, `#errorMessage`, `#examForm`
  - `function setLoading(bool)`: `submitBtn.disabled = bool; examCode.disabled = bool; btnSpinner.classList.toggle('visible', bool); btnSpinner.classList.toggle('hidden', !bool); btnArrow.classList.toggle('hidden', bool); btnText.textContent = bool ? 'Checking…' : 'JOIN EXAM'`
  - `function clearError()`: `errorMessage.textContent = ''`
  - `examCode.addEventListener('input', clearError)`
  - `#examForm submit` handler:
    - Call `event.preventDefault()`
    - Trim `quizCode = examCode.value.trim()` (FR-002)
    - If empty: set `errorMessage.textContent = 'Please enter your exam code.'` and return (FR-003)
    - Call `setLoading(true)` (FR-004)
    - Build `Promise.race` between `window.bridge.startExam(quizCode)` and a 15-second timeout promise that resolves to `{ ok: false, timeout: true }` (FR-012, research Decision 4)
    - On resolved result:
      - If `result.ok === true`: store nothing in renderer; call `window.location.href = '../exam/index.html'` (FR-006) — examSession is already stored in main.js
      - If `result.timeout === true`: call `setLoading(false)`; set `errorMessage.textContent = ERROR_MESSAGES.BRIDGE_ERROR`
      - If `result.ok === false`: handle errors via `showError(result.error)` and `setLoading(false)` (error display added in T010)

**Checkpoint**: Enter a valid exam code with a live session → loading state appears → app transitions to Exam page. App does not navigate on empty submit. 15-second timeout resolves with an error if the call stalls.

---

## Phase 4: User Story 2 — Receive Clear Error Feedback (Priority: P2)

**Goal**: Every failure path (code not found, already attempted, expired token, network failure) shows a specific, sanitised error message. Input is re-enabled with value preserved; error clears on keystroke.

**Independent Test**: Submit an invalid code (mocked via bridge returning EXAM_NOT_FOUND) — correct message displayed, input re-enabled, error clears when typing begins again. Test all 4 error codes.

### Implementation for User Story 2

- [X] T009 [P] [US2] Implement `map_lms_exam_error(status_code)` in `python_bridge/exam.py` and wire into the route from T007:
  - `404` → `({"code": "EXAM_NOT_FOUND", "message": "Exam code not found. Please check the code and try again."}, 404)`
  - `409` → `({"code": "ALREADY_ATTEMPTED", "message": "You have already attempted this exam."}, 409)`
  - `401` → `({"code": "UNAUTHORIZED", "message": "Your session has expired. Please log in again."}, 401)`
  - Any other LMS error → `({"code": "BRIDGE_ERROR", "message": "Unable to reach the server. Please check your connection and try again."}, 503)`
  - Replace the stub call in T007's route with the real `map_lms_exam_error(response.status_code)` call

- [X] T010 [US2] Add error display and recovery to `frontend/pages/exam-code/exam-code.js`:
  - Add `const ERROR_MESSAGES = { EXAM_NOT_FOUND: 'Exam code not found. Please check the code and try again.', ALREADY_ATTEMPTED: 'You have already attempted this exam.', BRIDGE_ERROR: 'Unable to reach the server. Please check your connection and try again.' }` at the top of the file
  - Add `function showError(err)`: `errorMessage.textContent = ERROR_MESSAGES[err?.code] ?? ERROR_MESSAGES.BRIDGE_ERROR` (FR-007; no raw LMS text ever rendered)
  - Update the `result.ok === false` branch in T008's submit handler to call `showError(result.error)` and `setLoading(false)` — input re-enabled by `setLoading(false)`, value preserved (input was not cleared), error clears on keystroke via existing `clearError` listener (FR-007 complete)

- [X] T011 [P] [US2] Add UNAUTHORIZED redirect logic to `frontend/main.js` `bridge:start-exam` handler (FR-008):
  - After receiving the bridge response, check `if (data?.code === 'UNAUTHORIZED')`: call `await clearAllKeytarEntries()`; then call `mainWindow.loadFile(path.join(__dirname, 'pages', 'login', 'index.html'))` and return without resolving the IPC invoke
  - This shadows the UNAUTHORIZED case entirely from the renderer — the IPC call effectively hangs (the page navigated away), which is the correct UX (silent redirect)

**Checkpoint**: Submit codes that map to EXAM_NOT_FOUND and ALREADY_ATTEMPTED — correct messages appear. Submit with an expired token — app silently redirects to Login. All 4 error scenarios in `specs/003-exam-access-page/mocks/` are handled.

---

## Phase 5: User Story 3 — Log Out from Exam Access Page (Priority: P3)

**Goal**: A student can log out from the Exam Access page, clearing their session and returning to the Login page.

**Independent Test**: Click logout → session cleared (keytar entries gone) → Login page loads.

### Implementation for User Story 3

- [X] T012 [P] [US3] Update `frontend/pages/exam-code/index.html` to refine the student bar added in T005:
  - Ensure `<span id="studentName">Loading…</span>` is present with a `data-placeholder` attribute for the pre-reveal state
  - Ensure `<button id="logoutBtn" type="button" class="logout-btn">Log out</button>` is present and has `type="button"` to prevent accidental form submission

- [X] T013 [US3] Add logout handler to `frontend/pages/exam-code/exam-code.js` (FR-010):
  - `document.getElementById('logoutBtn').addEventListener('click', async () => { await window.bridge.clearSession(); window.location.href = '../login/index.html'; })`

- [X] T014 [US3] Add page-init student name reveal to `frontend/pages/exam-code/exam-code.js` (FR-009):
  - Immediately after `DOMContentLoaded`, call `window.bridge.getSavedSession()` asynchronously (do not await before making the form interactive — FR-009 requires form is usable immediately)
  - In the `.then()` callback: if result has `firstName`, update `document.getElementById('studentName').textContent = result.firstName`; otherwise set to `'Student'` as a safe fallback
  - The `Loading…` placeholder text (set in T005 HTML) is shown while the keychain read is in progress

**Checkpoint**: Page loads → "Loading…" shown briefly → student's first name appears. Click Log out → Login page opens.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Visual polish pass, spinner consistency, and final integration smoke test.

- [X] T015 [P] Verify `frontend/pages/exam-code/exam-code.css` spinner animation matches Login page pattern: confirm `@keyframes spin`, `.btn-spinner`, `.hidden`/`.visible` toggle classes are consistent with `frontend/pages/login/login.css` — adjust if inconsistent

- [X] T016 Final smoke test against `specs/003-exam-access-page/quickstart.md`:
  - Verify scenario 1 (valid code → Exam page with title/duration/questions)
  - Verify scenario 2 (invalid code → EXAM_NOT_FOUND message, input re-enabled)
  - Verify scenario 3 (logout → Login page)
  - Verify 15-second timeout resolves with BRIDGE_ERROR message
  - Verify empty-code submit shows inline validation

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends On | Can Start When |
|-------|-----------|---------------|
| Phase 1 (Setup) | Nothing | Immediately |
| Phase 2 (Foundational) | Phase 1 complete | T001 done |
| Phase 3 (US1) | Phase 2 complete | T002, T003, T004 done |
| Phase 4 (US2) | Phase 3 complete | T005–T008 done |
| Phase 5 (US3) | Phase 3 complete | T005 done (T012 needs index.html) |
| Phase 6 (Polish) | Phase 4 + Phase 5 complete | T009–T014 done |

### User Story Dependencies

| Story | Requires | Independent From |
|-------|----------|-----------------|
| **US1 (P1)** | Foundation (T002–T004) | US2, US3 |
| **US2 (P2)** | US1 complete (T005–T008) | US3 |
| **US3 (P3)** | index.html exists (T005) | US2 (error handling) |

### Within Each Story

- T005, T006, T007 (Phase 3) are all [P] — all 3 can start simultaneously (different files)
- T008 (Phase 3) depends on T005 (needs HTML IDs) + T006 (needs CSS classes) + T007 (needs bridge route)
- T009 and T011 (Phase 4) are [P] — different files (exam.py / main.js), can start simultaneously
- T010 (Phase 4) is sequential after T008 (adds to exam-code.js)
- T012 (Phase 5) is [P] — modifies index.html (different from exam-code.js that T013/T014 modify)
- T013 and T014 are sequential (both add to exam-code.js)

---

## Parallel Execution Examples

### Phase 3 — US1 (recommended: 3-worker parallel start)

```
Worker A: T005 — index.html
Worker B: T006 — exam-code.css
Worker C: T007 — exam.py POST /exam-access route
  ↓ all complete
Worker A: T008 — exam-code.js (happy path + timeout)
```

### Phase 4 — US2 (2-worker parallel)

```
Worker A: T009 — map_lms_exam_error() in exam.py
Worker B: T011 — UNAUTHORIZED redirect in main.js
  ↓ both complete
Worker A: T010 — error display in exam-code.js
```

### Phase 5 — US3 (2-worker parallel start)

```
Worker A: T012 — update index.html (logout button + name placeholder)
Worker B: T013 — logout handler in exam-code.js
  ↓ T013 complete
Worker B: T014 — page-init name reveal in exam-code.js
```

---

## Implementation Strategy

**MVP Scope (Phase 1–3 only, US1 alone)**: After T001–T008 a student can enter a valid exam code and navigate to the Exam page. This is a shippable increment — the happy path is complete.

**Priority order if working sequentially**: T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016

**Files modified per task**:

| Task | File | Action |
|------|------|--------|
| T001 | `python_bridge/exam.py` | CREATE |
| T002 | `python_bridge/server.py` | MODIFY |
| T003 | `frontend/main.js` | MODIFY |
| T004 | `frontend/preload.js` | MODIFY |
| T005 | `frontend/pages/exam-code/index.html` | REPLACE |
| T006 | `frontend/pages/exam-code/exam-code.css` | CREATE |
| T007 | `python_bridge/exam.py` | MODIFY |
| T008 | `frontend/pages/exam-code/exam-code.js` | CREATE |
| T009 | `python_bridge/exam.py` | MODIFY |
| T010 | `frontend/pages/exam-code/exam-code.js` | MODIFY |
| T011 | `frontend/main.js` | MODIFY |
| T012 | `frontend/pages/exam-code/index.html` | MODIFY |
| T013 | `frontend/pages/exam-code/exam-code.js` | MODIFY |
| T014 | `frontend/pages/exam-code/exam-code.js` | MODIFY |
| T015 | `frontend/pages/exam-code/exam-code.css` | VERIFY |
| T016 | (smoke test) | VERIFY |
