# Contract: JSON-RPC enrollReference / unenrollReference Methods

**Type**: JSON-RPC 2.0 (stdin/stdout AI router)  
**Feature**: `010-identity-verification`  
**Date**: 2026-04-23

---

## enrollReference

**Handler**: `python_bridge/router.py` → `FaceRecognitionService.enroll()`  
**Caller**: `frontend/main.js` via `sendAiRpc('enrollReference', { frame, sessionId })`

### Request

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "enrollReference",
  "params": {
    "frame": "data:image/jpeg;base64,...",
    "sessionId": "1015"
  }
}
```

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `frame` | `string` | ✅ | Base64 data URL of the captured 640×480 JPEG reference image. |
| `sessionId` | `string` | ✅ | Exam attempt ID from `examSession.attemptId`. Used as Modal's `session_id` for embedding cache. |

### Response — Success

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": { "ok": true }
}
```

### Response — Failure

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "ok": false,
    "error": {
      "code": "NO_FACE_DETECTED",
      "message": "No face detected in the reference image. Please retake your photo."
    }
  }
}
```

**Error codes**:

| Code | Cause |
|------|-------|
| `NO_FACE_DETECTED` | `POST /analysis/face-detection-file` returned no face |
| `ENROLLMENT_FAILED` | `POST /analysis/enroll-file` returned non-200 or error body |
| `SERVICE_NOT_RUNNING` | `FaceRecognitionService` not yet started (startService not called) |
| `TIMEOUT` | Modal request timed out |
| `UNKNOWN_ERROR` | Unexpected exception in router or service |

### Internal Router Logic

```python
# router.py handler for enrollReference
async def handle_enroll_reference(params):
    frame = params.get('frame')
    session_id = params.get('sessionId')
    service = _services.get('face-recognition')
    if service is None or not service.is_running:
        return {"ok": False, "error": {"code": "SERVICE_NOT_RUNNING", ...}}
    return await service.enroll(frame)
```

### FaceRecognitionService.enroll() Internal Sequence

```
1. client.face_detect(session_id, frame)
     → POST /analysis/face-detection-file  { session_id (form), frame (file) }
     → if response["face_detected"] is False:
         return { "ok": False, "error": { "code": "NO_FACE_DETECTED", ... } }

2. client.enroll(session_id, frame)
     → POST /analysis/enroll-file  { session_id (form), references (file) }
     → if status != 200:
         return { "ok": False, "error": { "code": "ENROLLMENT_FAILED", ... } }

3. return { "ok": True }
```

---

## unenrollReference

**Handler**: `python_bridge/router.py` → `FaceRecognitionService.unenroll()`  
**Caller**: `frontend/main.js` (fire-and-forget, not awaited for UI flow)

### Request

```json
{
  "jsonrpc": "2.0",
  "id": 43,
  "method": "unenrollReference",
  "params": {
    "sessionId": "1015"
  }
}
```

### Response

```json
{
  "jsonrpc": "2.0",
  "id": 43,
  "result": { "ok": true }
}
```

Errors are swallowed by the router and logged to stderr; the main process does not block on failure.

### Internal Router Logic

```python
async def handle_unenroll_reference(params):
    session_id = params.get('sessionId')
    service = _services.get('face-recognition')
    if service is None:
        return {"ok": True}  # nothing to unenroll
    return await service.unenroll()
```

---

## Mock Responses (for offline testing)

Store in `specs/010-identity-verification/mocks/`:

**`enroll-success.json`**:
```json
{ "ok": true }
```

**`enroll-no-face.json`**:
```json
{
  "ok": false,
  "error": { "code": "NO_FACE_DETECTED", "message": "No face detected in the reference image." }
}
```

**`enroll-failed.json`**:
```json
{
  "ok": false,
  "error": { "code": "ENROLLMENT_FAILED", "message": "Modal enrollment endpoint returned 500." }
}
```
