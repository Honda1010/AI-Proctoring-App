# Research: Foundation — App Shell & Python Bridge

**Branch**: `001-foundation` | **Date**: 2026-04-15
**Input**: Unknowns extracted from Technical Context in plan.md

---

## Research Task 1 — Electron + Python Child Process Pattern

**Question**: What is the reliable pattern for spawning a Python subprocess from Electron,
detecting readiness, and handling crashes?

### Decision
Use `child_process.spawn` from Electron's **main process** with readiness detection via
**HTTP polling** (`GET /ping`) with exponential backoff.

### Rationale
- `child_process.spawn` is non-blocking and exposes `stdout`/`stderr` streams for debugging
- Python's Flask dev server does not emit a structured "ready" event to stdout; polling is more
  reliable than stdout-scraping
- HTTP polling integrates naturally with the existing `GET /ping` contract
- The main process is the correct owner of subprocess lifecycle (not the renderer)

### Recommended Pattern
```js
// main.js — simplified startup sequence
const { app, BrowserWindow, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')

let pythonProcess = null

async function startBridge(port) {
  pythonProcess = spawn('python', [
    path.join(__dirname, '..', 'python_bridge', 'server.py'),
    '--port', String(port)
  ], { env: { ...process.env } })

  pythonProcess.on('close', (code) => {
    if (code !== 0) mainWindow.webContents.send('bridge-crashed', code)
  })

  // Poll GET /ping — max 20 attempts × 500ms = 10 seconds
  return await pollBridgeReady(`http://localhost:${port}/ping`, 20, 500)
}

async function pollBridgeReady(url, retries, intervalMs) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url)
      if (res.ok) return true
    } catch (_) { /* bridge not up yet */ }
    await new Promise(r => setTimeout(r, intervalMs))
  }
  return false
}
```

### Alternatives Considered
- **stdout event** (`pythonProcess.stdout.on('data')`): Rejected — Flask's startup message
  format varies by version and is not machine-parseable
- **TCP connect probe**: Viable fallback but adds complexity over HTTP fetch which is already
  available in the Electron renderer's Node context
- **Python subprocess module / py-node**: Rejected — adds a brittle dependency when
  `child_process.spawn` is a native Node API with no additional cost

---

## Research Task 2 — Font Bundling Strategy

**Question**: Should Manrope and Inter be bundled as local font files or loaded via @fontsource
npm packages?

### Decision
Use **`@fontsource/manrope`** and **`@fontsource/inter`** npm packages.

### Rationale
- @fontsource installs `.woff2` files locally under `node_modules` — no CDN requests at runtime
- Electron's renderer runs without internet access in exam environments (isolated machines);
  CDN-fetched fonts would silently fall back to system fonts, breaking design fidelity
- The packages include only the weights needed (`import '@fontsource/manrope/700.css'` for bold),
  reducing bundle size vs. importing all weights
- electron-builder correctly includes node_modules in the packaged app's asar archive

### Recommended Pattern
```css
/* frontend/assets/design-tokens.css */
@import '@fontsource/manrope/400.css';
@import '@fontsource/manrope/600.css';
@import '@fontsource/manrope/700.css';
@import '@fontsource/inter/400.css';
@import '@fontsource/inter/500.css';
@import '@fontsource/inter/600.css';
```

### Alternatives Considered
- **Manual TTF/WOFF2 in `frontend/assets/fonts/`**: Valid but requires manual download,
  update management, and larger git repository. @fontsource handles versioning via npm.
- **Google Fonts CDN**: Rejected — requires internet, violates exam isolation requirement,
  privacy concern (Google tracks font requests)
- **System fonts**: Rejected — Manrope and Inter are unlikely to be installed on student
  machines; design fidelity violation (Principle III)

---

## Research Task 3 — Flask CORS for Electron Renderer

**Question**: Does the Flask bridge need CORS configuration to accept requests from the
Electron renderer? What origin does the renderer present?

### Decision
Install **`flask-cors`** and apply `CORS(app)` with no origin restriction. Bind the bridge
to `127.0.0.1` (loopback only), not `0.0.0.0`, to prevent external network access.

### Rationale
- Electron's renderer presents either `file://` (when loading local HTML) or a custom protocol
  as its origin. Flask rejects cross-origin requests by default.
