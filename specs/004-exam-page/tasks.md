# Tasks: Exam Page

**Input**: Design documents from `/specs/004-exam-page/`
**Prerequisites**: plan.md âœ…, spec.md âœ…, research.md âœ…, data-model.md âœ…, contracts/ âœ…, quickstart.md âœ…

**Feature**: `004-exam-page`
**Branch**: `004-exam-page`
**Date**: 2026-04-16
**Tests**: Not requested â€” implementation tasks only.

---

## Format: `[ID] [P?] [Story?] Description â€” file/path`

- **[P]**: Can run in parallel with other [P] tasks in the same phase (operates on a different file)
- **[Story]**: Which user story this task belongs to (US1=P1, US2=P1, US3=P2, US4=P2, US5=P3, US6=P3)
- Every task includes the exact file path that must be modified or created

---

## Phase 1: Setup (File Scaffolding)

**Purpose**: Create the three new source files and the result page placeholder so imports and file references don't break as later tasks fill in content. All tasks are parallel.

- [x] T001 [P] Create `frontend/pages/exam/exam.css` â€” empty file with a top comment `/* exam.css â€” Exam Page Styles â€” spec 004 */`; no content yet (styles added per phase)

- [x] T002 [P] Create `frontend/pages/exam/exam.js` â€” empty module scaffold: `'use strict';` + top-level `const` declarations for all module-scope variables as `null` or empty literals: `let currentIndex = 0; let examSession = null; let answerMap = {}; const flagSet = new Set(); let activeStream = null; let timerInterval = null; let timerStartTime = null; let timerTotalSeconds = 0; let isSubmitting = false; let autoSubmitted = false;` â€” no logic yet

- [x] T003 [P] Create `frontend/pages/result/index.html` â€” empty result page placeholder matching the same shell pattern used by `frontend/pages/loading/loading.html`: `<!DOCTYPE html>`, charset, viewport, CSP meta, title "Result â€” Lumina AI", link to `../../assets/components.css`, empty `<body>` with comment `<!-- Placeholder: spec 005-result-page will implement this page -->`

**Checkpoint**: All three new files exist; `npm start` still launches without errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire the complete IPC plumbing (`main.js` + `preload.js`) and the Python bridge submit route that all submit-related user stories (US3) depend on. Must be complete before US3 can be tested end-to-end. US1, US2, US4, US5 can be built in parallel with this phase since they don't invoke `bridge:submit-exam`.

**âš ï¸ CRITICAL**: US3 cannot be tested at all until T004â€“T008 are complete.

- [x] T004 Modify `python_bridge/exam.py` â€” add `map_lms_submit_error(status_code)` function immediately after the existing `map_lms_exam_error()` function:
  ```python
  def map_lms_submit_error(status_code: int):
      if status_code == 401:
          return {"code": "UNAUTHORIZED",   "message": "Your session has expired. Please log in again."}, 401
      if status_code == 404:
          return {"code": "EXAM_NOT_FOUND", "message": "This exam could not be found. Please contact your instructor."}, 404
      return     {"code": "BRIDGE_ERROR",   "message": "Unable to reach the server. Please check your connection and try again."}, 503
  ```

- [x] T005 Modify `python_bridge/exam.py` â€” add `POST /submit-exam` route at the end of the file (after the existing `/exam-access` route):
  - Read `attemptId`, `answers`, `token` from request body via `request.get_json(silent=True) or {}`
  - Validate `attemptId` is a positive integer; if not, return 400 with `map_lms_submit_error(400)[0]` (the BRIDGE_ERROR shape)
  - Call `requests.post(f"{base_url}/api/QuizAttempts/submit/{attempt_id}", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"answers": answers}, timeout=10, verify=False)` inside a `try/except requests.exceptions.RequestException`
  - On `response.status_code == 200`: return `jsonify(response.json()), 200`
  - On any other status or exception: return `jsonify(error_body), error_status` from `map_lms_submit_error()`
  - The `token` value MUST NOT appear in any log statement, error response, or exception message

- [x] T006 [P] Modify `frontend/preload.js` â€” two changes:
  1. Add `'bridge:submit-exam'` and `'bridge:get-submit-result'` to the `ALLOWED_INVOKE_CHANNELS` array (alongside existing `'bridge:get-exam-session'`)
  2. Add two methods to the `contextBridge.exposeInMainWorld('bridge', { ... })` object after the existing `getExamSession()`:
     ```js
     submitExam(answers) {
       return ipcRenderer.invoke('bridge:submit-exam', { answers });
     },
     getSubmitResult() {
       return ipcRenderer.invoke('bridge:get-submit-result');
     },
     ```

- [x] T007 Modify `frontend/main.js` â€” add `let submitResult = null;` as a new module-scope variable directly after the `let examSession = null;` declaration (line ~47), with JSDoc: `/** Graded result stored after a successful exam submission. Retrieved by spec 005 via bridge:get-submit-result. @type {object | null} */`

