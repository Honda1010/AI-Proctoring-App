# Tasks: Violation Clip Recording & Upload

**Input**: Design documents from `specs/011-violation-clip-upload/`  
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅  
**Branch**: `013-violation-clip-upload`  
**Generated**: 2026-05-05

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Can run in parallel (operates on a different file from its peers)
- **[US1/2/3]**: User story this task belongs to
- No story label = Setup or Foundational phase task

---

## Phase 1: Setup

**Purpose**: Add the new configuration key and dependency declaration that every other task depends on. None of these tasks share a file so all three can be done simultaneously.

- [X] T001 Add `clip_recording` block to `config.json` with keys: `pre_buffer_seconds: 10`, `post_buffer_seconds: 10`, `chunk_duration_ms: 1000`, `mime_type: "video/webm;codecs=vp9"`, `ffmpeg_crf: 23`, `ffmpeg_preset: "fast"`, `upload_retry_delay_ms: 3000` — `config.json`
- [X] T002 [P] Add `ffmpeg-python` to `python_bridge/requirements.txt`
- [X] T003 [P] Whitelist two new IPC channels in `frontend/preload.js`: add `'save-and-upload-clip'` to `ALLOWED_INVOKE_CHANNELS` and `'clip:upload-error'` to `ALLOWED_RECEIVE_CHANNELS`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the complete Python upload pipeline and register its JSON-RPC entry point. No renderer work can be end-to-end tested until T011 is done.

**⚠️ CRITICAL**: User story phases MUST NOT begin until T011 is complete.

- [X] T004 Verify `clip_recording` sub-dict is accessible via `load_config()` in `python_bridge/config.py` — confirm the existing loader passes through arbitrary top-level keys; no code change needed if it already does, otherwise add pass-through support — `python_bridge/config.py`
- [X] T005 Create `python_bridge/services/clip_upload_service.py` — define `ClipUploadService` class; load `BUNNY_STORAGE_URL`, `BUNNY_API_KEY`, `BUNNY_CDN_BASE_URL` from `os.environ` in `__init__`; raise `RuntimeError` on missing env var; define public method `upload_clip(temp_webm_path: str, metadata: dict) -> dict` stub returning `{'uploadStatus': 'pending'}` — `python_bridge/services/clip_upload_service.py`
- [X] T006 Implement ffmpeg-python re-encode step in `ClipUploadService.upload_clip()` — use `ffmpeg.input(temp_webm_path).output(temp_mp4_path, vcodec='libx264', acodec='aac', crf=ffmpeg_crf, preset=ffmpeg_preset)` where `temp_mp4_path` is created via `tempfile.mkstemp(suffix='.mp4')[1]`; call `ffmpeg.run(stream, quiet=True)` — `python_bridge/services/clip_upload_service.py`
- [X] T007 Implement Bunny CDN HTTP PUT upload in `ClipUploadService.upload_clip()` — build filename as `f"{student_id}/{url_safe_ts}_{primary_type}.mp4"` where `url_safe_ts = metadata['captureWindowStart'].replace(':', '-')`; PUT `open(temp_mp4_path, 'rb')` to `f"{BUNNY_STORAGE_URL}/{filename}"` with header `{'AccessKey': BUNNY_API_KEY}`; on HTTP 2xx set `evidence_url = f"{BUNNY_CDN_BASE_URL}/{filename}"` — `python_bridge/services/clip_upload_service.py`
- [X] T008 Implement single-retry logic wrapping the PUT call in `ClipUploadService.upload_clip()` — if the first PUT does not return 2xx, wait `upload_retry_delay_ms / 1000` seconds using `time.sleep()`, then retry once; if the retry also fails set `upload_status = 'upload_failed'` and `reason_code = 'UPLOAD_EXHAUSTED'` — `python_bridge/services/clip_upload_service.py`
- [X] T009 Implement `try/finally` temp file cleanup in `ClipUploadService.upload_clip()` — wrap the entire encode-upload block in `try/finally`; in the `finally` block delete both `temp_webm_path` and `temp_mp4_path` with `os.remove()` guarded by `os.path.exists()` — `python_bridge/services/clip_upload_service.py`
- [X] T010 Implement backend violation event POST in `ClipUploadService.upload_clip()` — after upload outcome is determined (success or failure), build `AiProctoringViolationEvent` dict per `specs/011-violation-clip-upload/contracts/backend-violation-event.json`; POST to `f"{base_url}/api/Proctoring/violation-clip"` with `Authorization: Bearer <token>` header (token loaded via the existing `auth.py` pattern); return `{'uploadStatus': upload_status, 'evidenceUrl': evidence_url, 'reasonCode': reason_code}` — `python_bridge/services/clip_upload_service.py`
- [X] T011 Register `upload_clip` JSON-RPC method in `python_bridge/router.py` — in `AIRouter.handle_request()` add `elif method == "upload_clip": await self.handle_upload_clip(request_id, params)`; implement `handle_upload_clip()` async method: instantiate `ClipUploadService(self.config)`, call `await asyncio.get_event_loop().run_in_executor(None, service.upload_clip, params['tempFilePath'], params['metadata'])`, send result with `self.send_response(request_id, result)` — `python_bridge/router.py`

