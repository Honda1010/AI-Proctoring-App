# Tasks: Windows Executable Installer with Automated Versioning

**Feature**: `017-package-win-installer`  
**Input**: Design documents from `specs/017-package-win-installer/`  
**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/build-pipeline.md ✅ · quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to (US1–US4)
- Exact file paths are included in every description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — new files and directories the pipeline needs to exist before any build work begins.

- [ ] T001 Create `scripts/` directory at repo root for build and version utilities
- [ ] T002 [P] Add `dist-python/`, `build-python/`, and `dist/` to `.gitignore` so build artifacts are never committed
- [ ] T003 [P] Add `version` field to `config.json` mirroring the current `package.json` version (`"version": "1.0.0"`)

**Checkpoint**: Directory scaffold and gitignore in place — ready for Phase 2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before any user story can be implemented. All stories depend on the version pipeline (T004–T006) and the PyInstaller spec (T007–T008) being in place.

⚠️ **CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Write `scripts/sync-version.js` — reads `package.json["version"]` and writes it to `config.json["version"]`; exits non-zero if either file cannot be parsed or written
- [ ] T005 [P] Add npm scripts to `package.json`: `version:bump` (`npm version patch --no-git-tag-version`), `version:sync` (`node scripts/sync-version.js`), `build:python` (`powershell -ExecutionPolicy Bypass -File scripts/build-python.ps1`), `build:electron` (`electron-builder --win nsis`), `build:installer` (`npm run build:python && npm run build:electron`), `release` (`npm run version:bump && npm run version:sync && npm run build:installer`)
- [ ] T006 [P] Update `package.json → build.nsis` section: add `oneClick: false`, `allowToChangeInstallationDirectory: false`, `createDesktopShortcut: true`, `createStartMenuShortcut: true`, `shortcutName: "Lumina AI Proctoring"` — satisfies FR-005, FR-009
- [ ] T007 Write `python_bridge/server.spec` — PyInstaller spec file with: entry point `python_bridge/server.py`, `--onedir` mode, `datas` entries for `AI/models/*.weights`, `AI/models/*.cfg`, `AI/models/*.names`, `AI/models/*.pb`, `AI/models/*.onnx`, `config.json`; `hiddenimports` for `flask`, `cv2`, `numpy`, `mediapipe`, `imutils`; `binaries` via `collect_binaries('cv2')` — satisfies FR-003, FR-013, FR-015
- [ ] T008 Write `scripts/build-python.ps1` — PowerShell wrapper that runs `pyinstaller python_bridge/server.spec --distpath dist-python --workpath build-python --noconfirm`; exits with non-zero code on PyInstaller failure

**Checkpoint**: Version pipeline scripts and PyInstaller spec are in place. User story phases can begin.

---

## Phase 3: User Story 1 — End-User Installs the Application (Priority: P1) 🎯 MVP

**Goal**: Produce a working NSIS installer that a user on a clean Windows 10/11 machine can run to get the fully functional app (frontend + AI backend) installed and launchable from a shortcut — satisfying FR-001 through FR-006, FR-009, FR-010, FR-013, FR-015.

**Independent Test**: Build the installer (`npm run build:installer`), copy it to a clean VM, run it, launch from shortcut — verify the exam interface loads and AI monitoring starts within 30 seconds (SC-003).

### Implementation for User Story 1

- [ ] T009 [US1] Update `package.json → build.extraResources` to copy `dist-python/server` folder → `python-bridge` inside the packaged app's resource directory (satisfies FR-002, FR-003 bundling together)
- [ ] T010 [US1] Modify `frontend/main.js`: add `startBackend()` function that (a) resolves the server executable path via `app.isPackaged` gate — packaged: `path.join(process.resourcesPath, 'python-bridge', 'server.exe')`, dev: uses existing `py python_bridge/server.py` — and (b) spawns it with `child_process.spawn()` passing `--port 5050 --config <configPath>` args; stores reference in module-level `pythonProcess` variable
- [ ] T011 [US1] Add health-check polling loop in `frontend/main.js` inside `startBackend()`: poll `http://127.0.0.1:5050/health` up to 10 times with 1-second intervals using `net.fetch()`; on success proceed to `createWindow()`; on all retries exhausted call `showBackendErrorDialog()` (satisfies FR-006, FR-014)
- [ ] T012 [US1] Add `showBackendErrorDialog()` function in `frontend/main.js` using `dialog.showErrorBox()` that displays: title "AI Monitoring Service Failed to Start", message explaining the backend could not be reached and the exam cannot proceed — satisfies FR-014
- [ ] T013 [US1] Hook `startBackend()` into `app.whenReady()` in `frontend/main.js` so it runs before `createWindow()` is called — ensures backend is healthy before the exam UI appears
- [ ] T014 [US1] Add graceful shutdown in `frontend/main.js`: on `app.on('before-quit')` / `app.on('will-quit')`, call `pythonProcess.kill()` if `pythonProcess` is alive — satisfies the acceptance scenario "all background services stop cleanly with no orphaned processes" (US1 scenario 3)
- [ ] T015 [US1] Resolve packaged `config.json` path in `frontend/main.js`: when `app.isPackaged`, read config from `path.join(process.resourcesPath, 'config.json')` instead of the dev-relative path; pass this resolved path as `--config` arg to `startBackend()`
- [ ] T016 [US1] Run `npm run build:python` and verify `dist-python/server/server.exe` is produced — first build smoke-test of the PyInstaller pipeline
- [ ] T017 [US1] Run `npm run build:electron` and verify `dist/Lumina AI Proctoring Setup 1.0.0.exe` is produced — confirms `extraResources`, NSIS config, and electron-builder integration are correct
- [ ] T018 [US1] Install produced `.exe` on a test machine (or current machine); verify Desktop + Start Menu shortcuts are created; verify app launches and reaches a usable state within 30 seconds — satisfies SC-002, SC-003, FR-005

