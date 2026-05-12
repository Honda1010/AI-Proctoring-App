# Research: Exam Lockdown (013)

**Date**: 2026-05-07  
**Resolved from**: spec.md Technical Context unknowns + integration patterns

---

## 1. Electron globalShortcut — OS-Reserved Key Limitations

### Decision
`globalShortcut.register()` silently fails for OS-reserved shortcuts on Windows. These shortcuts can **never** be intercepted at the Electron app layer:

| Shortcut | Status | Reason |
|----------|--------|--------|
| Alt+Tab | ❌ Unblockable | Windows DWM window-switcher |
| Win+D | ❌ Unblockable | Windows Shell (explorer.exe) |
| Win+L | ❌ Unblockable | Windows Shell |
| Win+PrintScreen | ❌ Unblockable | Windows Shell screenshot handler |
| Win+Shift+S | ❌ Unblockable | Snipping Tool Shell overlay |
| Ctrl+Shift+Esc | ❌ Unblockable | OS Task Manager |
| Alt+F4 | ⚠️ Partially | Not blockable via globalShortcut; use `mainWindow.on('close', ...)` to cancel close event instead |
| PrintScreen | ✅ Registerable | globalShortcut or before-input-event |
| Alt+PrintScreen | ✅ Registerable | globalShortcut or before-input-event |
| F11, Escape, Ctrl+Shift+I | ✅ Registerable | globalShortcut and before-input-event |
| Ctrl+W/A/C/V/X | ✅ Blockable | before-input-event (DOM-layer) |

### Rationale
Electron's `globalShortcut.register()` documentation explicitly states it silently fails when the OS already owns the shortcut. Win+*, Win+Shift+*, and system-level Ctrl+Alt+Del shortcuts are processed by the Windows Shell (`explorer.exe`) or the DWM compositor before any application window receives the event — `hookWindowMessage()` on the app's own HWND cannot intercept them either.

### Alternatives Considered
- **Low-level keyboard hook (`SetWindowsHookEx`)**: Requires a native Node.js addon (`.node`). Would block Win+D and Win+L system-wide but introduces a privileged global hook that Windows may reject on secure desktop and triggers AV/EDR alerts. Rejected: too invasive, outside Electron's capability set without native addons.
- **`hookWindowMessage()`**: Only intercepts messages routed to the app's HWND. Win+D/L are handled by the shell, not routed to individual windows.

### Implication for Implementation
- The spec's shortcut list must be split into two tiers at implementation time: (a) OS-owned shortcuts accepted as unblockable, and (b) app-interceptable shortcuts blocked via globalShortcut + before-input-event.
- `setContentProtection(true)` compensates for the unblockable Win+PrintScreen and Win+Shift+S screenshot paths.
- The design goal is achieved: screenshot key paths produce blank captures even when the shortcut cannot be consumed.

---

## 2. Electron `setContentProtection(true)` on Windows

### Decision
Use `mainWindow.setContentProtection(true)` as the primary screenshot defence. This calls `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` on Windows 10 v2004+ and causes the OS to render the window as a black/blank surface in all capture pipelines (GDI, DXGI, Media Foundation).

### Behaviour
| Capture Method | With Protection On |
|---|---|
| PrintScreen (clipboard) | Black rectangle at window position |
| Win+PrintScreen (save to disk) | Black rectangle |
| Win+Shift+S (Snipping Tool) | Black rectangle |
| ShareX, Greenshot (DXGI capture) | Black rectangle |
| OBS Desktop Capture (DXGI) | Black rectangle |
| OBS Window Capture (GDI) | Black rectangle |

