# Research: Violation Clip Recording & Upload

**Phase**: 0 — Pre-design research  
**Feature**: 011-violation-clip-upload  
**Date**: 2026-05-05  

---

## Decision 1: Pre-violation Buffer Implementation Strategy

**Decision**: In-memory JavaScript array acting as a circular ring buffer in the Electron renderer process; each entry is `{ blob: Blob, timestamp: string }` where timestamp is ISO 8601 UTC. The array is capped at `pre_buffer_seconds` entries (10); on overflow the oldest entry is shifted off the front. The MediaRecorder API emits one `Blob` chunk every `chunk_duration_ms` (1 000 ms) via the `ondataavailable` event.

**Rationale**:
- The MediaRecorder Web API `timeslice` option is a native browser mechanism for emitting time-sliced chunks; it requires no additional packages in the renderer.
- An array shifted on overflow is O(n) for shift but n = 10, making the cost negligible.
- A `Deque` or `CircularBuffer` class would be over-engineered for n = 10.
- Timestamps are captured inside the `ondataavailable` handler using `new Date().toISOString()` at the moment each chunk arrives, satisfying FR-016 (real chunk timestamps).

**Alternatives considered**:
- `canvas.captureStream()` + `MediaRecorder` — considered but unnecessary; MediaRecorder directly accepts the `getUserMedia` stream.
- IndexedDB pre-buffer — rejected: disk persistence violates FR-007/assumptions; memory is sufficient.
- SharedArrayBuffer ring buffer — rejected: overkill, requires COOP/COEP headers, no cross-process benefit for this use case.

---

## Decision 2: Lock-State Implementation

**Decision**: A single boolean flag `isCapturingPost` in the renderer scope. Set to `true` when a violation triggers the capture; set back to `false` only after `finalizeClip()` resolves (i.e., after the IPC call to `save-and-upload-clip` returns). Any violation event arriving while `isCapturingPost === true` is pushed onto a shared `clipViolations` array and no new capture is initiated.

**Rationale**: A boolean flag is the simplest possible mutex for single-threaded JavaScript. The renderer event loop ensures no concurrent mutation. The flag is local to the exam page's module scope, matching the `examSession` and `submitResult` patterns already used in `main.js`.

**Alternatives considered**:
- Promise-based lock (mutex library) — rejected: unnecessary complexity for single-threaded JS.
- `BroadcastChannel` — rejected: all state lives within one renderer page; no cross-page coordination needed.

---

## Decision 3: Video Encoding Pipeline

**Decision**: WebM/VP9 (renderer) → ffmpeg-python re-encode → H.264 MP4 (Python bridge) before upload. The renderer records with `mimeType: 'video/webm;codecs=vp9'`. The Python bridge re-encodes using `ffmpeg-python` with `vcodec=libx264, acodec=aac, crf=23, preset=fast`.

**Rationale**:
- H.264 MP4 has near-universal browser compatibility for CDN streaming, satisfying the spec requirement that clips be streamable from a CDN URL.
- VP9/WebM is the most reliably supported `mimeType` in Chromium-based Electron; `video/mp4` recording in Electron/Chromium is inconsistent across platforms.
- A CRF of 23 gives good visual quality at moderate file size (~1-2 MB for a 20-second clip at 720p).
- `preset=fast` balances encode time against file size; a 20-second clip encodes in < 3 seconds on modern hardware.

**Alternatives considered**:
- Direct MP4 recording in the renderer — rejected: `video/mp4;codecs=h264` mimeType is unreliable in Electron on Windows due to codec licensing; VP9 is always available.
- Server-side transcoding — rejected: adds latency and infrastructure dependency; local ffmpeg is faster and keeps credentials out of the encoder path.
- No re-encoding (upload WebM directly) — rejected: CDN streaming compatibility for WebM is inconsistent on non-Chrome browsers used by proctors.

---

## Decision 4: Cloud Upload Transport

