# Tasks: Offline Resilience

**Input**: Design documents from `specs/014-offline-resilience/`
**Branch**: `014-offline-resilience`
**Date**: 2026-05-13
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. No tests were requested in the spec — no test tasks are included.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add config values and establish the new offline page folder — zero runtime behaviour changes.

- [X] T001 Add `"offline_resilience"` section to `config.json` with fields `max_offline_minutes`, `max_disconnections`, `ping_interval_seconds`, `flicker_threshold_seconds` per `data-model.md` OfflineConfig schema
- [X] T002 [P] Create folder `frontend/pages/offline/` and create empty files `frontend/pages/offline/index.html` and `frontend/pages/offline/offline.js`

**Checkpoint**: Config is readable; offline page folder exists. No behaviour change yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that must be complete before any user story can be implemented — the `OfflineManager` class in `main.js` and the IPC wiring in `preload.js`.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 In `frontend/main.js`, add an `OfflineManager` class (or module) with: constructor that reads `config.offline_resilience` fields, an in-memory `OfflineSessionStats` object per `data-model.md`, and a `state` property initialised to `'ONLINE'`
- [X] T004 In `frontend/main.js` `OfflineManager`, implement the `startPingLoop()` method: sets a `setInterval` at `ping_interval_seconds * 1000` that calls `net.fetch('HEAD', config.baseUrl)`, records success/failure, and stores `disconnectStartTime` on first failure
- [X] T005 In `frontend/main.js` `OfflineManager`, implement the flicker guard: only trigger `ONLINE → OFFLINE` transition when `Date.now() - disconnectStartTime >= flicker_threshold_seconds * 1000`
- [X] T006 In `frontend/main.js` `OfflineManager`, implement the `transitionTo(newState, lockReason)` method that fires `offline:state-changed` IPC to the renderer with the full `OfflineStateEvent` payload per `contracts/offline-ipc.md`
- [X] T007 In `frontend/main.js` `OfflineManager`, implement the 30-second snapshot heartbeat: `setInterval` that sends `offline:snapshot-request` IPC to the renderer
- [X] T008 In `frontend/preload.js`, add the four new receive channels (`offline:state-changed`, `offline:snapshot-request`, `proctoring:pause`, `proctoring:resume`) to `ALLOWED_RECEIVE_CHANNELS` and expose the five contextBridge helpers (`onOfflineStateChanged`, `onSnapshotRequest`, `onProctoringPause`, `onProctoringResume`, `sendSnapshotData`) per `contracts/offline-ipc.md`
- [X] T009 In `frontend/main.js`, add an IPC handler for `offline:snapshot-data` that passes the payload to `OfflineManager.saveSnapshot(data)` — `saveSnapshot` writes `sessions/{attemptId}_offline_snapshot.json` synchronously via `fs.writeFileSync` per `contracts/offline-snapshot.md`

**Checkpoint**: `OfflineManager` exists, ping loop starts, IPC channels are wired. No UI shown yet.

---

## Phase 3: User Story 1 — Graceful Offline Transition (Priority: P1) 🎯 MVP

**Goal**: When the student loses connectivity the app exits fullscreen and shows the offline page with a live budget countdown and answered-question count.

**Independent Test**: Disable network adapter mid-exam → offline page appears within 10 seconds with correct countdown and answered-question count.

### Implementation