- [x] T008 Modify `frontend/main.js` â€” add two new IPC handlers in a new `// Exam submission IPC handlers (spec 004)` section immediately after the existing `bridge:get-exam-session` handler (around line 436):

  **Handler 1 â€” `bridge:submit-exam`**:
  ```js
  ipcMain.handle('bridge:submit-exam', async (_event, { answers }) => {
    try {
      const accessToken =
        sessionMemory?.accessToken ||
        (await keytar.getPassword(KEYTAR_SERVICE, 'access-token'));
      const attemptId = examSession?.attemptId;

      const response = await net.fetch(`http://127.0.0.1:${bridgePort}/submit-exam`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attemptId, answers, token: accessToken }),
      });

      const body = await response.json();

      if (response.ok) {
        submitResult = body;
        examSession = null;
        return { ok: true, data: submitResult };
      }

      if (body?.code === 'UNAUTHORIZED') {
        await clearAllKeytarEntries();
        sessionMemory = null;
        mainWindow?.loadFile(path.join(__dirname, 'pages/login/index.html'));
        return; // renderer IPC call never resolves â€” main.js navigates away
      }

      return { ok: false, error: body };
    } catch (_err) {
      return {
        ok: false,
        error: { code: 'BRIDGE_ERROR', message: 'Unable to reach the server. Please check your connection and try again.' },
      };
    }
  });
  ```

  **Handler 2 â€” `bridge:get-submit-result`**:
  ```js
  ipcMain.handle('bridge:get-submit-result', async () => {
    if (submitResult) return { ok: true, result: submitResult };
    return { ok: false };
  });
  ```

**Checkpoint**: Start the app; `window.bridge.submitExam` and `window.bridge.getSubmitResult` are callable from Electron DevTools console; `curl -X POST http://127.0.0.1:5050/submit-exam -H 'Content-Type: application/json' -d '{"attemptId":-1,"answers":[],"token":"t"}'` returns HTTP 400 BRIDGE_ERROR.

---

## Phase 3: User Story 1 â€” Load and Browse Questions (Priority: P1) ðŸŽ¯ MVP

**Goal**: A student lands on the Exam page, sees a loading skeleton while IPC resolves, then sees the first question with all choices rendered, and can navigate between questions via Prev/Next buttons, navigator pills, and the "Jump to" input. If no session is found, they are redirected to Login.

**Independent Test**: Inject `exam-session.json` mock into main.js `examSession`; open `frontend/pages/exam/index.html`; verify skeleton shows briefly then disappears; verify exam title in header; verify question 1 text and 4 lettered choices; click Next â†’ question 2 shown, badge updates; click a navigator pill â†’ jumps to that question; Prev on question 1 is disabled; Next on last question is disabled; type "5" in Jump to + Enter â†’ navigates to question 5; type "999" + Enter â†’ cleared with no navigation.

### Implementation for User Story 1

- [x] T009 [US1] Replace `frontend/pages/exam/index.html` content â€” write the full Ethereal Authority Exam page HTML structure using only semantic elements and `var(--token)` CSS references. Must include all of the following sections (no content logic, no JS â€” structure only):
  - `<head>`: charset, viewport, CSP meta (`default-src 'self'; style-src 'self'; script-src 'self'; font-src 'self' data:;`), title "Exam â€” Lumina AI", link `../../assets/design-tokens.css`, link `../../assets/components.css`, link `./exam.css`, script `defer src="./exam.js"`
  - **Loading skeleton overlay** (visible by default, hidden after IPC resolves): `<div class="skeleton-overlay" id="skeletonOverlay"><div class="skeleton-spinner"></div></div>`
  - **Fixed header** (`<header class="exam-header" id="examHeader">`): left side â€” `<h1 class="exam-title" id="examTitle">Loadingâ€¦</h1>`; centre â€” timer chip `<div class="timer-chip" id="timerChip"><span id="timerDisplay">--:--:--</span></div>`; right side â€” `<button class="btn btn-submit-exam" id="submitExamBtn">Submit Exam</button>`
  - **Main layout** (`<main class="exam-layout">`): question panel (`<section class="question-panel">`) + proctoring aside (`<aside class="proctoring-panel" id="proctoringPanel">`)
  - **Question panel** contents: question badge `<div class="question-badge" id="questionBadge">Question 1 of N</div>`, question text `<p class="question-text" id="questionText"></p>`, choices list `<ul class="choices-list" id="choicesList">` (populated by JS), flag button `<button class="flag-btn" id="flagBtn" aria-label="Flag this question">` with SVG flag icon
  - **Proctoring aside** contents: webcam section with `<video class="webcam-feed" id="webcamFeed" autoplay muted playsinline></video>`, LIVE badge `<span class="live-badge">LIVE FEED</span>`, camera-unavailable fallback `<div class="camera-unavailable hidden" id="cameraUnavailable">Camera unavailable</div>`, then 5 static AI status rows: Face Detection (Active), Eye Tracking (Active), Object Detection (Active), Face Anti-Spoofing (Active), Multiple Faces (Inactive)
  - **Bottom navigator bar** (`<nav class="exam-navigator" id="examNavigator">`): scroll area of pills `<div class="pills-container" id="pillsContainer">` (populated by JS), jump-to group `<div class="jump-to-group"><label for="jumpInput">Jump to</label><input type="number" id="jumpInput" min="1" class="jump-input" /></div>`, Prev/Next buttons `<button id="prevBtn" class="btn btn-nav">â† Previous</button>` and `<button id="nextBtn" class="btn btn-nav">Next Question â†’</button>`
  - **Confirmation modal** (hidden by default): `<div class="modal-backdrop hidden" id="modalBackdrop"><div class="modal-glass"><h2 id="modalTitle"></h2><p id="modalMessage"></p><div class="modal-actions"><button class="btn btn-secondary" id="modalCancelBtn">Cancel</button><button class="btn btn-primary" id="modalConfirmBtn">Submit</button></div></div></div>`
  - **Error banner** (hidden by default): `<div class="error-banner hidden" id="errorBanner"><span id="errorBannerText"></span><button class="btn btn-retry" id="retryBtn">Retry</button></div>`