**Checkpoint**: US1 complete — end-user can install and run the app from the installer on a clean machine.

---

## Phase 4: User Story 2 — Developer Runs the Build to Produce a New Release (Priority: P2)

**Goal**: The full `npm run build:installer` pipeline runs reliably end-to-end, producing a correctly named installer whose filename matches the project version (satisfies FR-007, FR-011, SC-001, SC-004, SC-006).

**Independent Test**: On a dev machine with all tools installed, run `npm run build:installer` and verify the output filename contains the current `package.json` version. Time the build — must complete in under 10 minutes (SC-001).

### Implementation for User Story 2

- [ ] T019 [US2] Verify `build.directories.output` in `package.json` is set to `dist` and that `electron-builder` names the output file using `productName` + `version` — confirms FR-007 (version embedded in filename) and FR-011 (configurable output dir) without code changes if already correct; document if any adjustment is needed
- [ ] T020 [US2] Add error guard in `scripts/build-python.ps1`: if `dist-python/server/server.exe` does not exist after PyInstaller completes, write an error message to stderr and exit with code 1 — prevents a silent partial build from producing a broken installer
- [ ] T021 [US2] Add pre-build check in `package.json → build:electron` script (or via an `electron-builder` beforeBuild hook) that aborts with a clear message if `dist-python/server` directory is missing — prevents `npm run build:electron` from producing an installer without the Python backend
- [ ] T022 [US2] Run `npm run build:installer` (full pipeline) and record the elapsed time; verify output installer filename matches `package.json` version exactly — validates SC-001 and SC-004
- [ ] T023 [US2] Install the produced installer and run a full dev-mode parity check: confirm every feature available in `npm start` dev mode is also functional in the installed version — validates SC-006

**Checkpoint**: US2 complete — the build pipeline reliably produces a correctly versioned installer in under 10 minutes.

---

## Phase 5: User Story 3 — Developer Increments the Version (Priority: P2)

**Goal**: `npm run version:bump` + `npm run version:sync` atomically increments the patch version in `package.json` and mirrors it to `config.json`, so the next build picks up the new version without any manual file editing (satisfies FR-008, SC-004, SC-005).

**Independent Test**: Run `npm run version:bump` (observe `package.json` increments), then `npm run version:sync` (observe `config.json` matches), then `npm run build:electron` (observe installer filename uses new version) — no manual file edits at any step.

### Implementation for User Story 3

- [ ] T024 [US3] Verify `npm run version:bump` correctly increments `package.json["version"]` from `1.0.0` → `1.0.1` and does not create a git commit or tag (`--no-git-tag-version` flag is present in T005 — confirm it works)
- [ ] T025 [US3] Verify `npm run version:sync` reads the updated `package.json["version"]` and writes it to `config.json["version"]` atomically; verify `config.json` is valid JSON after the write
- [ ] T026 [US3] Run the full release chain twice in sequence: first `npm run release` (produces `1.0.1`), then `npm run release` again (produces `1.0.2`); verify each output installer filename is correctly incremented and no version is repeated — validates SC-005 sequential uniqueness
- [ ] T027 [US3] Add a guard in `scripts/sync-version.js`: if `package.json["version"]` is not a valid semver string, log an error to stderr and exit with code 1 — prevents corrupted version strings from propagating to the installer

**Checkpoint**: US3 complete — version bumping and syncing is fully automated and sequential.

---

## Phase 6: User Story 4 — End-User Installs a New Version Over an Existing One (Priority: P3)

**Goal**: Running a newer version's NSIS installer on a machine with an older version already installed completes without errors and upgrades the installation in-place — satisfying FR-012, SC-007.

**Independent Test**: Install v1.0.0, then run v1.0.1 installer on the same machine; verify app launches as v1.0.1 with no error dialogs, no leftover v1.0.0 files, and no manual uninstall required.

### Implementation for User Story 4

- [ ] T028 [US4] Confirm `package.json → build.appId` is `com.lumina.proctoring` and has not changed from any previous build — this is the Windows Registry upgrade key; changing it would break upgrade detection
- [ ] T029 [US4] Build installer v1.0.0 (`npm run build:installer` at current version), install it on a test machine; then run `npm run version:bump && npm run version:sync && npm run build:installer` to produce v1.0.1; install v1.0.1 over the existing v1.0.0 installation without uninstalling first
- [ ] T030 [US4] Verify after upgrade: (a) app launches without error, (b) in-app version reads `1.0.1`, (c) Windows "Add or Remove Programs" shows only one entry for the app at v1.0.1, (d) no orphaned `v1.0.0` files remain in the install directory — satisfies FR-010, FR-012, SC-007