- [X] T010 [US1] In `frontend/pages/offline/index.html`, build the offline page markup: container div with `id="offline-page"`, a status heading, a countdown display (`id="budget-countdown"`), an answered-questions counter (`id="answered-count"`), and a descriptive message — use design-token CSS custom properties from `frontend/assets/design-tokens.css` for all colors; apply Manrope/Inter font classes
- [X] T011 [US1] In `frontend/pages/offline/offline.js`, implement the `renderOfflinePage(payload)` function: receives the `OfflineStateEvent` payload, updates `#budget-countdown` from `budgetRemainingMs`, updates `#answered-count` from `answeredCount`, and applies the correct CSS state class (`offline--neutral`, `offline--warning`, `offline--critical`) based on `budgetRemainingMs / budgetTotalMs` thresholds (>50% neutral, ≤50% warning, ≤20% critical)
- [X] T012 [US1] In `frontend/pages/offline/offline.js`, start the local countdown `setInterval` (1-second tick) that decrements the displayed `budgetRemainingMs` each second and re-applies the escalation CSS class on each tick
- [X] T013 [US1] In `frontend/pages/exam/exam.js`, register `bridge.onOfflineStateChanged(payload => { ... })`: when `payload.state === 'OFFLINE'`, call `bridge.sendSnapshotData({currentQuestionIndex, answers, frozenTimerSeconds})` then navigate the window to `../offline/index.html`
- [X] T014 [US1] In `frontend/main.js` `OfflineManager.transitionTo()`, when transitioning to `OFFLINE`: call `mainWindow.setFullScreen(false)` and send `proctoring:pause` IPC to the renderer before firing `offline:state-changed`

**Checkpoint**: Disable network → offline page appears, countdown ticks, answered count shows. Re-enable → nothing happens yet (US2).

---

## Phase 4: User Story 2 — Seamless Reconnection & Exam Resume (Priority: P1)

**Goal**: Reconnecting before budget/limit exhaustion fades the offline page, returns fullscreen, and resumes the exam on the exact same question with the timer frozen value.

**Independent Test**: Disconnect → wait 10s → reconnect → exam resumes on same question with timer at frozen value.

### Implementation

- [X] T015 [US2] In `frontend/pages/offline/offline.js`, register `bridge.onOfflineStateChanged(payload => { ... })`: when `payload.state === 'ONLINE'`, clear the local countdown interval, apply a CSS fade-out animation to `#offline-page`, then navigate back to `../exam/index.html`
- [X] T016 [US2] In `frontend/pages/exam/exam.js`, on page load check if `window.offlineResume` flag is set (written to `sessionStorage` by the offline page before navigating back): if true, restore `currentQuestionIndex` and `answers` from the snapshot data passed via `sessionStorage`, then set the timer display to `frozenTimerSeconds`
- [X] T017 [US2] In `frontend/pages/offline/offline.js`, before navigating back to the exam page on reconnect, write `{ currentQuestionIndex, answers, frozenTimerSeconds }` (received in the last snapshot payload) to `sessionStorage` so `exam.js` can restore state on load
- [X] T018 [US2] In `frontend/main.js` `OfflineManager.transitionTo()`, when transitioning to `ONLINE` (from `OFFLINE`, non-locked): call `mainWindow.setFullScreen(true)` and send `proctoring:resume` IPC to the renderer before firing `offline:state-changed`
- [X] T019 [US2] In `frontend/pages/exam/exam.js`, register `bridge.onProctoringPause(() => { ... })` and `bridge.onProctoringResume(() => { ... })`: pause clears all AI service polling intervals; resume restarts them from `config.ui.intervals` values

**Checkpoint**: Disconnect → offline page appears. Reconnect → exam page returns, timer frozen value displayed, proctoring resumes.

---

## Phase 5: User Story 3 — Exam Lock on Budget Exhaustion or Excess Disconnections (Priority: P2)

**Goal**: Offline page transforms into lock screen when budget is exhausted or disconnection limit exceeded; answered questions auto-submit on reconnect.

**Independent Test**: Set `max_offline_minutes: 1`, stay offline 65s → lock screen appears. Reconnect → auto-submit fires.

### Implementation

