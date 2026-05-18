# Implementation Plan: Windows Executable Installer with Automated Versioning

**Branch**: `017-package-win-installer` | **Date**: 2026-05-17 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/017-package-win-installer/spec.md`

---

## Summary

Package the Lumina AI Proctoring Electron app and its Python Flask/AI backend as a single, self-contained Windows NSIS installer (`.exe`). All AI model weights, the PyInstaller-frozen Python backend, and `config.json` are bundled inside the installer — no internet connection or pre-installed runtime is needed on the end-user machine. A version-bump + build pipeline (`npm run release`) automatically increments the patch version in `package.json`, syncs it to `config.json`, freezes the Python backend with PyInstaller (`--onedir`), and produces the final installer via `electron-builder`. If the backend fails to start at runtime, a clear error dialog blocks exam access.

---

## Technical Context

**Language/Version**: Node.js 20 LTS (Electron 33) / Python 3.11+  
**Primary Dependencies**: `electron-builder` ^25 (already in devDeps), `PyInstaller` 6.x, Node `child_process` (stdlib), `fs` (stdlib)  
**Storage**: `package.json` (version source of truth), `config.json` (mirrored version + runtime config), `dist-python/server/` (PyInstaller output), `dist/` (installer output)  
**Testing**: Manual install test on clean VM per `quickstart.md`; npm script dry-runs on dev machine  
**Target Platform**: Windows 10/11 64-bit (build and install target)  
**Project Type**: Desktop app — Electron + PyInstaller packaging pipeline  
**Performance Goals**: Full build completes in under 10 minutes (SC-001); app reaches usable state within 30 seconds of launch (SC-003)  
**Constraints**: Installer is fully offline-capable (no post-install downloads); size 500 MB–1 GB; PyInstaller `--onedir` mode (not `--onefile`) to avoid startup extraction penalty; `app.isPackaged` flag gates dev vs. packaged path resolution  
**Scale/Scope**: Single build pipeline; single installer artifact per version; no concurrent build processes

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development ✅
`spec.md` complete with 3 clarification Q&As, 4 user stories, 5+ edge cases, 15 FRs (FR-001–FR-015), 7 SCs. `/speckit-clarify` completed before this plan.

### Principle II — Architecture Boundary ✅
- **Python process spawning** lives exclusively in `frontend/main.js` (Electron main process). The renderer never spawns processes or accesses `process.resourcesPath` directly.
- **Path resolution** (`app.isPackaged` gate) is in `main.js` only.
- **Health check polling** runs in main process via `net.fetch()` / `http` — same pattern as existing connectivity ping in the offline resilience feature.
- **Error dialog** (FR-014) is triggered via `dialog.showErrorBox()` from main process — no renderer IPC needed.
- **Version sync script** (`scripts/sync-version.js`) runs at build time only; it never executes in production.
- No new IPC channels. No new renderer filesystem access. No new external HTTP surfaces.

### Principle III — Design System Fidelity ✅
- No new UI screens added (error dialog uses native `dialog.showErrorBox`).
- No changes to CSS design tokens or existing pages.

### Principle IV — Security by Default ✅
- The installer bundles only: Electron app, Python bridge `.exe`, AI model files, `config.json`. No credentials, API keys, or student data are bundled.
- `config.json` contains only configuration (no secrets) — consistent with existing practice.
- PyInstaller frozen binary does not expose a new network surface; it binds to `127.0.0.1:5050` (localhost only), same as the dev server.

### Principle V — Independent Testability ✅
- Each user story in the spec has an independently testable scenario.
- `build:python` can be tested without running `build:electron`.
- `version:bump` + `version:sync` can be tested without building.
- Health check polling can be tested by killing the backend process after app launch.

**Gates: All principles satisfied. No violations. Proceed.**

---

## Project Structure

### Documentation (this feature)

```text
specs/017-package-win-installer/
├── plan.md              ← This file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── build-pipeline.md   ← npm script + runtime interface contracts
└── tasks.md             ← Phase 2 output (/speckit-tasks command)
```

### Source Code Changes

```text
package.json
└── MODIFIED:
    ├── scripts: add version:bump, version:sync, build:python,
    │            build:electron, build:installer, release
    └── build.nsis: add oneClick, createDesktopShortcut, createStartMenuShortcut,
                    shortcutName; add extraResources for dist-python/server → python-bridge

scripts/                         ← NEW directory
├── sync-version.js              ← NEW: reads package.json version → writes to config.json
└── build-python.ps1             ← NEW: PowerShell wrapper that invokes PyInstaller

python_bridge/
└── server.spec                  ← NEW: PyInstaller spec file (datas, hiddenimports, binaries)

frontend/main.js
└── MODIFIED:
    ├── Add pythonProcess spawn logic (app.isPackaged path gate)
    ├── Add startBackend() function: spawn + health-check polling loop
    ├── Add showBackendErrorDialog() using dialog.showErrorBox()
    └── Hook startBackend() into app.whenReady() before createWindow()

.gitignore
└── MODIFIED: add dist-python/, build-python/, dist/
```

---

## Complexity Tracking

No constitution violations. No complexity tracking required.