**Checkpoint**: Python upload pipeline complete. Renderer can now call `upload_clip` via IPC and get a real result.

---

## Phase 3: User Story 1 — Proctor Reviews Forensic Clip Evidence (Priority: P1) 🎯 MVP

**Goal**: A violation triggers automatic capture of a 20-second clip (10s pre + 10s post), which is encoded, uploaded to Bunny CDN, and the resulting URL is returned to the renderer.

**Independent Test**: In the exam page DevTools console, call `window.bridge.aiRpc({ method: 'mockDetection', params: { service: 'object-detection', payload: { suspicious: true, objects: ['phone'], probability: 0.92 }, sessionId: 'test-clip' } })`; after ~30 seconds verify `evidenceUrl` appears in the console log and the CDN URL plays in a browser.

- [X] T012 [US1] Create `frontend/pages/exam/clip-recorder.js` module scaffold — declare module-scope variables: `let ringBuffer = []`, `let isCapturingPost = false`, `let clipViolations = []`, `let postChunks = []`, `let mediaRecorder = null`, `let clipConfig = null`, `let activeExamSession = null`; export `initClipRecorder(config, examSession)`, `handleViolationEvent(alert)`, `forceFinalize()`, `stopClipRecorder()` as named exports — `frontend/pages/exam/clip-recorder.js`
- [X] T013 [US1] Implement rolling ring buffer in `clip-recorder.js` — inside `initClipRecorder()`: call `navigator.mediaDevices.getUserMedia({ video: true, audio: false })` to get webcam stream; construct `new MediaRecorder(stream, { mimeType: clipConfig.mime_type })`; in `mediaRecorder.ondataavailable = (e) => { ... }` push `{ blob: e.data, timestamp: new Date().toISOString() }` to `ringBuffer`; if `ringBuffer.length > clipConfig.pre_buffer_seconds` shift the oldest entry; call `mediaRecorder.start(clipConfig.chunk_duration_ms)` — `frontend/pages/exam/clip-recorder.js`
- [X] T014 [US1] Implement violation trigger handler in `clip-recorder.js` — inside `handleViolationEvent(alert)`: if `isCapturingPost === true` append `{ violationType: alert.code, confidence: alert.evidence?.confidence ?? 0, timestamp: alert.timestamp, description: alert.message }` to `clipViolations` and return early; otherwise snapshot `const preViolationChunks = [...ringBuffer]`, set `isCapturingPost = true`, set `postChunks = []`, set `clipViolations = [{ violationType: alert.code, confidence: alert.evidence?.confidence ?? 0, timestamp: alert.timestamp, description: alert.message }]`, then start collecting post chunks — `frontend/pages/exam/clip-recorder.js`
- [X] T015 [US1] Implement post-violation chunk collector and finalizeClip trigger in `clip-recorder.js` — extend the `ondataavailable` handler: after the ring-buffer push, if `isCapturingPost === true` also push the current chunk to `postChunks`; when `postChunks.length >= clipConfig.post_buffer_seconds` call `finalizeClip(preViolationChunks)` (capture `preViolationChunks` in closure at trigger time) — `frontend/pages/exam/clip-recorder.js`
- [X] T016 [US1] Implement `finalizeClip(preViolationChunks)` async function in `clip-recorder.js` — merge blobs: `const merged = new Blob([...preViolationChunks.map(c => c.blob), ...postChunks.map(c => c.blob)], { type: clipConfig.mime_type })`; set `captureWindowStart = preViolationChunks[0]?.timestamp ?? postChunks[0].timestamp`; set `captureWindowEnd = postChunks[postChunks.length - 1].timestamp`; compute `description` (single vs multi-violation format); build `metadata` object per `ClipMetadata` contract; convert blob to ArrayBuffer via `await merged.arrayBuffer()`; call `await window.bridge.saveAndUploadClip({ blobArrayBuffer, metadata })`; after await set `isCapturingPost = false` and clear `clipViolations`, `postChunks` — `frontend/pages/exam/clip-recorder.js`
- [X] T017 [P] [US1] Add `ipcMain.handle('save-and-upload-clip', ...)` handler in `frontend/main.js` — receive `{ blobArrayBuffer, metadata }`; write `Buffer.from(blobArrayBuffer)` to `const tmpPath = path.join(os.tmpdir(), 'clip-' + Date.now() + '.webm')`; call existing `sendAiRpc('upload_clip', { tempFilePath: tmpPath, metadata, studentId: metadata.studentId, examAttemptId: metadata.examAttemptId })`; on result with `uploadStatus === 'upload_failed'` also send `mainWindow?.webContents.send('clip:upload-error', { ... })`; return `{ ok: true, result }` — `frontend/main.js`
- [X] T018 [P] [US1] Expose `saveAndUploadClip(payload)` on `window.bridge` in `frontend/preload.js` — add method to the `contextBridge.exposeInMainWorld('bridge', { ... })` object: `saveAndUploadClip(payload) { return ipcRenderer.invoke('save-and-upload-clip', payload); }` — `frontend/preload.js`
- [X] T019 [US1] Wire `handleViolationEvent` into the exam page AI event listener in `frontend/pages/exam/exam.js` — import/require `clip-recorder.js`; call `initClipRecorder(uiConfig.clip_recording, examSession)` on exam page load after webcam is ready; in the existing `bridge.onAiEvent(...)` callback, when `event.params?.type === 'alert'` call `handleViolationEvent(event.params)` — `frontend/pages/exam/exam.js`

