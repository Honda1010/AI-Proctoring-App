# Data Model: Identity Verification Page

**Phase**: 1 — Design  
**Feature**: `010-identity-verification`  
**Date**: 2026-04-23

---

## Entities

### 1. EnrollmentState *(new — Electron main process, module scope)*

Tracks whether the student has successfully enrolled their face embedding for the current exam session.

| Field | Type | Description |
|-------|------|-------------|
| `sessionId` | `string` | The exam attempt ID; matches `examSession.attemptId`. Used as the key for Modal's server-side embedding cache. |
| `enrolledAt` | `Date` | Timestamp of successful enrollment. |
| `succeeded` | `boolean` | `true` only after `enrollReference` JSON-RPC returns `{ ok: true }`. |

**Lifecycle**:
- Created: `bridge:enroll-reference` IPC handler, on `enrollReference` JSON-RPC success
- Read: `bridge:get-enrollment-status` IPC handler (exam page guard)
- Cleared (set to `null`): on `bridge:submit-exam` success, `bridge:clear-submit-result`, `bridge:clear-session`

**Storage**: Module-scope variable in `frontend/main.js`. Never written to disk or keytar.

```js
// frontend/main.js (module scope)
let enrollmentState = null;
// EnrollmentState | null
```

---

### 2. ReferenceImage *(transient — renderer memory only)*

The raw captured JPEG, held in the identity-verification page renderer until the IPC call completes.

| Field | Type | Description |
|-------|------|-------------|
| `dataUrl` | `string` | `data:image/jpeg;base64,...` string from `canvas.toDataURL('image/jpeg', 0.85)`. 640×480 resolution. |
| `capturedAt` | `Date` | Timestamp of user-initiated capture. |

**Lifecycle**:
- Created: when the student clicks "Capture Photo" and the frame passes the face-detection check
- Transmitted: sent as the `frame` field in `bridge:enroll-reference` IPC invoke payload
- Discarded: immediately after IPC resolves (success or failure); renderer has no persistent reference

**Storage**: Renderer JS variable. Never passed to `main.js` beyond the IPC call. Never written to disk.

---

### 3. FaceRecognitionService *(modified — `python_bridge/face_recognition.py`)*

Existing entity; extended with enrollment/unenrollment methods.

**New methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `enroll(frame)` | `async enroll(frame: str) -> dict` | Calls `ModalClient.face_detect(session_id, frame)` then `ModalClient.enroll(session_id, frame)`. Returns `{ ok: True }` or `{ ok: False, error: { code, message } }`. |
| `unenroll()` | `async unenroll() -> dict` | Calls `ModalClient.unenroll(session_id)`. Fire-and-forget; errors are logged but do not propagate. |

**Removed behaviour**:
- `start()` no longer calls `await self.client.predict(self.service_name, self.session_id, "WARMUP")`.

---

### 4. ModalClient *(modified — `python_bridge/modal_client.py`)*

Existing entity; extended with three new endpoint methods.

**New methods**:

| Method | Endpoint | Fields | Returns |
|--------|----------|--------|---------|
| `face_detect(session_id, frame)` | `POST {face_detect_endpoint_url}` | `session_id` (form), `frame` (file) | `{ "face_detected": bool, ... }` or error dict |
| `enroll(session_id, frame)` | `POST {enroll_endpoint_url}` | `session_id` (form), `references` (file, field name per API) | `{ "status": "enrolled" }` or error dict |
| `unenroll(session_id)` | `POST {unenroll_endpoint_url}` | `session_id` (form) | `{ "status": "unenrolled" }` or error dict |

**Configuration** (read from `config.json` → `services.face-recognition`):

| Config key | Example value |
|------------|---------------|
| `enroll_endpoint_url` | `https://moustafaalaa30--eduai-proctoring-proctoring-serve.modal.run/analysis/enroll-file` |
| `unenroll_endpoint_url` | `https://moustafaalaa30--eduai-proctoring-proctoring-serve.modal.run/analysis/unenroll` |
| `face_detect_endpoint_url` | `https://moustafaalaa30--eduai-proctoring-proctoring-serve.modal.run/analysis/face-detection-file` |

---

## State Machine: Identity Verification Page

```
        ┌──────────┐
        │   IDLE   │  (page loads, camera permission not yet requested)
        └────┬─────┘
             │ camera granted + stream active
             ▼
        ┌──────────┐
        │   LIVE   │  (webcam streaming; quality indicators updating)
        └────┬─────┘
             │ student clicks "Capture Photo"
             ▼
        ┌──────────────┐
        │  FACE-CHECK  │  (POST /analysis/face-detection-file in flight)
        └──┬───────────┘
           │ face detected        │ no face detected
           ▼                      ▼
      ┌──────────┐           ┌──────────┐
      │ CAPTURED │           │  ERROR   │ → show inline error → return to LIVE
      └────┬─────┘           └──────────┘
           │ student clicks "Confirm & Continue"
           ▼
      ┌───────────┐
      │ VERIFYING │  (POST /analysis/enroll-file in flight; spinner visible)
      └──┬────────┘
         │ enroll ok: true          │ enroll ok: false
         ▼                          ▼
    ┌──────────┐               ┌──────────┐
    │ ENROLLED │               │  ERROR   │ → show error pill → return to LIVE
    └────┬─────┘               └──────────┘
         │
         ▼
    navigate → ai-readiness/index.html
```

**States**:

| State | Capture Button | Confirm Button | Retake Button | Spinner |
|-------|---------------|----------------|---------------|---------|
| IDLE | disabled (camera loading) | hidden | hidden | hidden |
| LIVE | enabled | hidden | hidden | hidden |
| FACE-CHECK | disabled | hidden | hidden | shown (small) |
| CAPTURED | hidden | enabled | enabled | hidden |
| VERIFYING | hidden | disabled | disabled | shown |
| ERROR | enabled (retake path) | hidden | shown if post-capture | hidden |

---

## Navigation Flow (updated)

```
Login → Exam Code → Identity Verification → AI Readiness → Exam → Result
                           ↑
                    (redirect gate if
                     no examSession)
                                                              ↑
                                                   (redirect gate if
                                                    enrollmentState?.succeeded !== true)
```

**Guard in `exam.js`**: On `DOMContentLoaded`, call `bridge:get-enrollment-status`. If `{ enrolled: false }`, redirect to `../identity-verification/index.html`.

---

## Validation Rules

| Field | Rule |
|-------|-------|
| `frame` sent to `bridge:enroll-reference` | Must be a `data:image/jpeg;base64,...` string; validated in `modal_client.py._decode_frame_to_image()` (existing validation) |
| `session_id` | Derived from `examSession.attemptId`; never null when enrollment is called (guarded by exam-session check on page load) |
| Enrollment state check | `enrollmentState?.succeeded === true` is the only gate; `null` state = not enrolled |