**Decision**: HTTP PUT to Bunny CDN Storage API using the `requests` library in the Python bridge. Config loaded exclusively from environment variables: `BUNNY_STORAGE_URL`, `BUNNY_API_KEY`, `BUNNY_CDN_BASE_URL`.

**Rationale**:
- Bunny CDN Storage API uses simple HTTP PUT with `AccessKey` header authentication — no SDK required; the `requests` library (already in requirements.txt) is sufficient.
- Environment variables keep credentials out of `config.json` and out of any version-controlled file, satisfying FR-007 and the constitution's Security by Default principle.
- The Python bridge process is the only process that reads these environment variables; they are never forwarded to the Electron renderer via IPC.

**Alternatives considered**:
- AWS S3 / `boto3` — evaluated but rejected to avoid adding a large SDK dependency; also requires more complex presigned URL management.
- Storing credentials in OS keychain via `keytar` — rejected: `keytar` is a Node.js module; the Python bridge has no `keytar` access. Environment variables are the idiomatic Python secret-passing mechanism.
- Storing credentials in `config.json` — **rejected (security violation)**: `config.json` is a version-controlled file visible to the Electron process; storing secrets there would violate FR-007.

---

## Decision 5: IPC Transport for Clip Submission

**Decision**: `ipcRenderer.invoke('save-and-upload-clip', { blobArrayBuffer, metadata })` → `ipcMain.handle('save-and-upload-clip')` → JSON-RPC 2.0 method `upload_clip` over the existing stdin/stdout channel to `router.py`.

**Rationale**: The existing JSON-RPC 2.0 router pattern is already established for all AI service communication (eye-gaze, object detection, speech, face recognition). Adding `upload_clip` as a new method to `router.py` requires no new transport, no new process, and no new IPC channel. The IPC layer stays architecturally consistent with existing usage.

**Constitution Compliance Note**: Constitution Principle II states that Electron communicates with Python via HTTP to `localhost:5050`. However, the existing codebase already uses a second Python process (`router.py`) communicating via stdin/stdout JSON-RPC 2.0 for all AI services. This is a **pre-existing justified deviation** from the constitution that predates this feature. This feature follows the same established deviation — it does not introduce a new transport pattern; it extends an existing one.

**Alternatives considered**:
- Route through Flask server on port 5050 — rejected: clip upload involves binary data (ArrayBuffer → temp file) which is awkward to proxy through Flask HTTP without adding multipart form handling. The router.py path is already optimized for binary payloads via temp files.
- New dedicated Python process — rejected: unnecessary; the router is already active during exams.

---

## Decision 6: Temp File Location and Cleanup

**Decision**: Both the `.webm` temp file (written by Electron main) and the `.mp4` output file (produced by ffmpeg-python) are created in `os.tmpdir()` using `tempfile.mkstemp()`. Both are deleted in a `try/finally` block in `clip_upload_service.py`, guaranteeing cleanup regardless of success or failure (FR-018).

**Rationale**: `os.tmpdir()` is writable on all platforms, OS-managed, and the standard location for process-lifetime temp files. `tempfile.mkstemp()` produces unique names, preventing name collisions when multiple exams run on the same machine. The `try/finally` pattern in Python guarantees cleanup even on exceptions.

**Alternatives considered**:
- Named temp files in the project directory — rejected: pollutes the project tree; harder to discover and clean on crash.
- In-memory encoding — rejected: `ffmpeg-python` requires file paths; in-memory pipe mode with ffmpeg is fragile across platforms.

---

## Decision 7: Filename Convention

**Decision**: `{studentId}/{captureStartTimestamp}_{primaryViolationType}.mp4` where `captureStartTimestamp` is the ISO 8601 UTC clip-window-start timestamp with `:` replaced by `-` (e.g., `2026-05-05T14-32-01.000Z`). `primaryViolationType` is the violation type that originally triggered the capture (e.g., `UNAUTHORIZED_OBJECT`, `GAZE_OFF_SCREEN`).

