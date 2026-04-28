# Research: Identity Verification Page

**Phase**: 0 — Outline & Research  
**Feature**: `010-identity-verification`  
**Date**: 2026-04-23

---

## Decision 1: IPC Routing for Enrollment

**Decision**: Route `bridge:enroll-reference` through the existing AI-router JSON-RPC channel via `sendAiRpc('enrollReference', { frame, sessionId })`, NOT through the Flask HTTP bridge on port 5050.

**Rationale**: The `FaceRecognitionService` object in `router.py` already owns the `ModalClient` instance and the face-recognition endpoint configuration. Enrollment is logically an operation of the face-recognition service — it establishes the reference embedding that all subsequent `predict` calls compare against. Routing enrollment through the Flask bridge would require duplicating `ModalClient` and endpoint URL resolution in `server.py`, splitting ownership of the same Modal service across two Python files. The existing AI router already handles `startService`, `stopService`, `predict`, and `queryStatus` for face-recognition; `enrollReference` and `unenrollReference` are natural additions to the same handler set.

**Alternatives Considered**:
- **Flask HTTP endpoint** (`POST /enroll-reference` on port 5050): Rejected — duplicates ModalClient; splits face-recognition service logic; requires Flask restart to pick up endpoint config changes.
- **Direct HTTP from main.js to Modal**: Rejected — violates architecture boundary (main.js must not call AI endpoints directly per constitution Principle II, even with the accepted stdin/stdout deviation).

---

## Decision 2: Client-Side Quality Indicators

**Decision**: Implement Lighting and Focus quality indicators using canvas pixel analysis in the browser (no additional libraries). Face Detected indicator is informational only (best-effort via brightness heuristic); the authoritative face check is the server-side `POST /analysis/face-detection-file` called at capture time.

**Rationale**: The existing AI readiness page already uses `canvas.toDataURL()` with an offscreen canvas drawn from the `<video>` element. Extending this with brightness analysis (average pixel luminance) for Lighting and a simple Laplacian-variance estimate via canvas pixel data for Focus requires zero new dependencies. MediaPipe.js (browser-based face detection) was evaluated but rejected — it adds ~8 MB to the renderer bundle, requires a WASM cross-origin policy exception, and duplicates functionality already present server-side on Modal. The server-side check is authoritative and called once at capture time; client-side indicators are best-effort guidance only.

**Implementation**:
```js
// Brightness (Lighting indicator)
function analyzeBrightness(ctx, w, h) {
  const { data } = ctx.getImageData(0, 0, w, h);
  let sum = 0;
  for (let i = 0; i < data.length; i += 4) {
    sum += 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
  }
  return sum / (data.length / 4); // 0–255; threshold: >40 = adequate
}
```

**Alternatives Considered**:
- **MediaPipe.js FaceDetector**: Rejected — ~8 MB WASM bundle; COOP/COEP headers required; redundant with server-side check.
- **`window.FaceDetector` (Web API)**: Rejected — experimental; not available in Electron's embedded Chromium by default; no polyfill path.

---

## Decision 3: Enrollment State Storage

**Decision**: Store enrollment state as a module-scope object in `frontend/main.js`:
```js
let enrollmentState = null;
// Shape: { sessionId: string, enrolledAt: Date, succeeded: boolean }
```

**Rationale**: Follows the exact same pattern as `examSession` and `submitResult` in `main.js`. No persistence to disk (constitution Principle IV). The enrollment state is scoped to one exam session and must be cleared when the session ends, so module-scope (process lifetime but cleared on logical session end) is appropriate. `enrollmentState` is separate from `examSession` to avoid coupling two independently-resolvable IPC channels.

**Alternatives Considered**:
- **keytar storage**: Rejected — biometric enrollment state is not a credential; clearing it on session end would require a keytar delete call on every exit path.
- **renderer sessionStorage**: Rejected — not accessible to main.js; renderer state is lost on page navigation anyway.

---

## Decision 4: New Modal Endpoint URLs in config.json

**Decision**: Add three explicit URL fields under `services.face-recognition` in `config.json`:
```json
"face-recognition": {
  "endpoint_url": "...verify-file",
  "enroll_endpoint_url": "...enroll-file",
  "unenroll_endpoint_url": "...unenroll",
  "face_detect_endpoint_url": "...face-detection-file"
}
```

**Rationale**: Explicit URLs per endpoint are consistent with the existing `object-detection.endpoint_url` pattern and `face-recognition.endpoint_url`. Deriving URLs from a shared base would require changing how `FaceRecognitionService` and `ModalClient` discover endpoints and would make individual endpoint overrides harder. All four endpoints share the same Modal app base URL but are distinct routes — keeping them explicit avoids string manipulation in service code.

**Alternatives Considered**:
- **Derive from base URL**: Rejected — requires URL manipulation in `FaceRecognitionService`; makes per-endpoint overrides harder; adds complexity for marginal DRY benefit.

---

## Decision 5: Unenroll Trigger Points

**Decision**: Call `unenrollReference` JSON-RPC on three exit paths from the exam session:
1. `bridge:submit-exam` success handler in `main.js` (after `submitResult` is stored)
2. `bridge:clear-submit-result` handler (student clicks "Back to Home" from result page)
3. `bridge:clear-session` handler (student logs out from any page)

**Rationale**: These three are the only paths that transition out of an active exam session in the current codebase. The unenroll call is fire-and-forget (no error should block the UI flow); if it fails, Modal's own TTL will eventually clean up the embedding. The call is made with the `sessionId` from `enrollmentState`, which is then set to `null`.

**Alternatives Considered**:
- **`app.before-quit` event**: Rejected as the only trigger — app crashes would miss it; force-close on Windows may not fire `before-quit` reliably.
- **Only on submit success**: Rejected — misses the logout path, leaving embeddings cached on Modal indefinitely.

---

## Decision 6: Exam Page Navigation Guard

**Decision**: The AI Readiness page (`ai-readiness.js`) already calls `bridge:get-exam-session` and redirects to `exam-code` if no session exists. The exam page (`exam.js`) will similarly call a new `bridge:get-enrollment-status` IPC channel on load; if `enrollmentState?.succeeded !== true`, it redirects to `identity-verification/index.html`.

**Rationale**: Layered guards (exam-code → identity-verification → ai-readiness → exam) match the existing pattern. Each page asserts the preceding step completed before rendering. Adding the guard only to the exam page is sufficient because the identity-verification page itself is only reachable after a valid exam session exists (guarded by the `getExamSession` check it performs on load).

---

## Decision 7: Capture Resolution

**Decision**: Capture at 640×480 JPEG, quality 0.85, for enrollment. This is higher than the 320×240 / 0.6 quality used by the AI readiness eye-gaze calibration, because enrollment requires a face-quality scan (ArcFace embedding extraction is resolution-sensitive).

**Rationale**: The Modal ArcFace service benefits from higher resolution for the reference image. 640×480 is the standard webcam resolution; 0.85 JPEG quality avoids compression artefacts that degrade embedding quality. The enrollment call is one-off, so bandwidth cost is negligible. Live exam verify calls (`predict`) continue at 320×240 / 0.6 as set by the existing frame-capture code in `exam.js`.

**Alternatives Considered**:
- **Same as exam frame (320×240)**: Rejected — suboptimal for enrollment quality; Modal documentation implies reference images benefit from higher resolution.
- **Full native webcam resolution**: Rejected — may exceed 1 MB per frame; no benefit over 640×480 for ArcFace embedding.
