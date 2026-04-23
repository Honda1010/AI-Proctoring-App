# Tasks: Identity Verification Page

**Input**: Design documents from `specs/010-identity-verification/`  
**Branch**: `010-identity-verification`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Not explicitly requested — no test tasks generated.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to ([US1]–[US4])

---

## Phase 1: Setup

**Purpose**: Configuration and new file scaffolding that must exist before any story work begins.

- [X] T001 Add `enroll_endpoint_url`, `unenroll_endpoint_url`, `face_detect_endpoint_url` under `services.face-recognition` in `config.json`
- [X] T002 [P] Scaffold `frontend/pages/identity-verification/index.html` (empty shell — `<head>`, font imports, CSS link, script tag only)
- [X] T003 [P] Scaffold `frontend/pages/identity-verification/identity-verification.css` (empty file with design-tokens import)
- [X] T004 [P] Scaffold `frontend/pages/identity-verification/identity-verification.js` (empty `'use strict';` module with DOMContentLoaded stub)

**Checkpoint**: Config updated; three new page files exist — story work can begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Python-layer changes that ALL user stories depend on. Must be complete before US1–US4.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [X] T005 Add `face_detect()`, `enroll()`, and `unenroll()` async methods to `ModalClient` in `python_bridge/modal_client.py` — read `face_detect_endpoint_url`, `enroll_endpoint_url`, `unenroll_endpoint_url` from the instance config; use multipart `session_id` (form) + `frame`/`references` (file) per `AI_Services_APIs.md`
- [X] T006 Add `enroll(frame)` and `unenroll()` async methods to `FaceRecognitionService` in `python_bridge/face_recognition.py`; `enroll()` chains `client.face_detect()` → `client.enroll()` and returns `{ok, error?}`; `unenroll()` calls `client.unenroll()` and swallows errors
- [X] T007 Remove the `await self.client.predict(self.service_name, self.session_id, "WARMUP")` call from `FaceRecognitionService.start()` in `python_bridge/face_recognition.py`
- [X] T008 Add `handle_enroll_reference` and `handle_unenroll_reference` dispatch handlers to `python_bridge/router.py`; register them in the method dispatch table alongside existing handlers (`startService`, `predict`, etc.)
- [X] T009 Pass `enroll_endpoint_url`, `unenroll_endpoint_url`, `face_detect_endpoint_url` from `FaceRecognitionService.__init__` to `ModalClient` (or store on `self` for use by new methods) in `python_bridge/face_recognition.py`

**Checkpoint**: Router accepts `enrollReference` and `unenrollReference` JSON-RPC calls; `FaceRecognitionService` no longer sends WARMUP on start.

---

## Phase 3: User Story 1 — Student Captures Reference Photo (Priority: P1) 🎯 MVP

**Goal**: Student can arrive at the Identity Verification page after entering an exam code, see their live webcam feed, click "Capture Photo," confirm, and be navigated to the AI Readiness page after successful enrollment.

**Independent Test**: Load `frontend/pages/identity-verification/index.html` directly. Confirm webcam activates, "Capture Photo" button is present and clickable, frame freezes on click, "Confirm & Continue" appears. Call `window.bridge.enrollReference(frame)` from DevTools console and confirm navigation to `ai-readiness/index.html` on mock success.