**Checkpoint**: US4 complete — upgrade path is clean and verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Hardening, documentation, and cleanup that improves the overall build pipeline quality across all user stories.

- [ ] T031 [P] Update `README.md` at repo root: add a "Building a Release" section referencing `specs/017-package-win-installer/quickstart.md` with the one-liner `npm run release`
- [ ] T032 [P] Add `dist/`, `dist-python/`, `build-python/` entries to `.gitignore` (verify T002 entries are correct and complete; add `*.spec` exclusion guard if needed)
- [ ] T033 [P] Add `app.on('child-process-gone')` / process exit-code logging in `frontend/main.js` so that if `pythonProcess` crashes post-startup, the error is written to the Electron log (not silently swallowed) — aids debugging of post-install issues
- [ ] T034 Validate the full quickstart flow end-to-end on a clean Windows 11 machine following `specs/017-package-win-installer/quickstart.md` exactly — confirm all steps produce the expected results with no undocumented prerequisites

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS all user stories
    ↓
Phase 3 (US1 - P1) ← MVP — complete this first
Phase 4 (US2 - P2) ← can start after Phase 2; builds on Phase 3 artifacts
Phase 5 (US3 - P2) ← can start after Phase 2; independent of US1/US2 implementation
Phase 6 (US4 - P3) ← requires Phase 3 + Phase 5 to produce two versioned installers
    ↓
Phase 7 (Polish) ← after all desired stories complete
```

### User Story Dependencies

| Story | Depends on | Independent? |
|---|---|---|
| US1 (P1) | Phase 2 complete | ✅ Yes |
| US2 (P2) | Phase 2 + US1 artifacts (the built installer) | Mostly — US2 validates the US1 pipeline output |
| US3 (P2) | Phase 2 complete (T004, T005) | ✅ Yes — version scripts are standalone |
| US4 (P3) | US1 (v1.0.0 installer) + US3 (version bump → v1.0.1 installer) | Depends on US1 + US3 |

### Within Each User Story

- Phase 2 tasks T004–T008 can proceed in parallel where marked `[P]`
- T010, T011, T012 within US1 are sequential (health check depends on `startBackend`, dialog depends on health check)
- T016, T017, T018 within US1 are sequential (build:python → build:electron → install test)

### Parallel Opportunities

- T002, T003 in Phase 1 can run in parallel with each other
- T005, T006 in Phase 2 can run in parallel (different files: `package.json` scripts vs `package.json` build config — both target the same file so coordinate carefully; treat as sequential if one developer)
- T007, T008 in Phase 2 can run in parallel with T005/T006 (different files: `server.spec` and `build-python.ps1`)
- T031, T032, T033 in Phase 7 can all run in parallel

---

## Parallel Example: Phase 2 Foundational

```text
# Group A — can start immediately (different files):
T004  scripts/sync-version.js
T007  python_bridge/server.spec
T008  scripts/build-python.ps1

# Group B — after T004 is drafted (same file package.json, coordinate):
T005  package.json → scripts
T006  package.json → build.nsis
```

## Parallel Example: Phase 7 Polish

```text
# All can run simultaneously:
T031  README.md update
T032  .gitignore verification
T033  frontend/main.js crash logging
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — Phases 1–3)

1. Complete **Phase 1** (Setup — ~15 min)
2. Complete **Phase 2** (Foundational — ~45 min) ← CRITICAL gate
3. Complete **Phase 3** (US1 — ~90 min including first build)
4. **STOP and VALIDATE**: Install the produced `.exe` on a clean machine; verify SC-001, SC-002, SC-003
5. Ship v1.0.0 installer if validation passes

### Incremental Delivery

| Step | What's delivered | Validation |
|---|---|---|
| Phase 1+2+3 | Working installer v1.0.0 | Install test on clean VM |
| + Phase 4 | Reliable build pipeline with timing + parity proof | Build twice; time it; parity check |
| + Phase 5 | Automated version bumping | Two sequential `npm run release` runs |
| + Phase 6 | Verified upgrade path | Upgrade v1.0.0 → v1.0.1 test |
| + Phase 7 | Polish + docs | Quickstart walkthrough on clean machine |

---

## Notes

- `[P]` tasks target different files or are otherwise non-conflicting — safe to run simultaneously
- `[Story]` label maps each task to its user story for full traceability back to `spec.md`
- The PyInstaller `--onedir` output (`dist-python/server/`) must exist **before** `npm run build:electron` runs — this is enforced by T021
- `app.isPackaged` is the single gate for dev vs. packaged path resolution in `main.js` — never use `process.env.NODE_ENV` for this
- Each user story phase ends with a concrete installation/validation step, not just a code-complete step
- Commit after each phase checkpoint using `/speckit-git-commit`