- [x] T010 [P] [US1] Implement `exam.css` â€” layout and skeleton styles:
  - Reset: `*, *::before, *::after { box-sizing: border-box; }` and `body { margin: 0; font-family: var(--font-body); background: var(--color-surface); color: var(--color-on-surface); }`
  - **Skeleton overlay**: `.skeleton-overlay { position: fixed; inset: 0; z-index: 999; background: var(--color-surface); display: flex; align-items: center; justify-content: center; }` â€” `.skeleton-overlay.hidden { display: none; }` â€” `.skeleton-spinner { width: 48px; height: 48px; border: 4px solid var(--color-surface-container-high); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }` â€” `@keyframes spin { to { transform: rotate(360deg); } }`
  - **Fixed header**: `.exam-header { position: fixed; top: 0; left: 0; right: 0; height: 64px; background: var(--color-surface-container-lowest); display: flex; align-items: center; justify-content: space-between; padding: 0 24px; z-index: 100; border-bottom: 1px solid rgba(0,0,0,0.06); }` â€” `.exam-title { font-family: var(--font-display); font-size: 18px; font-weight: 700; color: var(--color-on-surface); margin: 0; max-width: 360px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }`
  - **Layout grid**: `.exam-layout { display: grid; grid-template-columns: 1fr 320px; gap: 24px; margin-top: 64px; padding: 24px; min-height: calc(100vh - 64px - 72px); }` (72px = bottom nav height)
  - **Question panel**: `.question-panel { background: var(--color-surface-container-lowest); border-radius: var(--radius-card, 16px); padding: 32px; border: 1px solid rgba(var(--color-outline-rgb, 0,0,0), 0.08); }`
  - **Proctoring aside**: `.proctoring-panel { background: var(--color-surface-container-low); border-radius: var(--radius-card, 16px); padding: 20px; border: 1px solid rgba(var(--color-outline-rgb, 0,0,0), 0.08); display: flex; flex-direction: column; gap: 12px; }`
  - **Bottom navigator**: `.exam-navigator { position: fixed; bottom: 0; left: 0; right: 0; height: 72px; background: var(--color-surface-container-lowest); display: flex; align-items: center; gap: 16px; padding: 0 24px; border-top: 1px solid rgba(0,0,0,0.06); z-index: 100; }` â€” `.pills-container { display: flex; gap: 6px; overflow-x: auto; flex: 1; padding: 4px 0; scrollbar-width: thin; }` â€” `.jump-to-group { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--color-on-surface-variant); }` â€” `.jump-input { width: 56px; padding: 6px 8px; border: 1px solid var(--color-outline-variant); border-radius: var(--radius-chip, 8px); font-size: 13px; text-align: center; background: var(--color-surface); color: var(--color-on-surface); }`

