# Data Model: Exam Lockdown (013)

**Date**: 2026-05-07  
**Derived from**: spec.md + research.md

---

## Entities

### 1. `EnvironmentCheckResult`

The structured response returned by `POST /check-environment`.

| Field | Type | Description |
|-------|------|-------------|
| `vm_detected` | `boolean` | `true` if a virtual machine environment was detected |
| `vm_reason` | `string \| null` | Human-readable description of the VM indicator (e.g., `"VirtualBox detected via registry SCSI key"`). `null` when `vm_detected` is `false`. |
| `rdp_detected` | `boolean` | `true` if an active RDP connection or remote desktop process was detected |
| `rdp_reason` | `string \| null` | Human-readable description (e.g., `"TeamViewer.exe running"`). `null` when `rdp_detected` is `false`. |
| `screen_capture_detected` | `boolean` | `true` if a screen-capture application was found running |
| `screen_capture_reason` | `string \| null` | Human-readable description (e.g., `"OBS64.exe running"`). `null` when `screen_capture_detected` is `false`. |

**Validation rules:**
- All six fields are always present. No optional fields.
- `*_reason` is non-null only when the corresponding `*_detected` is `true`.
- If the check fails (exception in endpoint), the endpoint returns a 500 with `{ "code": "CHECK_ERROR", "message": "..." }`.

---

### 2. `LockdownAlertRecord`

A single JSON line appended to `sessions/{attemptId}.jsonl` when a lockdown violation is detected.

| Field | Type | Description |
|-------|------|-------------|
| `type` | `string` | Alert type: `"VIRTUAL_ENVIRONMENT"`, `"SCREEN_CAPTURE_DETECTED"`, or `"FULLSCREEN_ESCAPE_ATTEMPT"` |
| `timestamp` | `string` | UTC ISO 8601 timestamp (e.g., `"2026-05-07T14:32:11.123456+00:00"`) |
| `sessionId` | `string` | `examSession.attemptId` cast to string |
| `reason` | `string \| null` | Human-readable reason string from `EnvironmentCheckResult`, or `"fullscreen exit detected"` for `FULLSCREEN_ESCAPE_ATTEMPT` |

**Written by**: `main.js` (Electron main process), using the same best-effort `try/catch` pattern as `_append_to_session_log` in `python_bridge/services/clip_upload_service.py`. Never throws.

**File path**: `sessions/{examSession.attemptId}.jsonl` relative to the project root, resolved via `path.join(__dirname, '..', 'sessions', ...)`.

---

### 3. `LockdownViolationEvent` (IPC push payload)

The payload sent from `main.js` to the renderer via `mainWindow.webContents.send()` when a violation is detected.

| Field | Type | Description |
|-------|------|-------------|
| `reason` | `string` | Human-readable violation reason from `EnvironmentCheckResult` |

**Channels:**
- `lockdown:vm-detected` — for VM or RDP detection
- `lockdown:screen-capture-detected` — for screen-capture detection

---

### 4. `BlockedShortcutSet` (compile-time constant)

The complete set of shortcuts and their blocking layer.

| Shortcut | `globalShortcut` Layer | `before-input-event` Layer | Notes |
|----------|----------------------|--------------------------|-------|
| PrintScreen | ✅ | ✅ | Both layers for defence-in-depth |
| Alt+PrintScreen | ✅ | ✅ | |
| F11 | ✅ | ✅ | |
| Escape | ✅ | ✅ | |
| Ctrl+Shift+I | ✅ | ✅ | |
| Ctrl+W | ✅ | ✅ | |
| Ctrl+A | ✅ | ✅ | |
| Ctrl+C | ✅ | ✅ | |
| Ctrl+V | ✅ | ✅ | |
| Ctrl+X | ✅ | ✅ | |
| Alt+F4 | ❌ (OS) | ❌ (OS) | Handled via `mainWindow.on('close')` |
| Alt+Tab | ❌ (OS) | ❌ (OS) | Unblockable; accepted gap |
| Win+D | ❌ (OS) | ❌ (OS) | Unblockable; accepted gap |
| Win+L | ❌ (OS) | ❌ (OS) | Unblockable; accepted gap |
| Win+PrintScreen | ❌ (OS) | ❌ (OS) | Mitigated by `setContentProtection` |
| Win+Shift+S | ❌ (OS) | ❌ (OS) | Mitigated by `setContentProtection` |
| Ctrl+Shift+Esc | ❌ (OS) | ❌ (OS) | Unblockable; accepted gap |
| F12 | — | ✅ via `before-input-event` guard in existing handler | Existing handler modified |

---

### 5. Module-Scope State (`main.js` additions)

| Variable | Type | Initial Value | Description |
|----------|------|--------------|-------------|
| `envCheckInterval` | `NodeJS.Timeout \| null` | `null` | Handle for the 60-second periodic environment check. Set on exam start, cleared on all three exit paths. |
| `lockdownActive` | `boolean` | `false` | `true` while `globalShortcut` registrations are active. Guards against double-registration if `bridge:start-exam` is somehow called twice. |

---

### 6. Lockdown Blueprint (`python_bridge/lockdown.py`)

New Flask blueprint registered in `server.py`.

**Route**: `POST /check-environment`

**Request body**: `{}` (empty JSON object — no parameters needed; detection is stateless)

**Response** (200 OK): `EnvironmentCheckResult` JSON  
**Response** (500): `{ "code": "CHECK_ERROR", "message": "Environment check failed." }`

**Detection sub-checks** (all best-effort, 3-second timeout per subprocess):

| Sub-check | Method | Privilege |
|-----------|--------|-----------|
| Computer model (VM name in model string) | PowerShell `Get-CimInstance Win32_ComputerSystem` | None |
| Disk drive model (VM name in drive model) | PowerShell `Get-CimInstance Win32_DiskDrive` | None |
| Registry IDE/SCSI keys | `winreg` (built-in) | None |
| MAC address OUI | `psutil.net_if_addrs()` | None |
| RDP port 3389 connections | `psutil.net_connections('tcp')` | None (port listing only) |
| Remote desktop processes | `psutil.process_iter(['name'])` | None |
| CPU brand string | `platform.processor()` | None |
| Screen-capture processes | `psutil.process_iter(['name'])` | None |

**VM vendor keywords** (case-insensitive match): `virtualbox`, `vmware`, `qemu`, `hyper-v`, `hyperv`, `xenhvm`, `parallels`, `kvm`

**Remote desktop processes**: `TeamViewer.exe`, `AnyDesk.exe`, `vncviewer.exe`, `vncserver.exe`, `tvnserver.exe`, `LogMeIn.exe`, `Parsec.exe`, `rustdesk.exe`

**Screen-capture processes**: `SnippingTool.exe`, `ScreenClippingHost.exe`, `ShareX.exe`, `Greenshot.exe`, `OBS64.exe`, `obs32.exe`, `Camtasia.exe`

**VM OUI prefixes** (MAC address first 3 octets, lowercase colon-separated):
`08:00:27` (VirtualBox), `00:0c:29` (VMware ESX), `00:50:56` (VMware Workstation), `00:1c:42` (Parallels), `52:54:00` (QEMU/KVM), `00:03:ff` (Hyper-V)
