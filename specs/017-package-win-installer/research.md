# Research: Windows Executable Installer with Automated Versioning

**Feature**: `017-package-win-installer`  
**Date**: 2026-05-17  
**Phase**: 0 — Unknowns resolution

---

## R-001: PyInstaller Integration with electron-builder (NSIS)

**Decision**: Use `electron-builder`'s `extraResources` field to copy the PyInstaller-produced folder (`dist-python/`) into the Electron app's resource directory. At runtime, Electron resolves the path via `process.resourcesPath`.

**Rationale**: `extraResources` is the canonical `electron-builder` mechanism for embedding non-JS assets. The PyInstaller `--onedir` mode (a folder, not a single `.exe`) is preferred over `--onefile` because:
- `--onefile` unpacks to a temp directory on every launch, adding 3–10s cold-start latency.
- `--onedir` is available immediately — no extraction step.
- The folder approach survives Windows Defender scanning better than a self-extracting archive.

**Implementation pattern**:
```json
// package.json  →  build.extraResources
{
  "from": "dist-python/server",
  "to": "python-bridge"
}
```
The frozen executable is then at `<resourcesPath>/python-bridge/server.exe` at runtime.

**Alternatives considered**:
- `--onefile` PyInstaller: rejected due to startup latency and AV false-positive risk.
- Embedding a portable Python interpreter (copy entire CPython): rejected — 300 MB overhead without the dependency resolution benefits of PyInstaller.
- cx_Freeze: viable alternative but narrower community support and less reliable with OpenCV/numpy on Windows.

---

## R-002: Spawning the Frozen Python Backend from Electron main.js

**Decision**: In `frontend/main.js`, after `app.whenReady()`, spawn the PyInstaller executable as a `child_process` using Node's `child_process.spawn()`. The path is resolved dynamically based on whether the app is packaged (`app.isPackaged`).

**Rationale**: This is the standard Electron pattern for companion processes. The existing dev-mode startup already spawns `py python_bridge/server.py` — the packaged path simply swaps in `process.resourcesPath + '/python-bridge/server.exe'`.

**Implementation pattern**:
```js
const serverPath = app.isPackaged
  ? path.join(process.resourcesPath, 'python-bridge', 'server.exe')
  : 'py';
const serverArgs = app.isPackaged
  ? ['--port', '5050', '--config', configPath]
  : ['python_bridge/server.py', '--port', '5050', '--config', 'config.json'];

pythonProcess = spawn(serverPath, serverArgs, { stdio: 'pipe' });
pythonProcess.on('error', () => showBackendErrorDialog());
```

**Startup health check**: Poll `http://127.0.0.1:5050/health` with up to 10 retries (1s apart) before opening the main window. If all retries fail, display error dialog (FR-014) and keep window showing error state.

**Alternatives considered**:
- `child_process.exec()`: rejected — no reliable stream access for error detection.
- Starting Python from a shell script: rejected — adds complexity and shell dependency.

---

## R-003: Automated Version Bumping (Single Source of Truth)

**Decision**: `package.json` is the single source of truth for the version. A dedicated npm script (`version:bump`) calls `npm version patch --no-git-tag-version`, which increments `package.json` in place. A second script (`version:sync`) reads `package.json` and writes the `version` field into `config.json`.

**Rationale**: `npm version patch` is the standard, atomic version bumping tool — it validates semver, increments correctly, and never produces duplicates. Adding `--no-git-tag-version` prevents automatic git tagging (the developer controls when to tag). Writing to `config.json` keeps the runtime config in sync so the Python bridge can also read the version.

**Implementation pattern**:
```json
// package.json scripts
"version:bump": "npm version patch --no-git-tag-version",
"version:sync": "node scripts/sync-version.js",
"release": "npm run version:bump && npm run version:sync && npm run build:installer"
```

```js
// scripts/sync-version.js
const pkg = require('../package.json');
const cfg = require('../config.json');
cfg.version = pkg.version;
fs.writeFileSync('config.json', JSON.stringify(cfg, null, 2));
```