- [x] T011 [P] [US1] Implement `exam.css` â€” question area, badge, choice list, and flag button styles:
  - `.question-badge { display: inline-flex; align-items: center; padding: 4px 12px; background: var(--color-primary-fixed, #d0e9f0); color: var(--color-on-primary-fixed-variant, var(--color-primary)); border-radius: var(--radius-chip, 8px); font-size: 12px; font-weight: 600; letter-spacing: 0.04em; margin-bottom: 16px; }`
  - `.question-text { font-family: var(--font-display); font-size: 18px; font-weight: 600; color: var(--color-on-surface); line-height: 1.5; margin: 0 0 24px; }`
  - `.choices-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }`
  - `.choice-item { display: flex; align-items: center; gap: 16px; padding: 16px; background: var(--color-surface-container-lowest); border: 1.5px solid var(--color-outline-variant); border-radius: var(--radius-card, 16px); cursor: pointer; transition: border-color 0.15s, background 0.15s; }`
  - `.choice-item:hover { border-color: var(--color-primary); background: var(--color-surface-container-low); }`
  - `.choice-item.is-selected { border-color: var(--color-primary); border-width: 2px; background: var(--color-surface-container-low); }`
  - `.choice-letter { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; background: var(--color-surface-container-high); color: var(--color-on-surface-variant); flex-shrink: 0; transition: background 0.15s, color 0.15s; }`
  - `.choice-item.is-selected .choice-letter { background: var(--color-primary); color: #fff; }`
  - `.choice-text { font-size: 15px; color: var(--color-on-surface); line-height: 1.4; }`
  - `.flag-btn { margin-top: 20px; background: none; border: none; cursor: pointer; color: var(--color-on-surface-variant); padding: 8px; border-radius: var(--radius-chip, 8px); display: flex; align-items: center; gap: 6px; font-size: 13px; transition: color 0.15s; }`
  - `.flag-btn:hover { color: var(--color-tertiary); }`
  - `.flag-btn.is-flagged { color: var(--color-tertiary); }`

- [x] T012 [US1] Implement `exam.js` â€” `DOMContentLoaded` handler: call `window.bridge.getExamSession()`; on `{ ok: false }` navigate to Login with `window.location.replace('../login/index.html')`; on `{ ok: true, session }` assign `examSession = session`, parse `timerTotalSeconds` from `session.duration` (split `HH:mm:ss`, compute `h*3600 + m*60 + s`), call `initPage()` to populate title + question count + pills, call `renderQuestion(0)`, call `startTimer()`, call `initWebcam()`, then hide skeleton by adding `hidden` class to `#skeletonOverlay`

- [x] T013 [US1] Implement `exam.js` â€” `renderQuestion(index)` function: update `#questionBadge` text to "Question X of N"; set `#questionText` to `examSession.questions[index].questionText`; clear and rebuild `#choicesList` â€” for each choice, create `<li class="choice-item" data-question-id="..." data-choice-id="...">` with letter label `<span class="choice-letter">A/B/Câ€¦</span>` and `<span class="choice-text">...</span>`; if `answerMap[questionId] === choiceId`, add `is-selected` class; attach click handler on each `<li>`; update `#prevBtn` disabled state (index === 0); update `#nextBtn` disabled state (index === totalQuestions - 1); update `#flagBtn` active state from `flagSet.has(questionId)`; call `updatePillStates()`

- [x] T014 [US1] Implement `exam.js` â€” navigator pill generation in `initPage()`: create one `<button class="nav-pill" data-index="...">` per question inside `#pillsContainer`; each button shows `index + 1` as its label; wire click handler to call `renderQuestion(index)` and update `currentIndex`

- [x] T015 [US1] Implement `exam.js` â€” `updatePillStates()` function: iterate all `.nav-pill` buttons; remove state classes `is-answered`, `is-current`, `is-flagged`; for each pill whose question index matches a key in `answerMap` add `is-answered`; for the pill at `currentIndex` add `is-current`; for questions in `flagSet` add `is-flagged` (flagged takes priority â€” applied last, overwrites answered)

- [x] T016 [P] [US1] Implement `exam.css` â€” navigator pill state styles:
  - `.nav-pill { width: 36px; height: 36px; border-radius: 50%; border: none; background: var(--color-surface-container-high); color: var(--color-on-surface-variant); font-size: 12px; font-weight: 600; cursor: pointer; flex-shrink: 0; transition: background 0.15s, color 0.15s, box-shadow 0.15s; }`
  - `.nav-pill.is-answered { background: var(--color-primary); color: #fff; }`
  - `.nav-pill.is-current { background: var(--color-primary); color: #fff; box-shadow: 0 0 0 3px rgba(0,102,135,0.25); }`
  - `.nav-pill.is-flagged { background: var(--color-tertiary); color: #fff; }`

- [x] T017 [US1] Implement `exam.js` â€” Prev/Next button click handlers: `#prevBtn` on click â€” if `currentIndex > 0`, decrement `currentIndex`, call `renderQuestion(currentIndex)`; `#nextBtn` on click â€” if `currentIndex < totalQuestions - 1`, increment `currentIndex`, call `renderQuestion(currentIndex)`

