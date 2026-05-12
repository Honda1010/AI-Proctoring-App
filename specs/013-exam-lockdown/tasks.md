# Tasks: Exam Lockdown

**Input**: Design documents from `/specs/013-exam-lockdown/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- File paths are absolute from project root

---

## Phase 1: Setup

**Purpose**: Verify dependencies and confirm no new packages are required.

- [X] T001 Verify `psutil` is listed in `python_bridge/requirements.txt` (no new dependencies needed — confirm presence and version ≥ 5.9)

**Checkpoint**: All dependencies present. No installs required.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the Python lockdown blueprint stub and add shared state/helpers to `main.js`. MUST be complete before any user story work begins.

**⚠️ CRITICAL**: US3 and US4 depend on `python_bridge/lockdown.py` existing. US1–US4 all depend on the `main.js` state additions.

- [X] T002 Create `python_bridge/lockdown.py` with `lockdown_bp = Blueprint('lockdown', __name__)` and a bare `POST /check-environment` route that returns a clean `EnvironmentCheckResult` JSON (all fields `false`/`null`) — detection logic added in US3/US4 phases
- [X] T003 [P] Import `lockdown_bp` from `python_bridge/lockdown.py` and call `app.register_blueprint(lockdown_bp)` in `python_bridge/server.py` alongside existing `auth_bp` and `exam_bp` registrations
- [X] T004 [P] Add module-scope state variables `let envCheckInterval = null` and `let lockdownActive = false` immediately after the existing `let examSession = null` declaration (line 253) in `frontend/main.js`
- [X] T005 [P] Add `appendLockdownAlert(type, reason)` helper function in `frontend/main.js` that writes a `LockdownAlertRecord` JSON line to `sessions/{examSession.attemptId}.jsonl` using a `try/catch` best-effort pattern (never throws) — fields: `type`, `timestamp` (UTC ISO 8601 via `new Date().toISOString()`), `sessionId` (`String(examSession.attemptId)`), `reason`

**Checkpoint**: `POST /check-environment` returns `200 {"vm_detected":false,...}`. `appendLockdownAlert` and state vars exist in `main.js`. Blueprint registered.

---

## Phase 3: User Story 1 — Fullscreen Enforcement (Priority: P1) 🎯 MVP Start

**Goal**: Window is frameless kiosk fullscreen, always-on-top, non-closeable, and auto-re-enters fullscreen on OS-forced exit during an active exam session.

**Independent Test**: Start an exam session — window must fill screen with no title bar or OS chrome. Press Alt+F4 — window stays open. Force an OS fullscreen exit — window re-enters fullscreen within 1 second and `FULLSCREEN_ESCAPE_ATTEMPT` appears in `sessions/{attemptId}.jsonl`.

### Implementation for User Story 1

- [X] T006 [US1] Add `activateLockdown()` function in `frontend/main.js` that sets `lockdownActive = true` and calls: `mainWindow.setFullScreen(true)`, `mainWindow.setKiosk(true)`, `mainWindow.setAlwaysOnTop(true)`, `mainWindow.setResizable(false)`, `mainWindow.setMovable(false)`, `mainWindow.setMinimizable(false)` — shortcut registration and content protection added in later phases
- [X] T007 [US1] Add `deactivateLockdown()` function in `frontend/main.js` that sets `lockdownActive = false` and reverses all window setters: `setFullScreen(false)`, `setKiosk(false)`, `setAlwaysOnTop(false)`, `setResizable(true)`, `setMovable(true)`, `setMinimizable(true)` — shortcut unregistration and content protection removal added in later phases
- [X] T008 [US1] Add `mainWindow.on('close', (event) => { if (examSession) event.preventDefault(); })` handler in `frontend/main.js` to prevent window closure during active exam session; place after BrowserWindow constructor (around line 1130)
- [X] T009 [US1] Add `mainWindow.on('leave-full-screen', () => { if (examSession) { mainWindow.setFullScreen(true); appendLockdownAlert('FULLSCREEN_ESCAPE_ATTEMPT', 'fullscreen exit detected'); } })` handler in `frontend/main.js` — single best-effort re-entry, no retry loop, no student-facing message
- [X] T010 [US1] Wire `activateLockdown()` into the `bridge:start-exam` IPC handler (around line 678) in `frontend/main.js`, called immediately after `examSession = body` is set; wire `deactivateLockdown()` into all three exit paths: `bridge:submit-exam` (line ~823), `bridge:clear-session` (line ~563), and `bridge:clear-submit-result` (line ~920)

**Checkpoint**: Launch app, start exam — window is fullscreen, frameless, always-on-top. Alt+F4 does nothing. End exam — window restores normally.

---

## Phase 4: User Story 2 — Keyboard Shortcut Blocking (Priority: P1)

**Goal**: All interceptable shortcuts (Ctrl+C, PrintScreen, F11, Escape, Ctrl+Shift+I, etc.) are silently consumed during an active exam. F12/DevTools is blocked. All shortcuts restored on exam end.

**Independent Test**: With an active exam session, press each shortcut from the `BlockedShortcutSet` table in `specs/013-exam-lockdown/data-model.md` — each must produce no observable effect. End exam and verify all shortcuts work normally.

### Implementation for User Story 2

- [X] T011 [US2] Add `globalShortcut` to the destructured electron import at the top of `frontend/main.js` (line 1): change `{ app, BrowserWindow, ipcMain, net, shell }` to include `globalShortcut`
- [X] T012 [US2] Add `const BLOCKED_SHORTCUTS = ['PrintScreen', 'Alt+PrintScreen', 'F11', 'Escape', 'Ctrl+Shift+I', 'Ctrl+W', 'Ctrl+A', 'Ctrl+C', 'Ctrl+V', 'Ctrl+X']` constant in `frontend/main.js` and register each via `globalShortcut.register(shortcut, () => {})` inside `activateLockdown()` in `frontend/main.js`, guarded by `if (!lockdownActive)` to prevent double-registration
- [X] T013 [US2] Update the existing `before-input-event` handler (around line 1146) in `frontend/main.js`: add a guard `if (examSession)` that calls `event.preventDefault()` for any input whose `key` is in `BLOCKED_SHORTCUTS` equivalents (including `F12`, `Escape`, `F11`, `c`/`v`/`x`/`a`/`w` with ctrlKey, `i` with ctrlKey+shiftKey, `PrintScreen`); remove the existing unconditional F12→DevTools logic and replace with `if (!examSession) { mainWindow.webContents.openDevTools(); }`
- [X] T014 [US2] Add `globalShortcut.unregisterAll()` call inside `deactivateLockdown()` in `frontend/main.js`, placed before the window setter reversals

**Checkpoint**: Start exam — Ctrl+C, PrintScreen, F11, Escape, Ctrl+Shift+I all produce no effect. F12 does not open DevTools. End exam — F12 opens DevTools normally.

---

## Phase 5: User Story 3 — VM and Remote Desktop Detection (Priority: P2)

**Goal**: On exam start and every 60 seconds, the app checks for VM environments and remote desktop tools. Detections log a `VIRTUAL_ENVIRONMENT` alert and show a blocking modal. Modal dismissal resumes the exam immediately; re-detection on the next cycle shows it again.

**Independent Test**: Run app inside VirtualBox — start exam — blocking modal must appear within the first check cycle. Inspect `sessions/{attemptId}.jsonl` — a `VIRTUAL_ENVIRONMENT` record must be present. Dismiss modal — exam interaction resumes immediately.

### Implementation for User Story 3

- [X] T014 [P] [US3] Implement VM detection in `python_bridge/lockdown.py`
- [X] T015 [US3] Implement RDP/remote-desktop process detection in `python_bridge/lockdown.py`
- [X] T016 [US3] Implement RDP network detection in `python_bridge/lockdown.py`
- [X] T017 [US3] Add `runEnvCheck()` async function in `frontend/main.js`
- [X] T018 [US3] Inside `activateLockdown()` in `frontend/main.js`, call `runEnvCheck()` immediately (first check on exam start), then start `envCheckInterval = setInterval(runEnvCheck, 60_000)`; inside `deactivateLockdown()`, add `clearInterval(envCheckInterval); envCheckInterval = null;`
- [X] T019 [P] [US3] Add `'lockdown:vm-detected'` to `ALLOWED_RECEIVE_CHANNELS` array in `frontend/preload.js` and expose `onLockdownVmDetected` via `contextBridge.exposeInMainWorld`
- [X] T020 [P] [US3] Add VM violation modal markup to `frontend/pages/exam/index.html`
- [X] T021 [US3] In `frontend/pages/exam/exam.js`, wire `window.bridge.onLockdownVmDetected` to show `#lockdown-vm-modal`, disable interaction, and dismiss to re-enable immediately

