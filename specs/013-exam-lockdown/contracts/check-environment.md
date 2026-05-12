# Contract: POST /check-environment

**Blueprint**: `lockdown_bp` (`python_bridge/lockdown.py`)  
**Registered in**: `python_bridge/server.py`  
**Called by**: `main.js` via `net.fetch()` — internally, not via a renderer-callable IPC channel

---

## Request

```
POST http://127.0.0.1:{bridgePort}/check-environment
Content-Type: application/json

{}
```

- Body: empty JSON object. No parameters required; all checks are stateless.
- No `Authorization` header (bridge-internal call, no LMS involvement).

---

## Response — 200 OK

```json
{
  "vm_detected": false,
  "vm_reason": null,
  "rdp_detected": false,
  "rdp_reason": null,
  "screen_capture_detected": false,
  "screen_capture_reason": null
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `vm_detected` | `boolean` | `true` if a virtual machine environment was detected |
| `vm_reason` | `string \| null` | Human-readable reason. Non-null only when `vm_detected` is `true`. |
| `rdp_detected` | `boolean` | `true` if a remote desktop connection or process was detected |
| `rdp_reason` | `string \| null` | Human-readable reason. Non-null only when `rdp_detected` is `true`. |
| `screen_capture_detected` | `boolean` | `true` if a screen-capture application was found running |
| `screen_capture_reason` | `string \| null` | Human-readable reason. Non-null only when `screen_capture_detected` is `true`. |

### Example — VM detected

```json
{
  "vm_detected": true,
  "vm_reason": "VirtualBox detected via registry SCSI key",
  "rdp_detected": false,
  "rdp_reason": null,
  "screen_capture_detected": false,
  "screen_capture_reason": null
}
```

### Example — Screen capture detected

```json
{
  "vm_detected": false,
  "vm_reason": null,
  "rdp_detected": false,
  "rdp_reason": null,
  "screen_capture_detected": true,
  "screen_capture_reason": "OBS64.exe running"
}
```

---

## Response — 500 Internal Server Error

```json
{
  "code": "CHECK_ERROR",
  "message": "Environment check failed."
}
```

Returned only if an unhandled exception escapes the route handler. Individual sub-check failures are caught internally and treated as non-detection (clean result). A 500 should be extremely rare.

---

## Caller Behaviour (`main.js`)

```javascript
async function runEnvCheck() {
  try {
    const response = await net.fetch(`http://127.0.0.1:${bridgePort}/check-environment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!response.ok) return;  // treat non-200 as clean — silent failure
    const result = await response.json();

    if (result.vm_detected || result.rdp_detected) {
      appendLockdownAlert('VIRTUAL_ENVIRONMENT', result.vm_reason || result.rdp_reason);
      mainWindow?.webContents.send('lockdown:vm-detected', {
        reason: result.vm_reason || result.rdp_reason,
      });
    }
    if (result.screen_capture_detected) {
      appendLockdownAlert('SCREEN_CAPTURE_DETECTED', result.screen_capture_reason);
      mainWindow?.webContents.send('lockdown:screen-capture-detected', {
        reason: result.screen_capture_reason,
      });
    }
  } catch (_err) {
    // Bridge unreachable — silent failure per FR-017
  }
}
```

---

## IPC Push Channels (main → renderer)

These channels are added to `preload.js` `ALLOWED_RECEIVE_CHANNELS` and exposed via `contextBridge`.

### `lockdown:vm-detected`

**Direction**: `main.js` → renderer  
**Trigger**: `mainWindow.webContents.send('lockdown:vm-detected', payload)`  
**Payload**:

```json
{ "reason": "VMware detected via MAC address OUI 00:0C:29" }
```

**Renderer action**: Show a blocking modal with the reason string; suspend exam interaction until student clicks "Acknowledge".

---

### `lockdown:screen-capture-detected`

**Direction**: `main.js` → renderer  
**Trigger**: `mainWindow.webContents.send('lockdown:screen-capture-detected', payload)`  
**Payload**:

```json
{ "reason": "ShareX.exe running" }
```

**Renderer action**: Show a blocking modal with the reason string; suspend exam interaction until student clicks "Acknowledge".

---

## JSONL Alert Record

Written to `sessions/{examSession.attemptId}.jsonl` by `main.js` for each detected violation.

```json
{
  "type": "VIRTUAL_ENVIRONMENT",
  "timestamp": "2026-05-07T14:32:11.123456+00:00",
  "sessionId": "1067",
  "reason": "VirtualBox detected via registry SCSI key"
}
```

```json
{
  "type": "SCREEN_CAPTURE_DETECTED",
  "timestamp": "2026-05-07T14:32:11.123456+00:00",
  "sessionId": "1067",
  "reason": "OBS64.exe running"
}
```

```json
{
  "type": "FULLSCREEN_ESCAPE_ATTEMPT",
  "timestamp": "2026-05-07T14:32:11.123456+00:00",
  "sessionId": "1067",
  "reason": "fullscreen exit detected"
}
```