**Alternatives considered**:
- Manual version editing: rejected — error-prone, violates FR-008.
- Using a separate version file (`VERSION`): rejected — introduces a third source of truth.
- `standard-version` / `semantic-release`: rejected — over-engineered for a single-developer release workflow; adds changelog tooling not requested.

---

## R-004: PyInstaller Spec File for Flask + OpenCV + Detection Models

**Decision**: Use a hand-authored `.spec` file (`python_bridge/server.spec`) instead of relying on PyInstaller auto-analysis alone. This allows explicit inclusion of:
- `datas` entries for model weight files (`.weights`, `.cfg`, `.names`, `.pb`, `.onnx`)  
- Hidden imports for `flask`, `cv2`, `numpy`, `mediapipe`, `imutils`
- `binaries` for any DLLs OpenCV needs (e.g., `msvcp140.dll` collected via `collect_binaries('cv2')`)

**Rationale**: PyInstaller's auto-analysis misses dynamically-imported modules (common in Flask, OpenCV, and ML libraries). The `.spec` file gives deterministic, reproducible builds. Model files must be listed explicitly via `datas` since PyInstaller doesn't scan for binary assets.

**Key `.spec` patterns**:
```python
datas = [
    ('AI/models/*.weights', 'AI/models'),
    ('AI/models/*.cfg',     'AI/models'),
    ('AI/models/*.names',   'AI/models'),
    ('config.json',         '.'),
]
hiddenimports = ['flask', 'cv2', 'numpy', 'mediapipe', 'imutils', 'sklearn']
```

**Build command**:
```bash
pyinstaller python_bridge/server.spec --distpath dist-python --workpath build-python --noconfirm
```

**Alternatives considered**:
- `--collect-all` flag: collects everything from a package but inflates bundle size significantly and may still miss non-package assets.
- PyInstaller hooks directory: valid alternative for very complex packages; spec file chosen for simplicity.

---

## R-005: NSIS Installer Upgrade Behaviour (electron-builder)

**Decision**: Set `nsis.allowToChangeInstallationDirectory: false` and `nsis.oneClick: false` (wizard mode) in `package.json`. The `appId` (`com.lumina.proctoring`) is the NSIS upgrade key — when the same `appId` is seen, NSIS replaces the existing installation automatically without prompting for uninstall.

**Rationale**: `electron-builder`'s NSIS generator uses the `appId` as a Windows Registry `DisplayName` key. Running a newer-version installer with the same `appId` triggers NSIS's built-in upgrade path, satisfying FR-012. The wizard mode (`oneClick: false`) satisfies FR-009 (standard Next/Install/Finish flow).

**Key config**:
```json
"nsis": {
  "oneClick": false,
  "allowToChangeInstallationDirectory": false,
  "createDesktopShortcut": true,
  "createStartMenuShortcut": true,
  "shortcutName": "Lumina AI Proctoring"
}
```

**Alternatives considered**:
- `oneClick: true` (silent install): rejected — doesn't satisfy FR-009 (wizard flow required).
- Custom NSIS script: rejected — `electron-builder` handles upgrade logic correctly without custom scripting for this use case.

---

## R-006: Build Pipeline Orchestration

**Decision**: Define three npm scripts that can be run independently or chained:
1. `build:python` — runs PyInstaller via a PowerShell/shell wrapper
2. `build:electron` — runs `electron-builder --win nsis`
3. `build:installer` — runs `build:python` then `build:electron` in sequence

A thin PowerShell script (`scripts/build.ps1`) wraps the Python build step so developers on Windows can run a single `npm run release` that bumps version, syncs config, builds Python, and builds the Electron installer.

**SC-001 target**: Full build (PyInstaller + electron-builder) on a modern dev machine completes in under 10 minutes.

**Alternatives considered**:
- Makefile: cross-platform but adds tooling dependency not present in the project.
- GitHub Actions CI: valid for automated releases, but the spec targets local developer workflow first.