**Checkpoint**: Start exam in VirtualBox — `VIRTUAL_ENVIRONMENT` alert appears in session JSONL within 5 seconds, blocking modal appears. Dismiss — exam resumes immediately.

---

## Phase 6: User Story 4 — Screenshot and Screen Capture Blocking (Priority: P2)

**Goal**: Exam window renders as blank/black in OS screenshots. Running screen-capture tools (ShareX, OBS64, etc.) trigger a `SCREEN_CAPTURE_DETECTED` alert and blocking modal. Content protection removed on exam end.

**Independent Test**: Start exam — press PrintScreen — clipboard is empty. Open Snipping Tool — app window appears black. Launch ShareX — blocking modal appears and `SCREEN_CAPTURE_DETECTED` is in session JSONL.

### Implementation for User Story 4

- [X] T022 [US4] Implement screen-capture process detection in `python_bridge/lockdown.py`
- [X] T023 [US4] Add `mainWindow.setContentProtection(true)` call inside `activateLockdown()` in `frontend/main.js` and `mainWindow.setContentProtection(false)` inside `deactivateLockdown()`
- [X] T024 [US4] Extend `runEnvCheck()` in `frontend/main.js` to handle screen-capture detection
- [X] T025 [US4] Add `'lockdown:screen-capture-detected'` to `ALLOWED_RECEIVE_CHANNELS` in `frontend/preload.js` and expose `onLockdownCaptureDetected` via `contextBridge.exposeInMainWorld`
- [X] T026 [P] [US4] Add screen-capture violation modal markup to `frontend/pages/exam/index.html`
- [X] T027 [US4] In `frontend/pages/exam/exam.js`, wire `window.bridge.onLockdownCaptureDetected` to show `#lockdown-capture-modal`, disable interaction, and dismiss to re-enable immediately