**Rationale**: URL-safe colons-to-dashes transformation ensures the filename and CDN path are valid in all browsers and HTTP clients without percent-encoding. Grouping by `studentId/` prefix creates a natural namespace in cloud storage. The violation type in the filename allows proctors to quickly scan storage for specific violation types without opening each clip.

**Alternatives considered**:
- UUID-based filename — evaluated; rejected in favor of the semantic convention specified in FR-017 which gives proctors contextual information directly from the filename.
- Percent-encoding colons — rejected: percent-encoded CDN URLs are awkward to share and read.

---

## Decision 8: Confidence Score Representation

**Decision**: Float `0.0–1.0` derived by dividing the orchestrator's integer risk score (`0–100`) by `100.0`. The primary confidence score in `ClipMetadataPayload` reflects the triggering violation's individual detection confidence from the AI service event (already `0.0–1.0` in `ai-service-contract.json`). The orchestrator's risk score is used as a secondary signal only if the detection confidence is not directly available.

**Rationale**: The `ai-service-contract.json` already defines `confidence` as `number, minimum: 0, maximum: 1`. Using the detection event's own confidence directly is the most accurate representation. The ÷100 conversion from risk score is available as a fallback when the detection event's confidence is unavailable (e.g., when the violation is synthesized by the orchestrator rule engine rather than a direct AI confidence output).

---

## Decision 9: Upload Retry Policy

**Decision**: Single retry after a 3-second fixed delay (not exponential backoff). If the retry fails, log the failure, emit a structured `clip:upload-error` IPC event to the renderer, and still emit the violation event to the backend with `upload_failed` status.

**Rationale**: The spec (FR-010/011) explicitly requires "retry once after 3 seconds" — this overrides the original spec's "exponential backoff" language, which was corrected during the clarification session. A single fixed-delay retry is simpler to implement, test, and reason about than an exponential strategy. For a 20-second forensic clip, the total delay before failure declaration is bounded at 3 seconds, keeping the pipeline predictable.

**Alternatives considered**:
- Exponential backoff (3 retries) — was in the original spec; superseded by clarification Q9.
- Retry indefinitely — rejected: unbounded; would hold the lock indefinitely.

---

## Decision 10: Multi-violation Description Format

**Decision**: When a single clip contains `N > 1` violations, the human-readable description is formatted as: `"{primaryDescription} + {N-1} additional violation(s) in clip"`. For example: `"Phone detected in frame + 2 additional violations in clip"`. When N = 1 (only the triggering violation), the description is the violation's own `message` field from the orchestrator alert.

**Rationale**: This matches the exact format specified in clarification Q7 and FR-005. The format is intentionally concise to fit in notification banners and table cells in the proctor dashboard without truncation. The count allows the proctor to know there is more detail in the `allViolations` array without reading all entries.

---

## Resolved Unknowns Summary

| Unknown | Resolution |
|---|---|
| Pre-buffer JavaScript data structure | Circular array of `{ blob, timestamp }` entries, capped at 10 |
| Lock mechanism | Boolean `isCapturingPost` flag, released after IPC call returns |
| Video encoding pipeline | WebM/VP9 → ffmpeg-python → H.264 MP4 |
| Cloud provider | Bunny CDN via HTTP PUT; credentials from env vars only |
| IPC transport | Existing JSON-RPC 2.0 stdin/stdout router; new `upload_clip` method |
| Temp file strategy | `tempfile.mkstemp()` in `os.tmpdir()`; `try/finally` cleanup |
| Filename convention | `{studentId}/{captureStartTimestamp}_{primaryViolationType}.mp4` |
| Confidence score | Direct detection confidence (0.0–1.0); fallback: riskScore ÷ 100 |
| Retry policy | Single retry after 3s fixed delay |
| Multi-violation description | `"{primary} + {N-1} additional violation(s) in clip"` |