- [X] T010 [US1] Implement full HTML markup for `frontend/pages/identity-verification/index.html` — glassmorphism card layout, `<video id="webcamFeed">`, offscreen `<canvas id="captureCanvas">`, face-outline overlay with corner accents, "Capture Photo" button (`id="captureBtn"`), "Retake Photo" button (`id="retakeBtn"` hidden), "Confirm & Continue" button (`id="confirmBtn"` hidden), spinner element (`id="verifySpinner"` hidden), error pill (`id="errorPill"` hidden), and the three quality indicator rows (Lighting, Focus, Face Detected) per `Designs/Identity_Verification_Page/code.html`
- [X] T011 [US1] Implement `initCamera()` in `frontend/pages/identity-verification/identity-verification.js` — call `navigator.mediaDevices.getUserMedia({ video: true, audio: false })`, assign stream to `webcamFeed.srcObject`, show camera-denied error message if permission rejected (matches `ai-readiness.js` pattern)
- [X] T012 [US1] Implement `handleCaptureClick()` in `frontend/pages/identity-verification/identity-verification.js` — draw current `webcamFeed` frame to 640×480 canvas at JPEG quality 0.85, store as `capturedDataUrl`, switch UI to CAPTURED state (hide capture btn, show retake + confirm btns, freeze feed preview)
- [X] T013 [US1] Implement `handleConfirmClick()` in `frontend/pages/identity-verification/identity-verification.js` — enter VERIFYING state (disable all buttons, show "Verifying identity…" spinner), call `window.bridge.enrollReference(capturedDataUrl)`, on `ok: true` navigate to `../ai-readiness/index.html`, on failure call `showError()` and return to LIVE state
- [X] T014 [US1] Implement `showError(code)` in `frontend/pages/identity-verification/identity-verification.js` — map `NO_FACE_DETECTED` → "No face detected — adjust your position and try again"; `ENROLLMENT_FAILED` → "Verification failed — please retake your photo"; default → "An error occurred. Please try again."; display in `#errorPill`; resume live feed (re-assign `webcamFeed.srcObject = stream`)
- [X] T015 [US1] Add `let enrollmentState = null` module-scope variable to `frontend/main.js`; add `ipcMain.handle('bridge:enroll-reference', ...)` handler that reads `sessionId` from `examSession.attemptId`, calls `sendAiRpc('enrollReference', { frame, sessionId })`, sets `enrollmentState = { sessionId, enrolledAt: new Date(), succeeded: true }` on success, and returns `{ ok, error? }` to renderer
- [X] T016 [US1] Add `ipcMain.handle('bridge:get-enrollment-status', ...)` handler to `frontend/main.js` — returns `{ enrolled: enrollmentState?.succeeded === true }`
- [X] T017 [US1] Add `'bridge:enroll-reference'` and `'bridge:get-enrollment-status'` to `ALLOWED_INVOKE_CHANNELS` in `frontend/preload.js`
- [X] T018 [US1] Add `enrollReference(frame)` and `getEnrollmentStatus()` methods to the `contextBridge.exposeInMainWorld('bridge', { ... })` object in `frontend/preload.js`
- [X] T019 [US1] Change the successful exam-start redirect in `frontend/pages/exam-code/exam-code.js` from `'../ai-readiness/index.html'` to `'../identity-verification/index.html'`
- [X] T020 [US1] Add `DOMContentLoaded` guard to `frontend/pages/identity-verification/identity-verification.js` — call `window.bridge.getExamSession()` on load; if `!result?.ok` redirect to `../exam-code/index.html` (mirrors ai-readiness.js guard pattern); then call `initCamera()` and `startQualityLoop()`
- [X] T021 [US1] Add `beforeunload` handler to `frontend/pages/identity-verification/identity-verification.js` — stop webcam stream tracks and clear quality indicator interval

**Checkpoint**: US1 fully functional — student can capture photo and enroll. Navigation flow: exam-code → identity-verification → ai-readiness.

---

## Phase 4: User Story 2 — Student Retakes an Unsatisfactory Photo (Priority: P2)

**Goal**: After a capture, the student can click "Retake Photo" to discard the captured image and return to the live webcam feed.

**Independent Test**: Capture a photo (T012 state), then click "Retake Photo." Confirm live feed resumes, `capturedDataUrl` is null, capture button reappears, confirm/retake buttons are hidden.

- [X] T022 [US2] Implement `handleRetakeClick()` in `frontend/pages/identity-verification/identity-verification.js` — clear `capturedDataUrl`, re-assign `webcamFeed.srcObject = stream` to resume live feed, switch UI to LIVE state (show capture btn, hide retake + confirm btns, clear any error pill)