---

## Phase 4: User Story 2 — System Deduplicates Rapid Violations into One Clip (Priority: P2)

**Goal**: Multiple violations within the same 20-second window produce exactly one clip with all violations listed in metadata and the correct summarized description.

**Independent Test**: In DevTools console, fire two `mockDetection` calls 5 seconds apart; verify only one IPC call to `save-and-upload-clip` is made and the returned metadata `allViolations` array has two entries.

- [X] T020 [P] [US2] Verify lock absorption in `clip-recorder.js` — add a `console.debug` log inside the early-return branch of `handleViolationEvent` when `isCapturingPost === true` to confirm absorbed violations: `[clip-recorder] Violation absorbed into active clip: ${alert.code}`; confirm `primaryViolationType` in `metadata` is always from the *first* triggering event, not any absorbed one (already enforced by the snapshot at trigger time in T014) — `frontend/pages/exam/clip-recorder.js`
- [X] T021 [P] [US2] Implement multi-violation description computation in `finalizeClip()` in `clip-recorder.js` — if `clipViolations.length === 1`: `description = clipViolations[0].description`; else: `description = \`${clipViolations[0].description} + ${clipViolations.length - 1} additional violation(s) in clip\`` — `frontend/pages/exam/clip-recorder.js`
- [X] T022 [US2] Implement `forceFinalize()` export in `clip-recorder.js` for exam-end edge case — if `isCapturingPost === true` and `postChunks.length > 0`: call `finalizeClip(preViolationChunksSnapshot)` immediately with whatever post chunks are available (use a module-scope `preViolationChunksSnapshot` variable set at trigger time in T014); if `isCapturingPost === true` and `postChunks.length === 0`: reset lock (`isCapturingPost = false`, clear arrays) and log that no post footage was available — `frontend/pages/exam/clip-recorder.js`
- [X] T023 [US2] Wire `forceFinalize()` on exam session end in `frontend/pages/exam/exam.js` — in the existing exam teardown logic (wherever `stopService` IPC calls are made or the exam is submitted), call `await forceFinalize()` before tearing down the AI router process — `frontend/pages/exam/exam.js`