- [x] T018 [US1] Implement `exam.js` â€” "Jump to" input handler: on `keydown` event for `#jumpInput`, if `event.key === 'Enter'`, parse `parseInt(input.value, 10)` â€” if result is in range [1, totalQuestions], set `currentIndex = result - 1`, call `renderQuestion(currentIndex)`, clear input; otherwise clear input and re-focus it

**Checkpoint US1**: Inject `mocks/exam-session.json` into main.js `examSession`; open the Exam page; skeleton shows then hides; exam title renders in header; question 1 text and 4 lettered choices visible; Prev disabled; click Next â†’ question 2; click pill 5 â†’ question 5; type "3" in Jump-to â†’ question 3; type "999" â†’ no navigation and field is cleared; Last question Next button is disabled.

---

## Phase 4: User Story 2 â€” Select and Change Answers (Priority: P1) ðŸŽ¯ MVP

**Goal**: A student can click a choice, see it visually selected, navigate away and return to find the selection persisted, and change their answer at any time. Navigator pills reflect answered state.

**Independent Test**: On question 1 select choice B â†’ pill turns primary; navigate to question 2; navigate back to question 1 â†’ choice B still selected; click choice C â†’ C selected, B deselected; verify `answerMap` in DevTools console shows `{ [101]: <choiceId-of-C> }`.

### Implementation for User Story 2

- [x] T019 [US2] Implement `exam.js` â€” choice click handler (wire inside `renderQuestion()`): on `<li class="choice-item">` click, read `dataset.questionId` and `dataset.choiceId`; update `answerMap[+questionId] = +choiceId`; remove `is-selected` from all sibling `<li>` items; add `is-selected` to the clicked `<li>`; update the letter circle colours; call `updatePillStates()` to mark the pill as answered

**Checkpoint US2**: Answers survive Prev/Next navigation; answerMap in console shows all selected choices; changing selection replaces the old entry.

---

## Phase 5: User Story 3 â€” Submit Exam (Priority: P2)

**Goal**: A student can manually submit via confirmation modal or be auto-submitted by the timer. The submit call goes to the bridge, loading state is applied, on success the result page is loaded, on failure the error is shown with a Retry button (timer resumes if manual-submit failure; timer stays frozen if auto-submit failure).

**Independent Test**: (a) Click Submit Exam â†’ modal appears with correct unanswered count â†’ Cancel â†’ exam resumes; (b) Click Submit Exam â†’ Confirm â†’ loading state applied â†’ mock `submit-success.json` response â†’ navigates to `../result/index.html`; (c) Mock `submit-bridge-error.json` on Confirm â†’ loading clears, inline error shown, Retry button visible, timer resumes.

### Implementation for User Story 3

- [x] T020 [P] [US3] Implement `exam.css` â€” submission UI styles:
  - **Submit Exam button** (header): `.btn-submit-exam { padding: 8px 20px; border-radius: var(--radius-chip, 8px); border: none; background: linear-gradient(135deg, var(--color-error), var(--color-tertiary)); color: #fff; font-family: var(--font-display); font-size: 13px; font-weight: 700; cursor: pointer; letter-spacing: 0.04em; transition: opacity 0.15s; }` â€” `.btn-submit-exam:disabled { opacity: 0.5; cursor: not-allowed; }`
  - **Confirmation modal**: `.modal-backdrop { position: fixed; inset: 0; z-index: 200; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px); }` â€” `.modal-backdrop.hidden { display: none; }` â€” `.modal-glass { background: rgba(var(--color-surface-container-lowest-rgb, 255,255,255), 0.9); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.15); border-radius: var(--radius-card, 16px); padding: 32px; max-width: 440px; width: 90%; box-shadow: var(--shadow-ambient, 0 8px 32px rgba(0,0,0,0.12)); }` â€” `.modal-actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px; }`
  - **Error banner**: `.error-banner { position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); background: var(--color-error-container, #fde6e6); color: var(--color-on-error-container, #b00020); border-radius: var(--radius-chip, 8px); padding: 12px 20px; display: flex; align-items: center; gap: 16px; font-size: 14px; z-index: 150; }` â€” `.error-banner.hidden { display: none; }` â€” `.btn-retry { padding: 6px 14px; border: 1.5px solid currentColor; border-radius: var(--radius-chip, 8px); background: none; color: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }`
  - **Loading / disabled state**: `.exam-page-loading .btn-submit-exam, .exam-page-loading .btn-nav, .exam-page-loading .choice-item, .exam-page-loading .nav-pill, .exam-page-loading .flag-btn, .exam-page-loading #jumpInput { pointer-events: none; opacity: 0.5; }` â€” `.exam-page-loading .exam-header { cursor: wait; }`