**Checkpoint**: Start exam — Snipping Tool produces black window. Run ShareX — modal appears with `SCREEN_CAPTURE_DETECTED` in JSONL. End exam — PrintScreen and Snipping Tool work normally.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verify correctness across all exit paths, subprocess timeout safety, and simultaneous violation handling.

- [X] T028 Audit all three exam exit paths — `deactivateLockdown()` confirmed on `bridge:submit-exam`, `bridge:clear-session`, `bridge:clear-submit-result`
- [X] T029 Audit all `subprocess.run(timeout=3)` calls in `python_bridge/lockdown.py` — `TimeoutExpired` handled with `exc.process.kill()` in `_run_powershell`
- [X] T030 [P] Modal queue implemented in `frontend/pages/exam/exam.js` — simultaneous VM and capture detections are serialised; second modal only shown after first is dismissed

---

## Dependencies

```
Phase 1 (T001)
    └── Phase 2 (T002–T005)
            ├── Phase 3 US1 (T006–T010)   ← main.js window control
            │       └── Phase 4 US2 (T011–T014)  ← main.js shortcut blocking
            │               └── Phase 5 US3 (T017–T021)  ← env check + VM modal
            │                       └── Phase 6 US4 (T022–T027)  ← capture modal
            │                               └── Phase 7 (T028–T030)
            ├── Phase 5 T014–T016 [P] ← lockdown.py detection logic (independent of main.js)
            └── Phase 6 T022 [P] ← lockdown.py capture detection (independent of main.js)
```

**Parallel execution within phases**:
- T003, T004, T005 are independent (different files: server.py, main.js state, main.js helper)
- T014 (VM detection in lockdown.py) can run in parallel with T011–T013 (main.js shortcut work)
- T019, T020 are independent (preload.js vs index.html)
- T025, T026 are independent (preload.js vs index.html)

---

## Implementation Strategy

**MVP scope** (US1 + US2 — pure Electron, no backend changes):
Complete T001–T014 to deliver fully functional fullscreen enforcement and shortcut blocking with zero Python changes.

**Increment 2** (US3 — VM/RDP detection):
Complete T002–T003 (if not done) + T015–T021 to add periodic environment checking and VM violation modals.

**Increment 3** (US4 — Screenshot blocking):
Complete T022–T027 to add content protection and screen-capture process detection.

**Full delivery**:
Complete T028–T030 for cross-cutting audit and simultaneous violation handling.