**Checkpoint**: US2 fully functional — retake button discards capture and resumes live feed.

---

## Phase 5: User Story 3 — Quality Indicators Guide the Student (Priority: P3)

**Goal**: Three real-time quality indicators (Lighting, Focus, Face Detected) update continuously from a canvas pixel analysis tick while the webcam is active.

**Independent Test**: With webcam active, observe all three indicators cycling between states. Cover the camera lens — Lighting and Face Detected indicators should reflect the change within ~500 ms.

- [X] T023 [P] [US3] Implement `analyzeQuality(ctx, width, height)` in `frontend/pages/identity-verification/identity-verification.js` — compute average luminance (brightness) for Lighting indicator (`sum of 0.299R + 0.587G + 0.114B` across all pixels; threshold >40 = Adequate); compute Laplacian-variance estimate for Focus (`variance of pixel-diff across 3×3 neighbourhood on greyscale`; threshold >30 = Sharp); return `{ lighting: 'adequate'|'low', focus: 'sharp'|'blurry', face: 'detected'|'unknown' }` (face field is set by a separate brightness-contrast heuristic — bright oval region in upper-centre third of frame)
- [X] T024 [P] [US3] Implement `startQualityLoop()` and `stopQualityLoop()` in `frontend/pages/identity-verification/identity-verification.js` — `setInterval` at 500 ms; draw video to offscreen 160×120 canvas; call `analyzeQuality()`; update `#lightingIndicator`, `#focusIndicator`, `#faceIndicator` DOM elements with appropriate CSS class (`indicator--ok` / `indicator--warn`) and label text
- [X] T025 [US3] Implement CSS for quality indicators in `frontend/pages/identity-verification/identity-verification.css` — three-column row layout; `.indicator--ok` uses `var(--success)` accent; `.indicator--warn` uses `var(--warning)` accent; icon + label typography uses Inter body size per design tokens; matches `Designs/Identity_Verification_Page/code.html` layout

**Checkpoint**: US3 fully functional — quality indicators animate live while webcam is active.

---

## Phase 6: User Story 4 — Captured Reference Used by Face Recognition During Exam (Priority: P1)

**Goal**: The exam page is gated on enrollment status; the face-recognition service sends only `session_id` + live `frame` in each verify call (embedding already stored server-side after enrollment); unenroll fires on all exam exit paths.

**Independent Test**: Complete enrollment flow (US1), navigate to exam page — confirm page loads (not redirected). Submit exam or click "Back to Home" — confirm `unenrollReference` JSON-RPC is sent (check Electron main process logs).

- [X] T026 [US4] Add enrollment guard to `frontend/pages/exam/exam.js` `DOMContentLoaded` handler — call `window.bridge.getEnrollmentStatus()`; if `!result?.enrolled` navigate to `../identity-verification/index.html` before any other exam initialisation
- [X] T027 [US4] Add unenroll call to `bridge:submit-exam` success path in `frontend/main.js` — after `submitResult = body`, call `sendAiRpc('unenrollReference', { sessionId: enrollmentState?.sessionId })` fire-and-forget; then set `enrollmentState = null`
- [X] T028 [US4] Add unenroll call to `bridge:clear-submit-result` handler in `frontend/main.js` — call `sendAiRpc('unenrollReference', { sessionId: enrollmentState?.sessionId })` fire-and-forget; then set `enrollmentState = null` before the existing `examSession = null` line
- [X] T029 [US4] Add unenroll call to `bridge:clear-session` handler in `frontend/main.js` — call `sendAiRpc('unenrollReference', { sessionId: enrollmentState?.sessionId })` fire-and-forget; then set `enrollmentState = null`