- `flask-cors` with no restriction is acceptable **only because** the bridge is bound to
  `127.0.0.1`. No external machine can reach it.
- Binding to `127.0.0.1` (not `0.0.0.0`) is the key security control, not CORS headers.

### Recommended Pattern
```python
# python_bridge/server.py
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Safe: bridge bound to 127.0.0.1 only

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=PORT, debug=False)
```

### Alternatives Considered
- **No CORS (expect Electron to bypass)**: Electron's `webSecurity: false` disables CORS in
  the renderer. Rejected — disabling web security is a constitution violation (Principle IV).
- **Specific `origins='file://'`**: flask-cors does not reliably match `file://` on all
  platforms. The `127.0.0.1` bind is the correct security boundary, not the CORS origin.

---

## Research Task 4 — Config File Location When Packaged

**Question**: Where should `config.json` be read from when the app is packaged with
electron-builder into an ASAR archive?

### Decision
Use **two-path resolution**: development path (`__dirname` relative) for unpackaged, and
`process.resourcesPath` for packaged builds. The `app.isPackaged` flag distinguishes them.

### Rationale
- `app.getAppPath()` returns the path inside the `.asar` archive when packaged — files inside
  `.asar` are read-only. `config.json` must survive re-launch edits.
- `process.resourcesPath` points to the `resources/` folder adjacent to the `.asar` archive,
  which is writable. electron-builder's `extraResources` config copies files there.
- For development, `path.join(__dirname, '..', 'config.json')` (project root) is correct.

### Recommended Pattern
```js
// main.js
const configPath = app.isPackaged
  ? path.join(process.resourcesPath, 'config.json')
  : path.join(__dirname, '..', 'config.json')
```

electron-builder config:
```json
{
  "extraResources": ["config.json"]
}
```

### Alternatives Considered
- **`app.getPath('userData')`**: The user data directory is correct for user-created files,
  but `config.json` is an admin-managed deployment file. userData varies per Windows user
  account, making multi-user machine deployment harder.
- **Environment variable `LMS_BASE_URL`**: Valid but harder for non-technical admins. A JSON
  file is self-documenting.

---

## Research Task 5 — Single-Instance Lock

**Question**: How to prevent two copies of the app from running with two competing Python
bridges on the same port?

### Decision
Use **`app.requestSingleInstanceLock()`** built into Electron. On second launch, quit and
focus the existing window.

### Rationale
- Native Electron API — no additional dependencies
- The `second-instance` event allows the existing window to receive focus and come to foreground
- Prevents port 5050 conflict from duplicate launch, which would otherwise cause a misleading
  "port in use" error screen

### Recommended Pattern
```js
// main.js
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })
  app.whenReady().then(createWindow)
}
```

### Alternatives Considered
- **Lock file**: Fragile — not cleaned up if app crashes. `requestSingleInstanceLock()` handles
  this via OS-level file locking.
- **Named pipe / mutex**: `requestSingleInstanceLock()` already uses this mechanism internally
  on Windows. No need to duplicate.

---

## Summary of All Decisions

| # | Decision | Chosen Approach |
|---|----------|-----------------|
| 1 | Electron ↔ Python startup | `child_process.spawn` + HTTP polling GET /ping, 20×500ms |
| 2 | Font bundling | `@fontsource/manrope` + `@fontsource/inter` npm packages |
| 3 | Flask CORS | `flask-cors` CORS(app) + bind to `127.0.0.1` only |
| 4 | Config file (packaged) | `app.isPackaged` → `process.resourcesPath/config.json` |
| 5 | Single-instance lock | `app.requestSingleInstanceLock()` native Electron API |

All NEEDS CLARIFICATION items from Technical Context are now resolved.
No further clarification required before Phase 1 design.