---

## Phase 5: User Story 3 — Credentials Never Exposed to the Frontend (Priority: P3)

**Goal**: Architectural enforcement that `BUNNY_API_KEY` and all cloud credentials remain exclusively inside the Python bridge process and never appear in any IPC message, log, or renderer-accessible surface.

**Independent Test**: Add a test listener on all IPC traffic via Electron's `ipcMain.on` wildcard (dev-only) and assert that neither `'BUNNY'` nor `'AccessKey'` nor any known credential substring appears in any message payload.

- [X] T024 [P] [US3] Implement `clip:upload-error` push from `frontend/main.js` — in the `save-and-upload-clip` handler (T017), when the JSON-RPC result has `uploadStatus === 'upload_failed'`, call `mainWindow?.webContents.send('clip:upload-error', { studentId: metadata.studentId, examAttemptId: metadata.examAttemptId, sessionId: metadata.sessionId, reasonCode: result.reasonCode ?? 'UPLOAD_EXHAUSTED', timestamp: new Date().toISOString() })`; confirm the send payload contains no credentials or file paths — `frontend/main.js`
- [X] T025 [P] [US3] Add `onClipUploadError(callback)` listener on `window.bridge` in `frontend/preload.js` — add to the `contextBridge` object: `onClipUploadError(callback) { const handler = (_e, payload) => callback(payload); ipcRenderer.on('clip:upload-error', handler); return () => ipcRenderer.removeListener('clip:upload-error', handler); }` — `frontend/preload.js`
- [X] T026 [US3] Implement webcam-unavailable guard in `clip-recorder.js` — in `handleViolationEvent()`, if `ringBuffer.length === 0` and `!isCapturingPost`: log a warning, call `window.bridge.saveAndUploadClip({ blobArrayBuffer: null, metadata: { ...minimalMetadata, uploadStatus: 'clip_unavailable', reasonCode: 'WEBCAM_UNAVAILABLE' } })` so the backend still receives a record; do NOT set `isCapturingPost = true` — `frontend/pages/exam/clip-recorder.js`
- [X] T027 [US3] Audit IPC handler in `frontend/main.js` — verify the `save-and-upload-clip` handler: (a) never logs `blobArrayBuffer` contents, (b) never passes any env var or CDN key to the JSON-RPC params object (only `tempFilePath` and `metadata`), (c) the value returned to the renderer via `ipcMain.handle` return is only `{ ok, result: { uploadStatus, evidenceUrl, reasonCode } }` — no `tempFilePath` in the response — `frontend/main.js`

---

## Final Phase: Polish & Cross-Cutting Concerns

- [X] T028 [P] Create `python_bridge/services/test_clip_upload_service.py` with four pytest test cases: (1) **success path** — mock `ffmpeg.run()` no-op and `requests.put()` returning 200; assert `uploadStatus == 'success'` and `evidenceUrl` starts with `BUNNY_CDN_BASE_URL`; (2) **retry-once path** — mock first PUT returning 500, second returning 200; assert only two PUT calls made and `uploadStatus == 'success'`; (3) **exhausted retry path** — mock both PUTs returning 500; assert `uploadStatus == 'upload_failed'` and `reasonCode == 'UPLOAD_EXHAUSTED'`; (4) **cleanup path** — in all above cases assert neither the `.webm` nor `.mp4` temp files exist after the call completes — `python_bridge/services/test_clip_upload_service.py`
- [X] T029 [P] Implement `stopClipRecorder()` export in `clip-recorder.js` — stop and clean up the `MediaRecorder` and webcam stream: call `mediaRecorder?.stop()`, release the webcam stream tracks via `stream.getTracks().forEach(t => t.stop())`, reset all module-scope state variables to initial values — `frontend/pages/exam/clip-recorder.js`
- [X] T030 Wire `stopClipRecorder()` on exam teardown in `frontend/pages/exam/exam.js` — call `stopClipRecorder()` after `forceFinalize()` completes (T023) in the exam session teardown flow — `frontend/pages/exam/exam.js`

