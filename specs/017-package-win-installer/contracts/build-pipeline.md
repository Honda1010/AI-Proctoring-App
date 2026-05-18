# Contract: Build Pipeline Scripts

**Feature**: `017-package-win-installer`  
**Type**: Developer-facing CLI / npm script interface  
**Phase**: 1 — Design

---

## npm Script Interface

These are the public commands a developer interacts with. All are defined in `package.json → scripts`.

### `npm run version:bump`

Increments the patch version in `package.json`.

| Property | Value |
|---|---|
| Underlying command | `npm version patch --no-git-tag-version` |
| Input | Current `package.json["version"]` |
| Output | `package.json["version"]` incremented by 1 patch (e.g. `1.0.0` → `1.0.1`) |
| Side effects | None (no git commit, no git tag) |
| Error condition | Aborts if `package.json["version"]` is not valid semver |

---

### `npm run version:sync`

Mirrors the version from `package.json` into `config.json`.

| Property | Value |
|---|---|
| Underlying command | `node scripts/sync-version.js` |
| Input | `package.json["version"]` |
| Output | `config.json["version"]` set to same value; file written atomically |
| Error condition | Aborts with non-zero exit if `config.json` cannot be parsed or written |

---

### `npm run build:python`

Runs PyInstaller to produce the frozen Python backend executable.

| Property | Value |
|---|---|
| Underlying command | `powershell -File scripts/build-python.ps1` |
| Input | `python_bridge/server.spec` |
| Output | `dist-python/server/` directory containing `server.exe` + all dependencies |
| Work directory | `build-python/` (PyInstaller cache; excluded from git) |
| Error condition | Exits non-zero if PyInstaller returns error; build pipeline aborts |

---

### `npm run build:electron`

Packages the Electron app + Python bridge into the NSIS installer.

| Property | Value |
|---|---|
| Underlying command | `electron-builder --win nsis` |
| Input | `package.json["build"]` config, `dist-python/server/` (must exist) |
| Output | `dist/Lumina AI Proctoring Setup {version}.exe` |
| Error condition | Exits non-zero if `dist-python/server/` does not exist or `electron-builder` fails |

---

### `npm run build:installer`

Full pipeline: Python build → Electron build.

| Property | Value |
|---|---|
| Underlying command | `npm run build:python && npm run build:electron` |
| Prerequisite | `version:sync` must have been run first (or use `npm run release`) |

---

### `npm run release`

Full release pipeline: bump → sync → build.

| Property | Value |
|---|---|
| Underlying command | `npm run version:bump && npm run version:sync && npm run build:installer` |
| Output | Installer at `dist/Lumina AI Proctoring Setup {new_version}.exe` |
| Expected duration | Under 10 minutes on a standard dev machine (SC-001) |

---

## Runtime Interface: Python Bridge Startup

The frozen `server.exe` exposes the same Flask HTTP interface as the dev server. The Electron main process starts it and polls its health endpoint.

### Health Endpoint

```
GET http://127.0.0.1:5050/health
```

| Response | Meaning |
|---|---|
| `200 OK` | Backend is ready; Electron opens main window |
| Connection refused / timeout | Backend not yet ready; retry (max 10 × 1s) |
| All retries exhausted | Show error dialog; block exam access (FR-014) |

### Startup Arguments (passed by Electron to `server.exe`)

| Argument | Value |
|---|---|
| `--port` | `5050` (from `config.json`) |
| `--config` | Absolute path to `config.json` in `process.resourcesPath` |

---

## Runtime Interface: Packaged Path Resolution

Electron resolves packaged vs. dev paths via `app.isPackaged`:

| Mode | Python executable path | Config path |
|---|---|---|
| Dev | `py python_bridge/server.py` | `config.json` (repo root) |
| Packaged | `<resourcesPath>/python-bridge/server.exe` | `<resourcesPath>/config.json` |
