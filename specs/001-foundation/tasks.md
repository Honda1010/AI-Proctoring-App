---
description: "Task list for 001-foundation — App Shell & Python Bridge"
---

# Tasks: Foundation — App Shell & Python Bridge

**Input**: Design documents from `specs/001-foundation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: No automated test tasks (not requested in spec). Verification is by manual inspection
per the Independent Test criteria defined in each user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and
testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository initialization, dependency declarations, and project skeleton.
No user story work can begin until this phase is complete.

- [x] T001 Initialize `package.json` with name `lumina-ai-proctoring`, version `1.0.0`, main `frontend/main.js`, and start script `electron .` at project root
- [x] T002 Add Electron 33+, keytar 7.x, and @fontsource/manrope + @fontsource/inter to `package.json` dependencies; add electron-builder as devDependency at project root
- [x] T003 [P] Create `python_bridge/requirements.txt` with `flask>=3.0.0` and `flask-cors>=4.0.0`
- [x] T004 [P] Create `.gitignore` at project root covering `node_modules/`, `python_bridge/__pycache__/`, `python_bridge/*.pyc`, `config.json`, `dist/`, and `.specify/memory/`
- [x] T005 [P] Create `config.example.json` at project root with placeholder `baseUrl` (`https://your-lms-domain.edu/api`) and default `pythonPort` (5050)
- [x] T006 Create directory skeleton: `frontend/pages/loading/`, `frontend/pages/error/`, `frontend/pages/login/`, `frontend/pages/exam-code/`, `frontend/pages/exam/`, `frontend/assets/`, `python_bridge/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config loading and validation infrastructure. Both the Electron main process and
the Python bridge depend on `AppConfig` before any user story logic can execute.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T007 Create `python_bridge/config.py` — reads `config.json` from the path passed via `--config` CLI arg
- [x] T008 Create `frontend/main.js` skeleton — imports `app`, `BrowserWindow`, `ipcMain` from electron; imports `path`, `child_process.spawn`, `fs`; reads `config.json` using `app.isPackaged` path resolution (per research.md decision 4); exports `mainWindow` and `pythonProcess` for internal use; registers `app.requestSingleInstanceLock()` quit guard (per research.md decision 5)
- [x] T009 Create `frontend/preload.js` — uses `contextBridge.exposeInMainWorld('bridge', {...})` to expose safe IPC API to renderer: `onBridgeStatus(callback)` for receiving status events, `getBridgeStatus()` for querying current state; no Node.js APIs exposed directly to renderer

**Checkpoint**: Config loading and Electron skeleton ready — user story implementation can now begin

---

## Phase 3: User Story 1 — App Launches and Bridge Comes Online (Priority: P1) 🎯 MVP

**Goal**: Electron window opens, Python bridge starts, health polling succeeds, loading and
error screens handle all failure states.

**Independent Test**: Launch app with `npm start`. Observe loading screen, then bridge-ready
state. Test failure by renaming Python executable or blocking port 5050. Verify error screen
shows specific reason in all failure cases. Run `curl http://127.0.0.1:5050/ping` to confirm
bridge response independently.

- [x] T010 [US1] Create `python_bridge/server.py` — Flask app bound to `127.0.0.1` on port from `config.py`; applies `CORS(app)` from flask-cors; registers `GET /ping` route returning `{"status": "ok", "version": "1.0.0", "timestamp": <ISO-UTC>}` with HTTP 200; uses `argparse` to accept `--port` and `--config` CLI arguments; calls `config.py` on startup and exits with code 1 + stderr message on `ConfigError`; runs with `debug=False`, `use_reloader=False`
- [x] T011 [US1] Implement bridge startup in `frontend/main.js` — `startBridge(port)` function: calls `child_process.spawn('python', ['python_bridge/server.py', '--port', port, '--config', configPath])` with inherited env; registers `pythonProcess.on('close', ...)` handler that sends `bridge-crashed` IPC event to renderer if exit code is non-zero after bridge was `ready`; implements `pollBridgeReady(url, retries=20, intervalMs=500)` loop using `net.request` or node-fetch polling `GET /ping` — returns `true` on first 200 OK, `false` after 20 retries (10s total)
- [x] T012 [US1] Implement full `app.whenReady()` startup sequence in `frontend/main.js` — create `BrowserWindow` (1200×800, `webPreferences: {preload, contextIsolation: true, nodeIntegration: false}`); load `frontend/pages/loading/loading.html` immediately; validate `AppConfig` from `config.json` before spawning bridge (send `config-error` IPC event on failure); call `startBridge(port)`; on poll success navigate to login page placeholder; on poll failure send `bridge-failed` IPC event with reason message; register `app.on('window-all-closed')` quit handler
- [x] T013 [US1] Create `frontend/pages/loading/loading.html` — full-viewport loading screen using design tokens: `surface` background, centered card with `surface-container-lowest` fill, `xl` radius, `shadow-ambient`; Manrope headline "Starting Lumina AI…"; Inter body "Connecting to the proctoring bridge, please wait."; animated spinner using `primary` gradient; listens for `bridge:status` events via `window.bridge.onBridgeStatus` and navigates on `ready` or renders error details on `failed`/`crashed`/`config-error`
- [x] T014 [US1] Create `frontend/pages/error/error.html` — standalone error screen using design tokens: `surface` background; centered card with `surface-container-lowest` fill; `xl` radius; shield icon in `tertiary` color; Manrope headline "Unable to Start"; Inter body showing dynamic `errorMessage` injected by renderer JS; secondary button "Try Again" that calls `window.location.reload()`; label chip showing error `code` (`CONFIG_ERROR`, `BRIDGE_FAILED`, `BRIDGE_CRASHED`) styled with `full` radius; no inline styles — all via design tokens

---

## Phase 4: User Story 2 — Design Tokens Power All Pages (Priority: P2)

**Goal**: All 27 design tokens from the "Ethereal Authority" design system defined as CSS
custom properties; reusable component styles for buttons, inputs, and glass modals built
from those tokens; Manrope and Inter fonts bundled offline via @fontsource.

**Independent Test**: Create a minimal `test-tokens.html` page, import `design-tokens.css`
and `components.css`, open in Electron DevTools, run
`getComputedStyle(document.documentElement).getPropertyValue('--color-primary')` — must
return `#006687`. Render each component class and visually verify against design screenshots.

- [x] T015 [P] [US2] Create `frontend/assets/design-tokens.css` — defines all 27 tokens from data-model.md as `:root` CSS custom properties across 5 categories: Color (15 tokens: `--color-primary`, `--color-primary-container`, `--color-on-primary`, `--color-secondary-container`, `--color-on-secondary-container`, `--color-tertiary`, `--color-surface`, `--color-surface-container-low`, `--color-surface-container-lowest`, `--color-surface-bright`, `--color-on-surface`, `--color-on-surface-variant`, `--color-outline-variant`, `--color-primary-fixed`, `--color-on-secondary-fixed-variant`), Typography (8 tokens: `--font-display`, `--font-body`, `--font-size-display-lg`, `--font-size-headline-md`, `--font-size-body-lg`, `--font-size-label-md`, `--letter-spacing-display`, `--letter-spacing-label`), Spacing & Radius (4 tokens: `--radius-card`, `--radius-button`, `--radius-chip`, `--spacing-md`), Shadow (4 tokens: `--shadow-ambient`, `--blur-glass`, `--opacity-glass`, `--opacity-ghost-border`), Gradient (1 token: `--gradient-primary`); includes `@import` statements for @fontsource fonts at top
- [x] T016 [P] [US2] Create `frontend/assets/components.css` — imports `design-tokens.css`; implements `.btn-primary` (gradient fill via `--gradient-primary`, `--color-on-primary` text, `--radius-button` corners, no border, `0.5rem` padding horizontal, `0.75rem` vertical, uppercase Manrope label with `--letter-spacing-label`); `.btn-secondary` (`--color-secondary-container` fill, `--color-on-secondary-container` text, same radius/padding); `.btn-tertiary` (transparent fill, `--color-primary` text, hover adds `surface-container-high` fill); `.input-field` (`--color-surface-container-lowest` fill, `outline-variant` border at `--opacity-ghost-border` opacity, `--radius-button` corners, focus transitions border to `--color-primary` 100% opacity with 4px glow spread using `--color-primary-fixed` at 30% opacity); `.glass-modal` (`--color-surface-container-lowest` fill at `--opacity-glass` opacity, `backdrop-filter: blur(--blur-glass)`, 1px ghost border at 15% opacity, `--shadow-ambient`); `.status-chip` (`--radius-chip`, `--font-size-label-md`, letter-spacing `--letter-spacing-label`, uppercase Inter); no hardcoded hex values anywhere in this file
- [x] T017 [US2] Install @fontsource packages and verify font files land in `node_modules` — run `npm install @fontsource/manrope @fontsource/inter`; verify `node_modules/@fontsource/manrope/` contains `.woff2` files; add `@import` for weights 400, 600, 700 (Manrope) and 400, 500, 600 (Inter) to top of `frontend/assets/design-tokens.css`; confirm font-family custom property values match installed package names

---

## Phase 5: User Story 3 — Runtime Configuration Is External (Priority: P3)

**Goal**: All configuration lives in `config.json`; invalid or missing config always produces
a specific, readable error — never a silent crash; HTTPS is enforced at startup.

**Independent Test**: (a) Edit `config.json` to a mock `baseUrl`, relaunch — bridge logs must
show the mock URL. (b) Set `baseUrl` to `http://…`, relaunch — error screen shows "must use
HTTPS". (c) Delete `config.json`, relaunch — error screen shows "file not found" with path.
(d) Write malformed JSON to `config.json`, relaunch — error screen shows "invalid JSON".

- [x] T018 [US3] Harden `python_bridge/config.py` — implement `ConfigError` exception class with `code` (string enum: `FILE_NOT_FOUND`, `INVALID_JSON`, `MISSING_BASE_URL`, `INSECURE_PROTOCOL`, `INVALID_PORT`) and `message` (human-readable string) attributes; implement `load_config(config_path: str) -> AppConfig` raising typed `ConfigError` for each failure case; strip trailing slash from `base_url`; emit each error to `sys.stderr` as a single-line JSON string `{"error": code, "message": message}` so Electron can parse it from the subprocess stderr stream
- [x] T019 [US3] Implement config error propagation in `frontend/main.js` — before calling `startBridge()`, read and validate `config.json` (file existence, JSON parse); on any config error send `{type: 'config-error', code, message}` IPC event to renderer and abort startup; capture `pythonProcess.stderr` stream and parse JSON error lines — on `INSECURE_PROTOCOL` or other `ConfigError` codes surface them via `{type: 'config-error', code, message}` IPC event even if emitted by Python; implement `electron-builder` `extraResources` entry for `config.json` in `package.json` build config so it lands in `resources/` when packaged

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, edge case coverage, and verification that all acceptance scenarios pass.

- [x] T020 [P] Add `config.json` to `.gitignore` and confirm `config.example.json` is tracked; add a `README.md` entry in project root documenting the setup steps from `quickstart.md` in condensed form (prereqs, `npm install`, `pip install -r requirements.txt`, copy config, `npm start`)
- [x] T021 [P] Verify single-instance lock in `frontend/main.js` — confirm `app.requestSingleInstanceLock()` is called before `app.whenReady()`; confirm `second-instance` event handler calls `mainWindow.focus()` and `mainWindow.restore()` if minimized; add a comment explaining why this prevents port 5050 conflicts on duplicate launch
- [x] T022 Add `pythonProcess.on('close')` crash recovery in `frontend/main.js` — distinguish between intentional shutdown (app quitting, `bridgeState === 'stopping'`) and unexpected crash (`bridgeState === 'ready'` at time of close); only send `bridge-crashed` IPC event for unexpected exits; ensure the event carries exit `code` and the last 3 lines of stderr for diagnostic display on the error screen
- [x] T023 [P] Create `specs/001-foundation/mocks/ping-ok.json` — mock response fixture `{"status":"ok","version":"1.0.0","timestamp":"2026-04-15T00:00:00Z"}` for use in offline development; create `specs/001-foundation/mocks/config-error-http.json` — mock IPC payload `{"type":"config-error","code":"INSECURE_PROTOCOL","message":"baseUrl must use HTTPS (https://)"}` for testing the error screen without a real misconfiguration

---

## Dependencies (User Story Completion Order)

```
Phase 1 Setup (T001–T006)
        │
        ▼
Phase 2 Foundational (T007–T009)  ← must complete before any story phase
        │
        ├──────────────────────────────────────────────────────────────┐
        ▼                                                              ▼
Phase 3 US1 (T010–T014)                               Phase 4 US2 (T015–T017)
App shell + bridge startup                             Design tokens + fonts
        │                                                              │
        └──────────────────────┬───────────────────────────────────────┘
                               ▼
                    Phase 5 US3 (T018–T019)
                    Config validation & propagation
                               │
                               ▼
                    Final Phase Polish (T020–T023)
```

**Most stories can be worked in parallel after Phase 2**:
- US1 (T010–T014) and US2 (T015–T017) have no dependency on each other
- US3 (T018–T019) depends on the config.py skeleton from T007 (Phase 2) and main.js from T008

---

## Parallel Execution Examples

### Across user stories (after T009 completes):

```
Developer A: T010 → T011 → T012 → T013 → T014   (US1: bridge startup flow)
Developer B: T015 → T016 → T017                  (US2: design tokens + fonts)
```

### Within US2 (truly independent files):

```
T015  frontend/assets/design-tokens.css   (independent — no dependencies)
T016  frontend/assets/components.css      (depends on T015 existing)
T017  npm install + font @import          (depends on T015 file existing)
```

---

## Implementation Strategy

**MVP scope** = Phase 1 + Phase 2 + Phase 3 (US1) = Tasks T001–T014 (14 tasks).

This delivers a launchable app with proper bridge startup, health polling, loading screen,
and error handling — everything needed to verify the core architecture works end-to-end
before building any UI design or config hardening.

Once MVP is running:
- Add Phase 4 (US2 — design tokens) immediately: all page specs need it
- Add Phase 5 (US3 — config) last: it enhances existing config.py from Phase 2

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 23 |
| Phase 1 (Setup) | 6 tasks (T001–T006) |
| Phase 2 (Foundational) | 3 tasks (T007–T009) |
| Phase 3 US1 — App Launches | 5 tasks (T010–T014) |
| Phase 4 US2 — Design Tokens | 3 tasks (T015–T017) |
| Phase 5 US3 — Config | 2 tasks (T018–T019) |
| Final Phase Polish | 4 tasks (T020–T023) |
| Parallelizable [P] tasks | 10 tasks |
| MVP scope (deliverable US1) | T001–T014 (14 tasks) |

**Format validation**: All 23 tasks follow `- [ ] T### [P?] [US?] Description with file path` format. ✅
