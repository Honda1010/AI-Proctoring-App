# API Contract: Bridge Health Check

**Contract Type**: Internal HTTP (Electron → Python Bridge)
**Direction**: Electron main process → Python Flask bridge (localhost only)
**Version**: 1.0.0
**Defined in**: `specs/001-foundation/contracts/ping.md`

---

## Endpoint

```
GET http://localhost:{pythonPort}/ping
```

| Parameter | Value |
|-----------|-------|
| Method | `GET` |
| Host | `127.0.0.1` (loopback only) |
| Port | `pythonPort` from `config.json` (default: `5050`) |
| Auth | None required |
| Content-Type | N/A (no request body) |

---

## Request

No body. No query parameters. No headers required.

```
GET /ping HTTP/1.1
Host: 127.0.0.1:5050
```

---

## Responses

### ✅ 200 OK — Bridge is operational

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-04-15T10:30:00.000Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"ok"` on success |
| `version` | `string` | Bridge version (SemVer) |
| `timestamp` | `string` (ISO 8601 UTC) | Server time at response |

### ❌ Any non-200 or connection refused

Electron treats **any** non-200 response or connection error as "bridge not ready yet" during
the startup polling phase. After 20 failed retries (10 seconds total), Electron transitions
`BridgeStatus` to `failed` and renders the error screen.

---

## Electron Calling Behaviour

```js
// Polling contract — called by Electron main process during startup
// 20 attempts × 500ms interval = 10 second timeout maximum
const MAX_RETRIES = 20
const POLL_INTERVAL_MS = 500

for (let i = 0; i < MAX_RETRIES; i++) {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/ping`)
    if (response.status === 200) {
      const body = await response.json()
      if (body.status === 'ok') return { state: 'ready', port }
    }
  } catch (_) { /* connection refused — bridge still starting */ }
  await delay(POLL_INTERVAL_MS)
}
return { state: 'failed', message: 'Bridge did not respond within 10 seconds', port }
```

---

## Python Implementation Contract

The Python bridge MUST implement this endpoint exactly:

```python
from flask import jsonify
from datetime import datetime, timezone

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200
```

---

## Security Note

This endpoint requires **no authentication**. It is intentionally public on `127.0.0.1`.
Because the bridge is bound exclusively to the loopback interface (`127.0.0.1`, not `0.0.0.0`),
this endpoint is not reachable from any other machine on the network.