- [x] T021 [US3] Implement `exam.js` â€” "Submit Exam" button click handler: count unanswered = `examSession.questions.length - Object.keys(answerMap).length`; set `#modalTitle` to exam title; set `#modalMessage` to either `"You haven't answered any questions yet."` (if 0 answered) or `"${unanswered} question(s) remaining unanswered."` (if some answered but not all) or `"All questions answered. Ready to submit."` (if all answered); remove `hidden` from `#modalBackdrop`

- [x] T022 [US3] Implement `exam.js` â€” modal Cancel handler: `#modalCancelBtn` click â†’ add `hidden` to `#modalBackdrop`

- [x] T023 [US3] Implement `exam.js` â€” `submitExam(isAutoSubmit)` function:
  - Guard: if `isSubmitting` is `true`, return immediately (prevent double-submit including duplicate auto-submit)
  - Set `isSubmitting = true`; add `.exam-page-loading` class to `<body>`; add `hidden` to `#modalBackdrop`; add `hidden` to `#errorBanner`
  - Pause timer: `clearInterval(timerInterval); timerInterval = null;`
  - Build payload: `const answers = Object.entries(answerMap).map(([qId, cId]) => ({ questionId: +qId, choiceId: cId }))`
  - Call `const result = await window.bridge.submitExam(answers)`
  - **On `{ ok: true, data }`**: navigate to result page with `window.location.href = '../result/index.html'` (IPC side-effect: main.js already stored `submitResult`)
  - **On `{ ok: false, error }`**: set `isSubmitting = false`; remove `.exam-page-loading` from `<body>`; set `#errorBannerText` to `result.error.message`; remove `hidden` from `#errorBanner`; if `!isAutoSubmit` (manual submit failure), restart timer from remaining seconds; if `isAutoSubmit`, leave timer frozen at "00:00:00" (do NOT restart)
  - **On Promise rejection (rare network failure)**: same as `{ ok: false }` path with generic BRIDGE_ERROR message

- [x] T024 [US3] Implement `exam.js` â€” modal Confirm handler: `#modalConfirmBtn` click â†’ call `submitExam(false)`

- [x] T025 [US3] Implement `exam.js` â€” Retry button handler: `#retryBtn` click â†’ call `submitExam(autoSubmitted)` (pass `true` if timer expired, `false` if manual, so timer-resume logic is preserved on retry)

**Checkpoint US3**: Confirm modal shows correct unanswered count; Cancel resumes exam without submission; Confirm + mock success â†’ result page loads; Confirm + mock error â†’ error banner visible, Retry button present; timer resumes after a manual-submit failure.

---

## Phase 6: User Story 4 â€” Countdown Timer (Priority: P2)

**Goal**: A visible countdown timer runs from `examSession.duration` toward 00:00:00, using drift correction. It turns red at â‰¤5 minutes. At 00:00:00 it auto-submits without prompting the user.

**Independent Test**: Set `duration: "00:00:10"` in the mock session; open the Exam page; observe the timer counting from 00:00:10 down to 00:00:00; verify no confirmation modal is shown; auto-submit fires and navigates to result page (with success mock) or shows error banner (with error mock). Set `duration: "00:05:30"`; wait until `00:05:00` is displayed; verify timer chip text colour changes to `var(--color-error)`.

### Implementation for User Story 4

- [x] T026 [P] [US4] Implement `exam.css` â€” timer chip styles:
  - `.timer-chip { background: var(--color-surface-container-low); border-radius: var(--radius-chip, 8px); padding: 8px 16px; font-family: var(--font-display); font-size: 18px; font-weight: 700; color: var(--color-primary); letter-spacing: 0.04em; min-width: 110px; text-align: center; transition: color 0.3s; }`
  - `.timer-chip.is-warning { color: var(--color-error); }`

- [x] T027 [US4] Implement `exam.js` â€” `startTimer()` function:
  - Record `timerStartTime = Date.now()` and use `timerTotalSeconds` (already stored in Phase 3 T012)
  - Set `timerInterval = setInterval(() => { ... }, 1000)` where each tick:
    - Computes `elapsed = Math.floor((Date.now() - timerStartTime) / 1000)` (drift-corrected)
    - Computes `remaining = Math.max(0, timerTotalSeconds - elapsed)`
    - Formats `remaining` as HH:mm:ss: `const h = Math.floor(remaining/3600); const m = Math.floor((remaining%3600)/60); const s = remaining%60; const display = [h,m,s].map(n=>String(n).padStart(2,'0')).join(':')`
    - Updates `#timerDisplay` text content
    - Toggles `is-warning` class on `#timerChip` when `remaining <= 300` (5 minutes)
    - When `remaining === 0` and `!autoSubmitted`: `clearInterval(timerInterval); autoSubmitted = true; submitExam(true)`

- [x] T028 [US4] Implement `exam.js` â€” timer resume logic (used by US3 error recovery on manual submit): extract remaining seconds from `#timerDisplay` text content, set `timerStartTime = Date.now() - (timerTotalSeconds - remaining) * 1000`, then call `startTimer()`

