# Implementation Plan: Exam Lockdown

**Branch**: `013-exam-lockdown` | **Date**: 2026-05-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-exam-lockdown/spec.md`

## Summary

Implement four independent exam lockdown controls in the Lumina AI Proctoring desktop app:
1. **Fullscreen enforcement** — frameless kiosk window, always-on-top, close-guarded, auto-re-enters fullscreen on OS-forced exit, logs `FULLSCREEN_ESCAPE_ATTEMPT`.
2. **Keyboard shortcut blocking** — dual-layer (globalShortcut + before-input-event) for all interceptable shortcuts; close event guard for Alt+F4.
3. **VM and remote desktop detection** — new `POST /check-environment` Flask endpoint + 60-second periodic IPC-driven check; appends `VIRTUAL_ENVIRONMENT` alerts; shows blocking modal.
4. **Screenshot blocking** — `setContentProtection(true)` on exam start; screen-capture process detection via same `/check-environment` endpoint; appends `SCREEN_CAPTURE_DETECTED` alerts.

All controls activate when `examSession` is set in `frontend/main.js` and are fully released on all three exit paths: `bridge:submit-exam`, `bridge:clear-session`, `bridge:clear-submit-result`.

## Technical Context

**Language/Version**: Node.js 20 LTS (Electron 33+) / Python 3.11+
**Primary Dependencies**: `electron` (globalShortcut, BrowserWindow APIs), Flask 3.x, `psutil` (already in requirements), `winreg` (Python stdlib), `platform` (Python stdlib), `subprocess` (Python stdlib)
**Storage**: `sessions/{attemptId}.jsonl` — JSONL append-only, best-effort, no new schema
**Testing**: Manual verification per `quickstart.md`; mock fixture for `/check-environment`
**Target Platform**: Windows 10/11 desktop (x64) — Windows-only feature
**Project Type**: Desktop app (Electron renderer + main process + Python Flask bridge)
**Performance Goals**: Shortcut block < 50ms; fullscreen re-entry < 1s; env check < 5s per cycle
**Constraints**: 3-second timeout per subprocess call; explicit `proc.kill()` on TimeoutExpired; OS-reserved shortcuts (Win+D, Win+L, Alt+Tab, Ctrl+Shift+Esc) accepted as unblockable; `setContentProtection(true)` compensates for unblockable Win+PrintScreen and Win+Shift+S
**Scale/Scope**: Single exam session per app instance; no concurrent sessions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development ✅
`spec.md` complete with 5 clarifications, 4 user stories, 17 FRs, and 7 SCs. Clarification (`/speckit.clarify`) completed before this plan. Order respected.

### Principle II — Architecture Boundary ✅
- All window management (`setFullScreen`, `setKiosk`, `setContentProtection`, `globalShortcut`) lives in `frontend/main.js` (Electron main process). No renderer touches these APIs directly.
- VM/RDP/screen-capture detection lives in `python_bridge/lockdown.py` (new Flask blueprint). Called via `net.fetch()` from `main.js` — not directly from the renderer.
- Renderer receives `lockdown:vm-detected` and `lockdown:screen-capture-detected` push events through `preload.js` contextBridge — same pattern as `bridge:ai-event`. No raw IPC exposed.
- No LMS API calls introduced by this feature. No new direct HTTP calls from the renderer.

### Principle III — Design System Fidelity ✅
- Violation blocking modals reuse the `modal-backdrop` + `modal-glass` pattern from `frontend/pages/exam/index.html`.
- Colors via CSS custom properties from `frontend/assets/design-tokens.css` — no hardcoded hex values.
- Glassmorphism overlay: `surface-container-lowest` ≥70% opacity with `backdrop-filter: blur(≥16px)`.
- Typography: Manrope/Inter via existing CSS classes.

### Principle IV — Security by Default ✅
- JSONL alert records contain only: `type`, `timestamp`, `sessionId`, `reason`. No tokens, no credentials, no student email.
- `reason` strings are generated internally from detection logic — never from user input, never from LMS responses.
- Content protection prevents exam content exfiltration via OS screenshot pipelines.
- No new credential handling introduced.

### Principle V — Independent Testability ✅
- Each of the 4 user stories has an Independent Test defined in `spec.md`.
- Mock fixture for `/check-environment` stored in `specs/013-exam-lockdown/mocks/`.
- The Python `lockdown.py` blueprint can be tested independently via `curl` or `pytest`.

**Gates: All 5 principles satisfied. No violations. Proceed to implementation.**

## Project Structure

### Documentation (this feature)

```text
specs/013-exam-lockdown/
├── plan.md              ← This file
├── research.md          ← Phase 0 output (OS key limitations, WMIC deprecation, psutil facts)
├── data-model.md        ← Phase 1 output (EnvironmentCheckResult, LockdownAlertRecord, etc.)
├── quickstart.md        ← Phase 1 output (manual verification steps)
├── contracts/
│   └── check-environment.md  ← POST /check-environment contract + IPC push channels
├── mocks/
│   └── check-environment-clean.json   ← clean result fixture
│   └── check-environment-vm.json      ← VM detected fixture
│   └── check-environment-capture.json ← screen capture detected fixture
└── tasks.md             ← Phase 2 output (/speckit.tasks command)
```

### Source Code Changes

```text
python_bridge/
├── lockdown.py           ← NEW: Flask blueprint with POST /check-environment
├── server.py             ← MODIFIED: register lockdown_bp
└── requirements.txt      ← VERIFY: psutil already present (no new deps needed)

frontend/
├── main.js               ← MODIFIED: globalShortcut, setKiosk, setContentProtection,
│                                       close event guard, leave-full-screen handler,
│                                       envCheckInterval, lockdownActive,
│                                       appendLockdownAlert(), runEnvCheck(),
│                                       bridge:check-environment IPC,
│                                       lockdown cleanup on all 3 exit paths
├── preload.js            ← MODIFIED: add lockdown:vm-detected, lockdown:screen-capture-detected
│                                       to ALLOWED_RECEIVE_CHANNELS; expose onLockdownEvent helpers
└── pages/exam/
    ├── index.html        ← MODIFIED: add lockdown violation modal markup (vm + screen-capture)
    └── exam.js           ← MODIFIED: handle lockdown IPC events, show/hide violation modal

specs/013-exam-lockdown/
└── mocks/                ← NEW: /check-environment fixture files
```

## Complexity Tracking

No constitution violations. No complexity tracking required.