- [X] T020 [US3] In `frontend/main.js` `OfflineManager`, add lock-check logic inside the ping loop: after each second of offline time, recalculate `cumulativeOfflineMs`; if `cumulativeOfflineMs >= max_offline_minutes * 60000` OR `disconnectionCount > max_disconnections`, call `transitionTo('LOCKED', reason)` immediately
- [X] T021 [US3] In `frontend/pages/offline/index.html`, add lock screen markup inside the same page (hidden by default): `id="lock-screen"` div with a lock icon, a "Exam Locked" heading, the lock reason message, and a "reconnecting…" indicator — all using design-token colors
- [X] T022 [US3] In `frontend/pages/offline/offline.js`, handle `payload.state === 'LOCKED'` in `onOfflineStateChanged`: clear the countdown interval, hide `#offline-page`, show `#lock-screen`, display the `lockReason` message (`"budget_exhausted"` or `"disconnection_limit"`)
- [X] T023 [US3] In `frontend/main.js` `OfflineManager`, implement `autoSubmitOnReconnect()`: reads `sessions/{attemptId}_offline_snapshot.json`, extracts `answers`, calls the existing LMS submit endpoint via `net.fetch()` using the stored session token, logs result to `sessions/{attemptId}.jsonl`
- [X] T024 [US3] In `frontend/main.js` `OfflineManager`, when a ping succeeds and current state is `LOCKED`, call `autoSubmitOnReconnect()` then delete the snapshot file via `fs.unlinkSync`; do NOT transition to `ONLINE`

**Checkpoint**: Budget/limit breach → lock screen. Reconnect → auto-submit fires, snapshot deleted.

---

## Phase 6: User Story 4 — App Crash & Session Recovery (Priority: P2)

**Goal**: Reopening the app after a crash restores the session at the exact point of failure; if locked before crash, lock screen is shown.

**Independent Test**: Answer questions → force-quit → reopen → same question, all answers, correct timer. Also: lock exam → force-quit → reopen → lock screen shown.

### Implementation

- [X] T025 [US4] In `frontend/main.js`, in the `app.on('ready')` / window creation path, before loading any page call `OfflineManager.tryRestoreSession()`: checks for `sessions/{attemptId}_offline_snapshot.json` existence, parses it, handles JSON parse errors gracefully (log + continue fresh)
- [X] T026 [US4] In `frontend/main.js` `OfflineManager.tryRestoreSession()`, implement restore branch for `lockStatus === 'active'`: write snapshot data to `sessionStorage` equivalent (pass as query param or via IPC), load `frontend/pages/exam/index.html`, restore `OfflineSessionStats` from `offlineStats` in the snapshot
- [X] T027 [US4] In `frontend/main.js` `OfflineManager.tryRestoreSession()`, implement restore branch for `lockStatus === 'locked'`: load `frontend/pages/offline/index.html` and pass a flag so `offline.js` immediately shows the lock screen; attempt `autoSubmitOnReconnect()` if currently online
- [X] T028 [US4] In `frontend/main.js` `OfflineManager.saveSnapshot()`, ensure the snapshot is written on every state transition (including `LOCKED`) so `lockStatus` is always up to date at crash time

**Checkpoint**: Force-quit mid-exam → reopen → correct state restored. Force-quit after lock → reopen → lock screen.

---

## Phase 7: User Story 5 — Never-Reconnected Session Flagging (Priority: P3)

**Goal**: Sessions that are locked but never result in auto-submit are flagged in the JSONL log for instructor review.

**Independent Test**: Lock exam → close app without reconnecting → check `sessions/{attemptId}.jsonl` for `OFFLINE_SESSION_FLAGGED` record.

### Implementation

- [X] T029 [US5] In `frontend/main.js`, register `app.on('before-quit')` / `app.on('will-quit')` handler: if `OfflineManager.state === 'LOCKED'` and auto-submit has NOT been triggered, call `OfflineManager.flagSessionForReview()`
- [X] T030 [US5] In `frontend/main.js` `OfflineManager`, implement `flagSessionForReview()`: appends a `OFFLINE_SESSION_FLAGGED` JSONL record to `sessions/{attemptId}.jsonl` per the `data-model.md` session flag schema (`type`, `timestamp`, `sessionId`, `reason: 'never_reconnected'`, `cumulativeOfflineMs`, `disconnectionCount`, `answeredCount`)

