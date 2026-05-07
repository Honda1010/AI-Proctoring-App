# Quickstart: Violation Clip Recording & Upload

**Feature**: 011-violation-clip-upload  
**Branch**: `013-violation-clip-upload`  
**Date**: 2026-05-05  

This guide explains how to set up, develop, and test the violation clip feature end-to-end on a local machine.

---

## Prerequisites

- Node.js 20 LTS + Electron 33+ (existing project setup)
- Python 3.11+ with `.venv` active (`c:\Users\mohaned\Documents\AI-Proctoring-App\.venv`)
- `ffmpeg` installed and on `PATH` (required by `ffmpeg-python`)
- Bunny CDN storage bucket provisioned with a `Storage Zone` and CDN pull zone
- Three environment variables set in your shell before launching:

```sh
# Windows PowerShell
$env:BUNNY_STORAGE_URL = "https://storage.bunnycdn.com/your-storage-zone"
$env:BUNNY_API_KEY     = "your-access-key"
$env:BUNNY_CDN_BASE_URL = "https://your-pullzone.b-cdn.net"
```

> **NEVER** put these values in `config.json`, `.env` files tracked by git, or any Electron process.

---

## Installing New Dependencies

```powershell
# Python: add ffmpeg-python to requirements.txt and install
cd c:\Users\mohaned\Documents\AI-Proctoring-App
.venv\Scripts\Activate.ps1
pip install ffmpeg-python
```

Verify ffmpeg binary:
```powershell
ffmpeg -version
```

---

## Config: Adding `clip_recording` Block

Add the following block to `config.json` at the top level alongside `services`, `ui`, etc.:

```json
"clip_recording": {
  "pre_buffer_seconds": 10,
  "post_buffer_seconds": 10,
  "chunk_duration_ms": 1000,
  "mime_type": "video/webm;codecs=vp9",
  "ffmpeg_crf": 23,
  "ffmpeg_preset": "fast",
  "upload_retry_delay_ms": 3000
}
```

---

## New Files to Create

```
frontend/pages/exam/
  clip-recorder.js          ← Renderer: ring buffer + capture state machine

frontend/main.js            ← MODIFIED: add ipcMain.handle('save-and-upload-clip')

frontend/preload.js         ← MODIFIED: whitelist new IPC channels

python_bridge/services/
  clip_upload_service.py    ← Python: ffmpeg encode + Bunny CDN upload + backend emit

python_bridge/router.py     ← MODIFIED: register upload_clip JSON-RPC method
```

---

## End-to-End Local Test (Manual)

### Step 1 — Start the app with env vars set

```powershell
$env:BUNNY_STORAGE_URL   = "https://storage.bunnycdn.com/lumina-test"
$env:BUNNY_API_KEY       = "YOUR_TEST_KEY"
$env:BUNNY_CDN_BASE_URL  = "https://lumina-test.b-cdn.net"
npm start
```

### Step 2 — Trigger a mock violation

The exam page calls `window.bridge.aiRpc({ method: 'mockDetection', params: { ... } })` to inject a test violation event. A test script is provided:

```javascript
// In the DevTools console on the exam page:
window.bridge.aiRpc({
  method: 'mockDetection',
  params: {
    service: 'object-detection',
    payload: { suspicious: true, objects: ['phone'], probability: 0.92 },
    sessionId: 'test-session-clip'
  }
});
```

### Step 3 — Observe capture flow

Expected sequence in DevTools console:
1. `[clip-recorder] Violation received: UNAUTHORIZED_OBJECT — isCapturingPost=false → starting capture`
2. `[clip-recorder] Pre-buffer snapshot: 10 chunks (captureWindowStart: ...)`
3. `[clip-recorder] Post-violation chunk collected: 1/10 ... 10/10`
4. `[clip-recorder] finalizeClip() — merging blobs, invoking IPC`
5. `[main] save-and-upload-clip received — writing temp file to os.tmpdir()`
6. Python stderr: `[clip_upload_service] Encoding .webm → .mp4 (CRF=23, preset=fast)`
7. Python stderr: `[clip_upload_service] Uploading to Bunny CDN: stu-XXX/2026-05-05T14-32-01-000Z_UNAUTHORIZED_OBJECT.mp4`
8. Python stderr: `[clip_upload_service] Upload success. evidenceUrl: https://...`
9. Python stderr: `[clip_upload_service] Backend event emitted. Cleaning up temp files.`
10. `[clip-recorder] Upload complete — isCapturingPost=false`

### Step 4 — Verify

- Check your Bunny CDN storage zone for the uploaded `.mp4` file under `{studentId}/`
- Open the CDN URL in a browser — the clip should play
- Check `sessions/{sessionId}.jsonl` for the violation event entry with `evidenceUrl`

---

## Unit Test: Python Upload Service

```powershell
cd c:\Users\mohaned\Documents\AI-Proctoring-App
.venv\Scripts\Activate.ps1
pytest python_bridge/services/test_clip_upload_service.py -v
```

Test cases to cover:
- Successful encode + upload: mock `ffmpeg.run()` and `requests.put()`; assert `evidenceUrl` matches expected CDN path
- Upload failure + retry: mock first PUT returning 500, second returning 200; assert retry fires after 3s
- Upload failure + exhausted: mock both PUTs returning 500; assert `uploadStatus = 'upload_failed'`, `reasonCode = 'UPLOAD_EXHAUSTED'`
- Temp file cleanup: assert both `.webm` and `.mp4` temp files are deleted regardless of success/failure

---

## Unit Test: Renderer Ring Buffer

Open the Electron DevTools console on the exam page and run:

```javascript
// Simulate 15 ondataavailable events — ring buffer should only hold 10
const fakeChunks = Array.from({ length: 15 }, (_, i) => ({
  blob: new Blob(['x']),
  timestamp: new Date(Date.now() + i * 1000).toISOString()
}));
// After pushing 15 chunks, buffer.length should be 10 and buffer[0].timestamp should be chunk 5
```

---

## Debugging Tips

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `MediaRecorder` not starting | `mimeType` unsupported in Electron build | Check `MediaRecorder.isTypeSupported('video/webm;codecs=vp9')` in console |
| `ffmpeg not found` error | ffmpeg not on PATH | Install ffmpeg and restart terminal |
| `BUNNY_API_KEY` missing | Env vars not set | Set env vars before `npm start` |
| Clip is only 10s (no pre-buffer) | Buffer not running before exam start | Ensure `MediaRecorder.start(timeslice)` is called in exam page `onload` / session start |
| `clip:upload-error` event fired | Upload retry exhausted | Check network; verify BUNNY_STORAGE_URL format (must end without trailing `/`) |
| Temp `.webm` file not deleted | Exception in cleanup path | Check Python stderr; the `try/finally` should always clean up — look for permission errors in `os.tmpdir()` |
