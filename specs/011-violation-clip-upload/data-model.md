# Data Model: Violation Clip Recording & Upload

**Phase**: 1 — Design  
**Feature**: 011-violation-clip-upload  
**Date**: 2026-05-05  

---

## Entities

### 1. `BufferChunk` (In-Memory, Renderer)

Represents one one-second slice of webcam footage held in the rolling pre-violation buffer.

| Field | Type | Description |
|-------|------|-------------|
| `blob` | `Blob` | Raw video chunk emitted by `MediaRecorder.ondataavailable` |
| `timestamp` | `string` (ISO 8601 UTC) | Capture time, recorded at the moment the `ondataavailable` event fires |

**Validation rules**:
- `timestamp` MUST be a valid ISO 8601 UTC string (e.g., `2026-05-05T14:32:01.000Z`)
- Buffer is capped at `config.clip_recording.pre_buffer_seconds` entries (default 10); oldest entry is shifted off on overflow

**Lifecycle**: Created continuously during an active exam session. Discarded when the exam session ends or when shifted out of the ring buffer on overflow.

---

### 2. `ClipViolationEntry` (In-Memory, Renderer + Python)

A single violation event captured within a clip's time window. Multiple entries can belong to one `ViolationClip`.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `violationType` | `string` | Non-empty; one of the orchestrator alert codes (e.g., `UNAUTHORIZED_OBJECT`, `GAZE_OFF_SCREEN`, `NO_FACE_DETECTED`, `SPEECH_DETECTED`, `UNAUTHORIZED_PERSON`, `SPOOF_DETECTED`) | The alert code emitted by the orchestrator |
| `confidence` | `number` | `0.0–1.0` float | Detection confidence from the AI service event; fallback: `riskScore / 100.0` |
| `timestamp` | `string` | ISO 8601 UTC | When this individual violation was detected |
| `description` | `string` | Non-empty | Human-readable description from the orchestrator alert `message` field |

---

### 3. `ClipMetadata` (In-Memory, Renderer → IPC → Python)

The complete metadata object assembled in the renderer by `finalizeClip()` and transmitted to the Electron main process alongside the raw clip blob.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `studentId` | `string` | Non-empty | Identifier of the exam taker |
| `examAttemptId` | `string` | Non-empty | Identifier of the current exam attempt |
| `captureWindowStart` | `string` | ISO 8601 UTC | Timestamp of the first pre-violation buffer chunk; derived from `preViolationChunks[0].timestamp` |
| `captureWindowEnd` | `string` | ISO 8601 UTC | Timestamp of the last post-violation chunk; derived from the timestamp of the final `postViolationChunks` entry |
| `primaryViolationType` | `string` | Non-empty | The violation type of the event that originally triggered the capture (used in filename) |
| `primaryConfidence` | `number` | `0.0–1.0` | Confidence of the triggering violation |
| `allViolations` | `ClipViolationEntry[]` | Min 1 entry | All violations captured within the clip window, including the triggering event |
| `description` | `string` | Non-empty | Human-readable summary: single violation → violation `description`; multiple → `"{primary description} + {N-1} additional violation(s) in clip"` |
| `sessionId` | `string` | Non-empty | Current exam session ID (for correlating with JSONL session log) |

**State transitions**:
```
[violation triggered]
       │
       ▼
  ClipMetadata created with:
  - primaryViolationType = triggering event type
  - allViolations = [triggering violation]
  - captureWindowStart = preViolationChunks[0].timestamp
       │
       ▼ (each subsequent violation during lock)
  allViolations.push(new ClipViolationEntry)
       │
       ▼ (10 post-violation chunks collected)
  captureWindowEnd = final post-chunk timestamp
  description = computed
       │
       ▼
  Serialised → IPC → Python
```

---

### 4. `ClipUploadRequest` (IPC Payload: Renderer → Main → Python)

The data packet sent over `ipcRenderer.invoke('save-and-upload-clip', ...)`.

| Field | Type | Description |
|-------|------|-------------|
| `blobArrayBuffer` | `ArrayBuffer` | The merged pre+post clip converted to ArrayBuffer |
| `metadata` | `ClipMetadata` | See above |

**IPC serialisation**: `ArrayBuffer` is structured-clone-serialisable and passes through Electron's IPC layer without conversion. The main process writes it directly to a temp `.webm` file.

---

### 5. `JsonRpcUploadClipParams` (Python bridge: `upload_clip` method params)

The parameters object of the JSON-RPC 2.0 request sent from the Electron main process to `router.py`.

| Field | Type | Description |
|-------|------|-------------|
| `tempFilePath` | `string` | Absolute path to the temp `.webm` file written by Electron main |
| `metadata` | `ClipMetadata` | Forwarded verbatim from the IPC payload |
| `studentId` | `string` | Extracted from `metadata.studentId` for convenience |
| `examAttemptId` | `string` | Extracted from `metadata.examAttemptId` for convenience |

---

### 6. `ViolationClip` (Backend-bound result)