**Checkpoint**: Lock exam → quit app → open `sessions/{attemptId}.jsonl` → `OFFLINE_SESSION_FLAGGED` record present.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, edge cases, and UX polish across all stories.

- [X] T031 [P] In `frontend/main.js` `OfflineManager.saveSnapshot()`, add try/catch around `fs.writeFileSync`: on error, append a `SNAPSHOT_WRITE_FAILED` warning to `sessions/{attemptId}.jsonl` but do not throw (session continues in memory)
- [X] T032 [P] In `frontend/pages/offline/offline.js`, handle the `max_disconnections === 0` edge case: if `maxDisconnections === 0` and `disconnectionCount >= 1`, transition immediately to lock screen without showing offline countdown
- [X] T033 [P] In `frontend/pages/offline/offline.js`, add CSS `@keyframes` fade-in animation for the offline page appearance and fade-out for the reconnection transition — use `frontend/assets/design-tokens.css` timing variables
- [X] T034 In `frontend/main.js` `OfflineManager`, add a guard so that a ping success received within the same tick as a `LOCKED` transition does not incorrectly transition back to `ONLINE` (check `state === 'LOCKED'` before any `ONLINE` transition)
- [X] T035 Run all 8 manual test scenarios from `specs/014-offline-resilience/quickstart.md` and resolve any failures

**Checkpoint**: All edge cases handled, animations smooth, all quickstart tests pass.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — first deliverable (MVP)
- **US2 (Phase 4)**: Depends on Phase 3 (needs the offline page navigation from US1)
- **US3 (Phase 5)**: Depends on Phase 2 — can be worked in parallel with US1/US2 after foundation
- **US4 (Phase 6)**: Depends on Phase 2 and T009 (snapshot save) — independent of US1–US3 UI
- **US5 (Phase 7)**: Depends on Phase 5 (needs `lockStatus` to be set)
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|-----------|-------------------|
| US1 (P1) | Phase 2 complete | — |
| US2 (P1) | US1 complete (needs offline page) | US3, US4 |
| US3 (P2) | Phase 2 complete | US4 |
| US4 (P2) | Phase 2 + T009 | US3 |
| US5 (P3) | US3 complete | — |

### Within Each Phase

- Models/data before services
- IPC channels before UI consumers
- `OfflineManager` methods before the renderer code that calls them via IPC

---

## Parallel Execution Example: Foundation Phase

```
After T001–T002 (Setup):
  T003 OfflineManager class skeleton         ← must be first
  T004 startPingLoop()                       ← after T003
  T005 flicker guard                         ← after T003
  T006 transitionTo()                        ← after T003
  T007 snapshot heartbeat                    ← after T003
  T008 [P] preload.js IPC channels           ← parallel with T004–T007
  T009 snapshot-data IPC handler             ← after T008
```

## Parallel Execution Example: US3 & US4 (after Foundation)

```
T020–T024 (US3 lock + auto-submit)      ← parallel track A
T025–T028 (US4 crash recovery)          ← parallel track B
Both depend only on Foundation — no cross-dependency
```

---

## Implementation Strategy

### MVP (User Story 1 only — Phases 1–3)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundation (T003–T009)
3. Complete Phase 3: US1 offline transition (T010–T014)
4. **STOP & VALIDATE**: Disable network adapter → offline page appears with countdown and answered count
5. Demo / review before proceeding

### Incremental Delivery

1. Phases 1–3 → Offline page visible *(MVP)*
2. Phase 4 → Reconnection resumes exam
3. Phase 5 → Exam locks; auto-submit
4. Phase 6 → Crash recovery
5. Phase 7 → Session flagging
6. Phase 8 → Polish & quickstart validation

---

## Notes

- [P] tasks operate on different files or are fully independent — safe to run in parallel
- Each user story phase is independently testable per its **Independent Test** definition
- No new npm packages are required — only Electron built-ins and Node stdlib (`fs`, `net`)
- The Python bridge requires zero changes for this feature
- Restore `max_offline_minutes` and `max_disconnections` in `config.json` to production values after testing