**Checkpoint**: US4 fully functional — exam page gated; unenroll fires on all three exit paths; face-recognition verify calls use session_id only (no reference image sent per-frame — Modal uses enrolled embedding).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Design system compliance, CSS completion, and UX details.

- [X] T030 [P] Implement complete CSS for `frontend/pages/identity-verification/identity-verification.css` — full page layout matching `Designs/Identity_Verification_Page/code.html`: glassmorphism card (`var(--surface-container-lowest)` ≥70% opacity, `backdrop-filter: blur(16px)`); face-outline frame with four corner-accent SVG brackets (`var(--primary)` colour); video element fills frame; button styles (primary gradient "Capture Photo", secondary ghost "Retake Photo"); spinner animation; error pill; all colours via CSS custom properties from `frontend/assets/design-tokens.css` — no hardcoded hex
- [X] T031 [P] Add Manrope + Inter font imports to `frontend/pages/identity-verification/index.html` `<head>` (matching existing pages: `@fontsource/manrope` and `@fontsource/inter`)
- [X] T032 Verify `bridge:get-enrollment-status` is NOT accessible when `enrollmentState` is null and no exam session exists — confirm `{ enrolled: false }` returned (not an error); manual test: open exam page without prior enrollment, confirm redirect to identity-verification

---

## Dependencies (Story Completion Order)

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundation — Python layer)
    ↓           ↓
Phase 3      Phase 6
(US1 — MVP)  (US4 — exam gate + unenroll)
    ↓
Phase 4
(US2 — retake)
    ↓
Phase 5
(US3 — quality indicators)
    ↓
Phase 7
(Polish)
```

**US4 parallel note**: T026–T029 (US4 frontend) can be worked in parallel with T010–T021 (US1) once Phase 2 is complete, since they touch different parts of `main.js` and `exam.js`.

---

## Parallel Execution Examples

### Sprint 1 — After Phase 2 complete, run these in parallel:

| Stream A (US1 — page + IPC) | Stream B (US4 — exam gate + unenroll) |
|-----------------------------|---------------------------------------|
| T010 HTML markup | T026 Exam page enrollment guard |
| T011 initCamera() | T027 Unenroll on submit |
| T012 handleCaptureClick() | T028 Unenroll on back-to-home |
| T013 handleConfirmClick() | T029 Unenroll on logout |
| T014 showError() | |
| T015 main.js enroll handler | |
| T016 main.js status handler | |
| T017–T018 preload.js | |
| T019 exam-code redirect | |
| T020 page guard | |
| T021 beforeunload | |

### Sprint 2 — After US1 complete, run in parallel:

| Stream A (US2) | Stream B (US3) | Stream C (Polish) |
|----------------|----------------|-------------------|
| T022 Retake click | T023 analyzeQuality() | T030 Full CSS |
| | T024 startQualityLoop() | T031 Font imports |
| | T025 Indicator CSS | T032 Guard verify |

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1) + Phase 6 (US4)**

This delivers: student capture → enrollment → exam with face-recognition using Modal embeddings + guard against skipping enrollment. Everything needed for the feature to be live and testable end-to-end.

US2 (retake) and US3 (quality indicators) are UX enhancements that can be added in a follow-up increment without blocking the core flow.

---

## Task Count Summary

| Phase | Tasks | Stories |
|-------|-------|---------|
| Phase 1: Setup | T001–T004 (4) | — |
| Phase 2: Foundation | T005–T009 (5) | — |
| Phase 3: US1 MVP | T010–T021 (12) | US1 |
| Phase 4: US2 | T022 (1) | US2 |
| Phase 5: US3 | T023–T025 (3) | US3 |
| Phase 6: US4 | T026–T029 (4) | US4 |
| Phase 7: Polish | T030–T032 (3) | — |
| **Total** | **32** | **4 stories** |

**Parallel opportunities**: 11 tasks marked [P] across Phases 1, 5, and 7.  
**MVP scope**: T001–T021 + T026–T029 = 25 tasks.