---

## Dependencies Graph

```
T001 ──────────────────────────┐
T002 [P] ───────────────────── ┤ (all Phase 1 independent)
T003 [P] ───────────────────── ┘
                                │
                         T001 ──▶ T004
                                  │
                         T004 ──▶ T005
                                  │
                 T005 ──▶ T006 ──▶ T007 ──▶ T008 ──▶ T009 ──▶ T010
                                                                  │
                                                         T010 ──▶ T011
                                                                  │
┌─────────────────────────────────────────────────────────────────┘
│
T003 ──▶ T018 [P]
T011 ──▶ T017 [P] ──▶ T019 ──▶ T012 ──▶ T013 ──▶ T014 ──▶ T015 ──▶ T016
                                                                       │
                                         (US2 builds on US1 complete) ─┘
                                                                       │
T020 [P] ─┐                                                            │
T021 [P] ─┤ can be done in parallel after T016                        │
T022    ──┤                                                            │
T023    ──┘                                                            │
          │                                                            │
     (US3 builds on US1+US2)                                          │
T024 [P] ─┐                                                            │
T025 [P] ─┤ parallel                                                  │
T026    ──┤                                                            │
T027    ──┘                                                            │
          │                                                            │
T028 [P] ─┐  (Polish: independent)                                    │
T029 [P] ──┤                                                          │
T030     ──┘                                                          │
```

## Parallel Execution Examples

### Story 1 Accelerated (after T011 is done)
```
Stream A: T012 → T013 → T014 → T015 → T016 → T019
Stream B: T017  (main.js — parallel with T012–T016)
Stream C: T018  (preload.js — parallel with T012–T016)
```

### Story 2 + Story 3 in Parallel (after T016 is done)
```
Stream A: T020, T021, T022 → T023  (US2 dedup work)
Stream B: T024, T025, T026, T027   (US3 security hardening)
```

### Polish in Parallel (after T010)
```
Stream A: T028  (Python tests — only needs T005–T010)
Stream B: T029  (stopClipRecorder — only needs T012 scaffold)
```

## Implementation Strategy

**MVP Scope (deliver value fastest)**:
1. Complete Phase 1 (T001–T003) — 10 min
2. Complete Phase 2 (T004–T011) — Python pipeline working and testable
3. Complete Phase 3 (T012–T019) — full end-to-end capture flow

**After MVP**: Phase 4 (dedup hardening) → Phase 5 (security audit) → Polish

**Suggested MVP cut**: T001–T019 = 19 tasks deliver User Story 1 (P1) completely.  
US2 dedup is partially implemented by the lock flag from T014; Phase 4 hardens edge cases.

---

## Task Count Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Phase 1: Setup | T001–T003 | — |
| Phase 2: Foundational | T004–T011 | — |
| Phase 3: US1 (P1) | T012–T019 | US1 |
| Phase 4: US2 (P2) | T020–T023 | US2 |
| Phase 5: US3 (P3) | T024–T027 | US3 |
| Final: Polish | T028–T030 | — |
| **Total** | **30 tasks** | |

| User Story | Task Count |
|------------|-----------|
| US1 (P1) | 8 tasks (T012–T019) |
| US2 (P2) | 4 tasks (T020–T023) |
| US3 (P3) | 4 tasks (T024–T027) |
| Shared Setup/Foundation/Polish | 14 tasks |
