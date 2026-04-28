# Contract: bridge:enroll-reference IPC Channel

**Type**: Electron IPC (invoke/handle)  
**Feature**: `010-identity-verification`  
**Date**: 2026-04-23

---

## Overview

The `bridge:enroll-reference` channel is invoked by the Identity Verification renderer page to trigger server-side face validation and Modal enrollment. The Electron main process receives the captured frame, forwards it to the AI router via JSON-RPC, and returns a typed result to the renderer.

---

## Request

**Invoked by**: `frontend/pages/identity-verification/identity-verification.js`  
**Handled by**: `frontend/main.js`

```js
// Renderer
const result = await window.bridge.enrollReference({ frame });
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `frame` | `string` | ✅ | Base64 data URL — `data:image/jpeg;base64,...`. 640×480 JPEG captured from `canvas.toDataURL('image/jpeg', 0.85)`. |

**Validation**: `frame` must start with `data:` and contain `;base64,`. Validated in `modal_client.py._decode_frame_to_image()` (existing); invalid frame returns `NO_FACE_DETECTED` error.

---

## Response

```ts
type EnrollReferenceResult =
  | { ok: true }
  | { ok: false; error: { code: EnrollErrorCode; message: string } };

type EnrollErrorCode =
  | 'NO_FACE_DETECTED'    // face-detection-file returned no face
  | 'ENROLLMENT_FAILED'   // enroll-file returned error or non-200
  | 'SERVICE_NOT_RUNNING' // FaceRecognitionService not started
  | 'TIMEOUT'             // Modal request timed out (>30s)
  | 'BRIDGE_ERROR';       // unexpected error in main/router
```

---

## Main Process Logic

```
ipcMain.handle('bridge:enroll-reference', async (_event, { frame }) => {
  1. Read sessionId from examSession.attemptId
  2. If !examSession → return { ok: false, error: { code: 'BRIDGE_ERROR', ... } }
  3. Call sendAiRpc('enrollReference', { frame, sessionId })
  4. If result.ok → set enrollmentState = { sessionId, enrolledAt: new Date(), succeeded: true }
  5. Return result as-is to renderer
})
```

**Side effect on success**: `enrollmentState` is set in module scope. This is the flag read by `bridge:get-enrollment-status`.

---

## bridge:get-enrollment-status

**Invoked by**: `frontend/pages/exam/exam.js` (on DOMContentLoaded, as a navigation guard)  
**Returns**:
```js
{ enrolled: boolean }  // true only if enrollmentState?.succeeded === true
```

---

## bridge:unenroll-reference *(internal, not renderer-exposed)*

Called internally by main.js at three exit points. Not exposed via preload.js (renderer never calls it directly).

```
Trigger points in main.js:
  - bridge:submit-exam success handler
  - bridge:clear-submit-result handler
  - bridge:clear-session handler
```

**Action**: `await sendAiRpc('unenrollReference', { sessionId })`, fire-and-forget. Then `enrollmentState = null`.

---

## Preload Whitelist Changes

Add to `ALLOWED_INVOKE_CHANNELS` in `frontend/preload.js`:

```js
'bridge:enroll-reference',
'bridge:get-enrollment-status',
```

Add to `contextBridge.exposeInMainWorld('bridge', { ... })`:

```js
enrollReference(frame) {
  return ipcRenderer.invoke('bridge:enroll-reference', { frame });
},
getEnrollmentStatus() {
  return ipcRenderer.invoke('bridge:get-enrollment-status');
},
```
