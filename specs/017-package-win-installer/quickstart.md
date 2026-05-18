# Quickstart: Building the Windows Installer

**Feature**: `017-package-win-installer`  
**Audience**: Developer running the build on Windows 10/11

---

## Prerequisites

Ensure these are installed on the **build machine** (not required on end-user machines):

| Tool | Version | Check |
|---|---|---|
| Node.js | 20 LTS | `node --version` |
| Python | 3.11+ | `python --version` |
| PyInstaller | 6.x | `pyinstaller --version` |
| All Python deps | (from `requirements.txt`) | `pip install -r requirements.txt` |
| electron-builder | (auto via devDeps) | `npx electron-builder --version` |

> **Note**: The end-user machine does **not** need any of these. The installer is fully self-contained.

---

## First-Time Setup

```powershell
# 1. Install Node dependencies (if not already done)
npm install

# 2. Install Python dependencies (if not already done)
pip install -r requirements.txt
pip install pyinstaller
```

---

## Producing a Release Installer

### Option A — Full Release (recommended)

Bumps version, syncs config, builds everything:

```powershell
npm run release
```

Output: `dist\Lumina AI Proctoring Setup 1.0.X.exe`

---

### Option B — Manual Step-by-Step

```powershell
# Step 1: Bump patch version (1.0.0 → 1.0.1)
npm run version:bump

# Step 2: Mirror version into config.json
npm run version:sync

# Step 3: Freeze Python backend with PyInstaller
npm run build:python

# Step 4: Package Electron app + Python into NSIS installer
npm run build:electron
```

---

## Checking the Output

```powershell
# List the dist/ directory — should contain the versioned .exe
Get-ChildItem dist\

# Expected output:
#   Lumina AI Proctoring Setup 1.0.X.exe
```

---

## Testing the Installer on a Clean Machine

1. Copy `dist\Lumina AI Proctoring Setup 1.0.X.exe` to a clean Windows 10/11 VM or machine with no dev tools.
2. Run the installer — click **Next → Install → Finish**.
3. Launch **Lumina AI Proctoring** from the Desktop shortcut.
4. Verify: the exam interface loads within 30 seconds (SC-003).
5. Verify: no error dialog appears (backend started successfully).
6. Run through a test exam session to confirm all features work.

---

## Upgrading an Existing Installation

Simply run the newer version's installer on a machine where an older version is already installed. The installer will replace the old version automatically — no manual uninstall required (FR-012).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `pyinstaller: command not found` | PyInstaller not installed | `pip install pyinstaller` |
| `dist-python/server` missing when running `build:electron` | `build:python` not run first | Run `npm run build:python` first |
| Error dialog on launch: "AI monitoring service failed to start" | Backend `.exe` missing or crashed | Check `dist-python/server/server.exe` exists; re-run `build:python` |
| Installer shows old version number | `version:sync` not run after `version:bump` | Run `npm run version:sync` |
| Large installer / build times | AI model files bundled (expected) | Normal — installer is 500MB–1GB by design |