**Checkpoint US4**: Timer ticks down accurately; SC-004 drift check â€” run a 5-second mock exam, verify it reaches 00:00:00 within 1 second of real elapsed time and auto-submit fires; warning colour activates at 00:05:00.

---

## Phase 7: User Story 5 â€” Flag Questions for Review (Priority: P3)

**Goal**: A student can flag a question for later review. Flagged questions show a distinct warning-coloured indicator in the navigator. Flagging a question already answered does not clear the answer.

**Independent Test**: Click flag button on question 3 â†’ navigator pill 3 turns tertiary (orange); navigate away and back â†’ flag persists; click flag button again â†’ pill reverts to answered or unanswered state.

### Implementation for User Story 5

- [x] T029 [US5] Implement `exam.js` â€” flag button click handler: read `questionId` of current question (`examSession.questions[currentIndex].id`); toggle: `flagSet.has(questionId) ? flagSet.delete(questionId) : flagSet.add(questionId)`; update `#flagBtn` â€” add/remove `is-flagged` class; call `updatePillStates()`

**Checkpoint US5**: Flag toggle works in both directions; navigator pill priority (flagged > answered > unanswered) confirmed by answering then flagging question 2.

---

## Phase 8: User Story 6 â€” Proctoring Panel (Priority: P3)

**Goal**: The live webcam feed is displayed in the proctoring aside panel. If permission is denied, a "Camera unavailable" placeholder is shown without affecting exam functionality. All tracks are released on navigation away.

**Independent Test**: Allow camera â†’ `<video>` shows live feed, "LIVE FEED" badge visible; Deny camera â†’ "Camera unavailable" placeholder shown, exam still usable; Submit and navigate â†’ camera indicator light goes off within 1 second.

### Implementation for User Story 6

- [x] T030 [P] [US6] Implement `exam.css` â€” proctoring panel, webcam view, status row, and AI indicator styles:
  - `.webcam-section { position: relative; border-radius: var(--radius-card, 16px); overflow: hidden; background: var(--color-surface-container-high); aspect-ratio: 4/3; }`
  - `.webcam-feed { width: 100%; height: 100%; object-fit: cover; display: block; }`
  - `.live-badge { position: absolute; top: 8px; left: 8px; background: var(--color-error); color: #fff; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; padding: 2px 8px; border-radius: 4px; }`
  - `.camera-unavailable { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--color-surface-container-high); color: var(--color-on-surface-variant); font-size: 13px; }`
  - `.camera-unavailable.hidden { display: none; }`
  - `.ai-status-rows { display: flex; flex-direction: column; gap: 8px; margin-top: 4px; }`
  - `.status-row { background: var(--color-surface-container-lowest); border-radius: var(--radius-card, 16px); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; }`
  - `.status-label { color: var(--color-on-surface-variant); }`
  - `.status-indicator { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.06em; }`
  - `.status-indicator.active { background: rgba(0,128,0,0.1); color: #1a7a1a; }`
  - `.status-indicator.inactive { background: var(--color-surface-container-high); color: var(--color-on-surface-variant); }`

- [x] T031 [US6] Implement `exam.js` â€” `initWebcam()` function: call `navigator.mediaDevices.getUserMedia({ video: true, audio: false })`; on success: assign `activeStream = stream`; assign `document.getElementById('webcamFeed').srcObject = stream`; on failure (any error including `NotAllowedError`, `NotFoundError`): `document.getElementById('webcamFeed').classList.add('hidden')`; `document.getElementById('cameraUnavailable').classList.remove('hidden')`

- [x] T032 [US6] Implement `exam.js` â€” `beforeunload` handler: `window.addEventListener('beforeunload', () => { activeStream?.getTracks().forEach(t => t.stop()); })` â€” add this registration inside the `DOMContentLoaded` handler immediately after `initWebcam()` is called

**Checkpoint US6**: Video renders; denial shows placeholder; submitting and navigating away stops camera tracks (light off within 1 second per SC-006).

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, CSP validation, design token audit, and quickstart scenario walkthrough.

- [x] T033 Update the Content-Security-Policy meta tag in `frontend/pages/exam/index.html` â€” verify that `media-src 'self'` is added if needed for `getUserMedia` (Electron renderer policy check); also confirm `script-src 'self'` already covers the `defer` script tag; confirm the CSP does not block `blob:` URLs if `srcObject` uses any blob URL internally

- [x] T034 [P] Design token audit in `frontend/pages/exam/exam.css` â€” scan the entire file and verify zero hardcoded hex/rgb colour values appear; all colour references must use `var(--color-*)` tokens; no `1px solid #borderHex`-style rules; font references use `var(--font-display)` for headings and `var(--font-body)` for body text

