# Implementation Plan: Offline Resilience

**Branch**: `014-offline-resilience` | **Date**: 2026-05-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/014-offline-resilience/spec.md`

## Summary

Add offline resilience to the Lumina AI Proctoring desktop app so that a temporary internet disruption never loses a student's exam progress. When a student loses connectivity (detected by a 5-second ping to the exam server), the app exits fullscreen, pauses all AI proctoring services, freezes the exam timer, and shows a dedicated offline page with a live countdown of the remaining offline budget and the count of already-answered questions. The offline page escalates visually (neutral → amber at ≤50% budget → red at ≤20% budget). If the student reconnects before the budget or disconnection limit (both configurable in `config.json`) is exhausted, the exam resumes exactly where it paused. If either limit is breached, the offline page becomes a lock screen and all answered questions auto-submit on reconnect. A local snapshot is flushed to disk on every answer change and every 30 seconds, enabling crash recovery. A session that never reconnects is flagged for instructor review.

## Technical Context

**Language/Version**: Node.js 20 LTS (Electron 33) / Python 3.11+
**Primary Dependencies**: `electron` (BrowserWindow, net.fetch, ipcMain/ipcRenderer), Flask 3.x (existing Python bridge), `fs` (Node stdlib — for local snapshot persistence)
**Storage**: `sessions/{attemptId}_offline_snapshot.json` — single-file atomic overwrite on disk, keyed by `attemptId`. JSONL session log (`sessions/{attemptId}.jsonl`) — existing, no schema change needed.
**Testing**: Manual verification per `quickstart.md`; mock JSON fixtures for ping endpoint
**Target Platform**: Windows 10/11 desktop (x64)
**Project Type**: Desktop app (Electron renderer + main process + Python Flask bridge)
**Performance Goals**: Connectivity ping round-trip < 2s; offline page shown < 3s of connection loss; exam resume < 3s of reconnection; snapshot write < 50ms
**Constraints**: Ping interval = 5s (configurable candidate); snapshot heartbeat = 30s; flicker threshold = 2s (disconnections < 2s ignored); no new npm packages required; `navigator.onLine` NOT used as the primary signal
**Scale/Scope**: Single exam session per app instance; no concurrent sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development ✅
`spec.md` complete with 5 clarification Q&As, 5 user stories, 6 edge cases, 19 FRs, 8 SCs. `/speckit-clarify` completed before this plan. Order respected.

### Principle II — Architecture Boundary ✅
- **Ping-based connectivity detection** lives in `frontend/main.js` (Electron main process) using `net.fetch()`. No renderer makes ping requests directly.
- **Offline state machine** (`offline`, `reconnected`, `locked`) is owned by `main.js`. State transitions are pushed to the renderer via `preload.js` contextBridge — same pattern as existing `bridge:ai-event`.
- **Local snapshot persistence** (`fs.writeFileSync`) runs in main process only — renderer never touches the filesystem directly.
- **Proctoring pause/resume** is signalled via existing IPC channels to the renderer, which stops/restarts polling; the Python bridge receives `stop`/`start` commands via existing Flask endpoints.
- **Auto-submit on reconnect** is triggered from `main.js` using `net.fetch()` to the LMS — same path as the existing submit flow.
- No new direct HTTP calls from the renderer. No new raw IPC channels exposed to the renderer beyond the contextBridge wrapper.

### Principle III — Design System Fidelity ✅
- Offline page and lock screen are new renderer pages (`frontend/pages/offline/`) following the existing page-per-folder convention.
- Colors via CSS custom properties from `frontend/assets/design-tokens.css`. Visual escalation states (neutral / amber / red) map to existing semantic token values — no hardcoded hex.
- Glassmorphism overlay uses `surface-container-lowest` ≥70% opacity with `backdrop-filter: blur(≥16px)`.
- Countdown animation uses CSS `@keyframes` only — no canvas, no external animation library.
- Typography: Manrope/Inter via existing font classes.

### Principle IV — Security by Default ✅
- Local snapshot contains only: `attemptId`, `currentQuestionIndex`, `answers` (student-provided data, already sent to LMS), `frozenTimerSeconds`, `lockStatus`, `offlineStats`. No tokens, no credentials, no student email in the snapshot file.
- Ping endpoint is the existing LMS `baseUrl` health route — no new surface introduced.
- Auto-submit reuses the existing submit IPC path — no new credential handling.

### Principle V — Independent Testability ✅
- Each of the 5 user stories has an Independent Test defined in `spec.md`.
- Mock ping-failure fixture allows offline state to be triggered without actually disconnecting.
- Snapshot file can be manually inspected and corrupted to test crash recovery paths.

**Gates: All 5 principles satisfied. No violations. Proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/014-offline-resilience/
├── plan.md              ← This file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   ├── offline-ipc.md        ← IPC channels between main ↔ renderer
│   └── offline-snapshot.md   ← Local snapshot file schema
└── tasks.md             ← Phase 2 output (/speckit-tasks command)
```

### Source Code Changes

```text
config.json
└── MODIFIED: add "offline_resilience" section with max_offline_minutes,
              max_disconnections, ping_interval_seconds, flicker_threshold_seconds

frontend/
├── main.js
│   └── MODIFIED: OfflineManager class — ping loop, state machine,
│                 snapshot read/write, proctoring pause/resume signals,
│                 auto-submit on reconnect, session flagging
├── preload.js
│   └── MODIFIED: add offline IPC channels to ALLOWED_RECEIVE_CHANNELS;
│                 expose onOfflineEvent, onLockEvent helpers via contextBridge
└── pages/
    └── offline/              ← NEW folder
        ├── index.html        ← NEW: offline page + lock screen markup
        └── offline.js        ← NEW: countdown render, visual escalation, lock transition

sessions/
└── {attemptId}_offline_snapshot.json  ← NEW runtime file (not committed)
```

## Complexity Tracking

No constitution violations. No complexity tracking required.