### Caveats
- On Windows 10 older than v2004 (pre-May 2020): window renders as black but with `WDA_MONITOR` semantics (still protected — just a different affinity flag internally).
- macOS: uses `NSWindowSharingNone`. ScreenCaptureKit-based apps on newer macOS can bypass this (Electron GitHub issue #48258). Out of scope — spec is Windows-only.
- DevTools: DevTools opens in a separate `BrowserWindow`; content protection applies only to the window it is called on. Since DevTools is blocked by F12 blocking, this is not a concern.

### Rationale
Single API call, built into Electron, zero external dependencies. Covers the unblockable Win+Shift+S and Win+PrintScreen paths that cannot be consumed via `globalShortcut`.

---

## 3. WMIC Deprecation on Windows 11 (22H2+)

### Decision
Use **PowerShell `Get-CimInstance`** as the primary WMI query method. Keep WMIC as a silent fallback for machines that may have it available.

```
Primary: powershell -Command "Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object Model | ConvertTo-Json"
Fallback: wmic computersystem get model
```

### Rationale
WMIC is deprecated as of Windows 11 22H2 (Oct 2022). Microsoft has not removed it yet in 2026, but it is unsupported and will eventually be removed. `Get-CimInstance` is the documented modern replacement and is available on all target Windows 10/11 machines.

### Alternatives Considered
- **Python `wmi` module**: Cleanest interface but requires `pywin32` as a dependency (large binary wheel). Not currently in `python_bridge/requirements.txt` — adding it solely for VM detection is disproportionate.
- **`subprocess(['wmic', ...])`**: Still functional on Windows 11 in 2026 but deprecated. Use as fallback only.

---

## 4. Python `winreg` for Registry-Based VM Detection

### Decision
Use the built-in `winreg` module (standard library — no additional dependency) to enumerate `HKLM\SYSTEM\CurrentControlSet\Enum\IDE` and `HKLM\SYSTEM\CurrentControlSet\Enum\SCSI`.

### Key Facts
- **No admin rights required**: `HKLM\SYSTEM\CurrentControlSet` is world-readable.
- **`PermissionError` is rare but possible** on some locked-down machines; handle silently.
- **Key may be absent** (e.g., IDE key on SCSI-only machine): handle `FileNotFoundError` silently.
- Sub-key names contain hardware identifiers (e.g., `"VEN_80EE&DEV_CAFE"` for VirtualBox) — check both key names and string values against VM vendor keywords.

### Alternatives Considered
- WMI via `Get-CimInstance Win32_DiskDrive`: Equivalent data, but adds a PowerShell subprocess call. Using `winreg` directly avoids process spawning overhead and the 3-second timeout concern.

---

## 5. `psutil` for Process Enumeration and Network Connection Detection

### Decision
Use `psutil` (already available in `python_bridge/requirements.txt` via existing AI services) for both process enumeration and RDP connection detection.

```python
# Process enumeration (no admin required)
psutil.process_iter(['name'])  # returns cached name with each proc info dict

# RDP detection (no admin required for basic connections; may miss kernel-level)
psutil.net_connections(kind='tcp')  # filter for laddr.port==3389 or raddr.port==3389
```

### Key Facts
- **`psutil.process_iter(['name'])`**: Works without admin rights. Inaccessible processes raise `NoSuchProcess` / `AccessDenied` — silently skip, continue iteration.
- **`psutil.net_connections()`**: Preferred over `netstat` subprocess — no process spawning, no timeout risk, returns structured objects. Requires no admin for listing TCP/UDP connections in ESTABLISHED or LISTEN state.
- **Admin for `net_connections()`**: Getting the PID associated with a connection requires elevated privileges on Windows; port numbers and states do not.

### Alternatives Considered
- `subprocess(['netstat', '-n'])`: Works but requires spawning an extra process with a 3-second timeout, parsing text output, and handling encoding issues. `psutil` is already a dependency and gives structured data.

---

## 6. Subprocess Timeout Safety on Windows

### Decision
When using `subprocess.run(..., timeout=3, capture_output=True)`, the `TimeoutExpired` exception does **not** automatically kill the subprocess on Windows. The implementation must explicitly call `proc.kill()` in the exception handler.

```python
import subprocess

proc = subprocess.Popen(cmd, capture_output=True, text=True)
try:
    stdout, stderr = proc.communicate(timeout=3)
except subprocess.TimeoutExpired:
    proc.kill()
    stdout, stderr = proc.communicate()  # drain after kill
    return None  # treat as non-detection
```

Using `subprocess.run(..., timeout=3)` is equivalent — on `TimeoutExpired`, call `.kill()` on the `process` attribute if using the lower-level API, or use `Popen` + `communicate(timeout=...)` for explicit control.

### Rationale
`subprocess.run` with `timeout` raises `TimeoutExpired` and internally calls `proc.kill()` on Unix but **not** on Windows (documented Python behaviour). Explicit kill prevents zombie `wmic` or `powershell` processes accumulating during long exam sessions.

---

## 7. MAC Address OUI Detection

### Decision
Use `psutil.net_if_addrs()` to retrieve all interface MAC addresses and compare against known VM vendor OUI prefixes.

Known VM OUI prefixes:
| Prefix | Vendor |
|--------|--------|
| `08:00:27` | VirtualBox |
| `00:0c:29` | VMware (ESX) |
| `00:50:56` | VMware (Workstation/ESX) |
| `00:1c:42` | Parallels |
| `52:54:00` | QEMU/KVM |
| `00:03:ff` | Hyper-V |

`uuid.getnode()` returns only one MAC address (the "primary" adapter) and may return the loopback if no real NIC exists. `psutil.net_if_addrs()` returns all adapters and is more thorough.

---

## 8. New Renderer-Side IPC Channels

New channels must be added to `preload.js` to allow the renderer to receive lockdown push events.

| Channel | Direction | Payload | Purpose |
|---------|-----------|---------|---------|
| `lockdown:vm-detected` | main → renderer | `{ reason: string }` | Show VM/RDP blocking modal |
| `lockdown:screen-capture-detected` | main → renderer | `{ reason: string }` | Show screen-capture blocking modal |

These follow the same `ipcRenderer.on` / `mainWindow.webContents.send` pattern as `bridge:ai-event` and `clip:upload-error`.

No new `invoke` channels are needed from the renderer — all lockdown logic is driven by `main.js`.

---

## 9. New IPC Invoke Channel

| Channel | Direction | Args | Returns |
|---------|-----------|------|---------|
| `bridge:check-environment` | renderer or main → main | none (called internally) | `{ ok: bool, result: EnvironmentCheckResult }` |

Since periodic checks are driven from `main.js` itself (not from the renderer), this channel is called internally by `main.js` using `net.fetch()` directly to `http://127.0.0.1:{bridgePort}/check-environment`. No renderer-callable channel is needed.

---

## 10. Module-Scope State Additions (main.js)

Three new module-scope variables are needed in `frontend/main.js`:

```javascript
/** @type {NodeJS.Timeout | null} */
let envCheckInterval = null;  // Periodic environment check timer

/** @type {boolean} */
let lockdownActive = false;   // True while globalShortcuts are registered
```

These follow the existing pattern of `examSession`, `submitResult`, `enrollmentState`, etc.

---

## Summary of Decisions

| Unknown | Decision |
|---------|---------|
| OS-reserved shortcuts (Alt+Tab, Win+D, Win+L, Win+Shift+S, etc.) | Accept as unblockable at Electron level; compensate with setContentProtection |
| Alt+F4 | Block via `mainWindow.on('close')` event cancellation |
| Screenshot interception | `setContentProtection(true)` — calls WDA_EXCLUDEFROMCAPTURE on Windows |
| WMIC deprecation | PowerShell Get-CimInstance primary, WMIC fallback |
| Registry VM detection | `winreg` built-in module (no admin required) |
| Process enumeration | `psutil.process_iter(['name'])` (already in requirements) |
| RDP detection | `psutil.net_connections()` (no subprocess spawn needed) |
| Subprocess timeout kill | Explicit `proc.kill()` required on Windows after TimeoutExpired |
| MAC address OUI | `psutil.net_if_addrs()` (all adapters, more thorough than uuid.getnode()) |
| New receive IPC channels | `lockdown:vm-detected`, `lockdown:screen-capture-detected` |
| New Flask blueprint | `lockdown_bp` in `python_bridge/lockdown.py`, POST /check-environment |