- [x] T035 [P] Integration smoke test against `specs/004-exam-page/mocks/exam-session.json` â€” follow all 8 manual test scenarios in `specs/004-exam-page/quickstart.md` Scenarios 1â€“8; mark each scenario pass/fail; fix any failures before marking T035 done

- [x] T036 Verify `frontend/pages/result/index.html` placeholder loads without JS errors when navigated to after a successful submit â€” open DevTools Console on the result page and confirm no uncaught exceptions from leftover exam.js code

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies â€” can start immediately; all three tasks are parallel
- **Phase 2 (Foundational)**: Depends on Phase 1 completion â€” blocks US3 end-to-end testing only
- **Phase 3 (US1)**: Depends on Phase 1; independent of Phase 2 (bridge:get-exam-session already exists from spec 003)
- **Phase 4 (US2)**: Depends on Phase 3 completion
- **Phase 5 (US3)**: Depends on Phase 2 AND Phase 4
- **Phase 6 (US4)**: Depends on Phase 3 (timer is initialized after session load in T012)
- **Phase 7 (US5)**: Depends on Phase 3 (flagSet updates call updatePillStates from US1)
- **Phase 8 (US6)**: Depends on Phase 3 (initWebcam called in DOMContentLoaded T012 path)
- **Phase 9 (Polish)**: Depends on all story phases

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 1 (scaffolding). Core browsing is independent of submit plumbing.
- **US2 (P1)**: Depends on US1 (answerMap updates call renderQuestion + updatePillStates from US1).
- **US3 (P2)**: Depends on Phase 2 (IPC plumbing) AND US2 (answerMap is serialised for the payload).
- **US4 (P2)**: Depends on US1 (startTimer called from DOMContentLoaded after session load).
- **US5 (P3)**: Depends on US1 (updatePillStates must exist before flag toggle calls it).
- **US6 (P3)**: Depends on US1 (initWebcam called from the shared DOMContentLoaded handler in T012).

### Within Each User Story

- HTML structure (T009) â†’ CSS (T010/T011) â†’ JS logic (T012â€“T018) for US1
- Phase 2 (T004â€“T008) can be built in parallel with Phase 3 (US1)

---

## Parallel Execution Examples

### Phase 1 (all parallel)
```
T001  Create exam.css stub
T002  Create exam.js stub
T003  Create result/index.html placeholder
```

### Phase 2 (T004+T005 parallel to T006, then T007+T008 parallel)
```
T004  Add map_lms_submit_error() to exam.py
T005  Add POST /submit-exam route to exam.py      â† depends on T004
T006  Add channels + methods to preload.js         â† parallel to T004/T005
T007  Add submitResult var to main.js              â† depends on T006
T008  Add IPC handlers to main.js                  â† depends on T007
```

### Phase 3 (US1)
```
T010  exam.css â€” layout + skeleton                  [P] parallel to T011
T011  exam.css â€” question area + choices + flag     [P] parallel to T010
T016  exam.css â€” navigator pill states              [P] parallel to T010, T011
T009  index.html â€” full HTML structure              (do first; others read it)
T012  exam.js â€” DOMContentLoaded + session bootstrap
T013  exam.js â€” renderQuestion()                    (depends on T012)
T014  exam.js â€” pill generation in initPage()       (depends on T012)
T015  exam.js â€” updatePillStates()                  (depends on T014)
T017  exam.js â€” Prev/Next handlers                  (depends on T013)
T018  exam.js â€” Jump-to handler                     (depends on T013)
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (T001â€“T003)
2. Complete Phase 3: US1 (T009â€“T018) â€” browsable exam
3. Complete Phase 4: US2 (T019) â€” answer selection
4. **STOP and VALIDATE**: Answers persist across navigation; pills reflect answered state
5. Demo: A student can read all questions and select answers

### Incremental Delivery

| Increment | Stories | Validates |
|-----------|---------|-----------|
| after US1+US2 | Browse + Answer | SC-001, SC-002 |
| + Phase 2 + US3 | Submit | SC-003, portal-end-to-end |
| + US4 | Timer | SC-004, SC-005 |
| + US5 | Flag | UX quality |
| + US6 | Webcam | SC-006, FR-017/018 |
| + Phase 9 | Polish | All SCs |

### Total Task Summary

| Phase | Tasks | Parallelisable |
|-------|-------|----------------|
| Phase 1: Setup | 3 | 3 |
| Phase 2: Foundational | 5 | 2 |
| Phase 3: US1 | 10 | 3 |
| Phase 4: US2 | 1 | 0 |
| Phase 5: US3 | 6 | 1 |
| Phase 6: US4 | 3 | 1 |
| Phase 7: US5 | 1 | 0 |
| Phase 8: US6 | 3 | 1 |
| Phase 9: Polish | 4 | 2 |
| **Total** | **36** | **13** |