The canonical clip record as stored in the backend database. This is what the backend API endpoint persists when it receives the `AiProctoringViolationEvent`.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `clipId` | `string` (UUID) | Unique, generated by backend | Persistent clip identifier |
| `studentId` | `string` | Non-empty | Student identifier |
| `examAttemptId` | `string` | Non-empty | Exam attempt identifier |
| `captureWindowStart` | `string` | ISO 8601 UTC | Clip start timestamp |
| `captureWindowEnd` | `string` | ISO 8601 UTC | Clip end timestamp |
| `evidenceUrl` | `string` (URL) \| `null` | Nullable on failure | CDN-hosted URL of the uploaded clip |
| `uploadStatus` | `enum` | `pending` \| `success` \| `upload_failed` \| `clip_unavailable` | Final disposition of the upload attempt |
| `reasonCode` | `string` \| `null` | Nullable | Machine-readable reason on failure (e.g., `WEBCAM_UNAVAILABLE`, `UPLOAD_EXHAUSTED`) |
| `primaryConfidence` | `number` | `0.0–1.0` | AI confidence of the triggering violation |
| `description` | `string` | Non-empty | Human-readable summary |
| `allViolations` | `ClipViolationEntry[]` | Min 1 | All violations in the clip window |

---

### 7. `AiProctoringViolationEvent` (Backend API payload: Python → LMS)

The structured event emitted by the Python bridge to the backend API endpoint after upload completes (success or failure).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `studentId` | `string` | Non-empty | Student identifier |
| `examAttemptId` | `string` | Non-empty | Exam attempt identifier |
| `evidenceUrl` | `string` \| `null` | Nullable | CDN-hosted clip URL; `null` on failure |
| `uploadStatus` | `string` | `success` \| `upload_failed` \| `clip_unavailable` | Upload outcome |
| `reasonCode` | `string` \| `null` | Nullable | Reason on failure |
| `captureWindowStart` | `string` | ISO 8601 UTC | |
| `captureWindowEnd` | `string` | ISO 8601 UTC | |
| `primaryViolationType` | `string` | Non-empty | Alert code of triggering violation |
| `primaryConfidence` | `number` | `0.0–1.0` | |
| `description` | `string` | Non-empty | Human-readable summary |
| `allViolations` | `ClipViolationEntry[]` | Min 1 | |
| `sessionId` | `string` | Non-empty | Exam session identifier |

---

## Configuration Constants (`config.json` — `clip_recording` key)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `pre_buffer_seconds` | `integer` | `10` | Size of the ring buffer in entries (1 entry = 1 second) |
| `post_buffer_seconds` | `integer` | `10` | Number of post-violation chunks to collect |
| `chunk_duration_ms` | `integer` | `1000` | MediaRecorder timeslice in milliseconds |
| `mime_type` | `string` | `"video/webm;codecs=vp9"` | MediaRecorder mimeType |
| `ffmpeg_crf` | `integer` | `23` | ffmpeg H.264 CRF quality setting |
| `ffmpeg_preset` | `string` | `"fast"` | ffmpeg H.264 preset |
| `upload_retry_delay_ms` | `integer` | `3000` | Delay before single upload retry in milliseconds |

---

## Entity Relationships

```
BufferChunk (n) ─────── assembled into ────▶ ClipUploadRequest.blobArrayBuffer
                                                    │
                                                    ▼
                               ┌─────────────────────────────────┐
                               │         ClipMetadata             │
                               │  ┌─────────────────────────────┐│
                               │  │ allViolations (1..N)         ││
                               │  │  └── ClipViolationEntry      ││
                               │  └─────────────────────────────┘│
                               └──────────────┬──────────────────┘
                                              │ IPC + JSON-RPC
                                              ▼
                               ┌─────────────────────────────────┐
                               │    clip_upload_service.py        │
                               │  .webm temp ──ffmpeg──▶ .mp4    │
                               │  HTTP PUT ──▶ Bunny CDN          │
                               └──────────────┬──────────────────┘
                                              │
                                              ▼
                               AiProctoringViolationEvent ──▶ Backend API
                                              │
                                              ▼
                                       ViolationClip (persisted)
```

---

## State Machine: Clip Capture Lifecycle

```
IDLE
  │
  │  violation event received
  ▼
CAPTURING_POST  (isCapturingPost = true)
  │  · snapshot preViolationChunks from ring buffer
  │  · begin counting postViolationChunks
  │  · absorb additional violations into allViolations[]
  │
  │  10 post-chunks collected  OR  exam session ends
  ▼
FINALIZING
  │  · merge blobs → single Blob
  │  · compute description, captureWindowEnd
  │  · convert to ArrayBuffer
  │  · invoke IPC 'save-and-upload-clip'
  │
  ├──▶ (Python: write temp .webm → encode → upload → emit backend event → cleanup)
  │
  │  IPC call returns
  ▼
IDLE  (isCapturingPost = false)
```

**Error sub-states** (all transition back to IDLE after handling):
- `UPLOAD_FAILED_AFTER_RETRY` → backend event emitted with `upload_failed`; `clip:upload-error` IPC sent to renderer
- `WEBCAM_UNAVAILABLE` → backend event emitted with `clip_unavailable`; no upload attempted
- `EXAM_ENDED_DURING_CAPTURE` → force-finalize with available post-chunks → same FINALIZING flow
