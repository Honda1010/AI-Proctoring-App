# Quickstart: Identity Verification Page

**Feature**: `010-identity-verification`  
**Date**: 2026-04-23

---

## Prerequisites

- Venv activated: `.venv\Scripts\Activate.ps1`
- All Python packages installed: `pip install -r python_bridge/requirements.txt`
- `config.json` updated with the three new `face-recognition` endpoint URLs (see step 1 below)
- Modal app deployed and accessible (or use mock mode — see Mock Testing section)

---

## Step 1: Update config.json

Add three new endpoint URLs under `services.face-recognition`:

```json
"face-recognition": {
  "endpoint_url":         "https://moustafaalaa30--eduai-proctoring-proctoring-serve.modal.run/analysis/verify-file",
  "enroll_endpoint_url":  "https://moustafaalaa30--eduai-proctoring-proctoring-serve.modal.run/analysis/enroll-file",
  "unenroll_endpoint_url": "https://moustafaalaa30--eduai-proctoring-proctoring-serve.modal.run/analysis/unenroll",
  "face_detect_endpoint_url": "https://moustafaalaa30--eduai-proctoring-proctoring-serve.modal.run/analysis/face-detection-file"
}
```

---

## Step 2: Run the App

```powershell
npm start
```

The app starts Electron, spawns the Python Flask bridge (port 5050), and spawns the AI router (stdin/stdout).

---

## Step 3: Happy Path Walkthrough

1. **Login** — enter credentials on the Login page.
2. **Exam Code** — enter a valid exam code; click "JOIN EXAM."
3. **Identity Verification** — the new page loads:
   - Webcam activates automatically
   - Lighting / Focus / Face Detected indicators appear (client-side heuristics)
4. **Capture Photo** — position face and click "Capture Photo."
   - A spinner appears briefly while `POST /analysis/face-detection-file` runs
   - If face detected: live feed freezes; preview shown; "Confirm & Continue" button appears
   - If no face: inline error shown; live feed continues
5. **Confirm & Continue** — click the button:
   - "Verifying identity…" spinner shown; all buttons disabled
   - `POST /analysis/enroll-file` called via AI router
   - On success: navigate to AI Readiness page
   - On failure: error pill shown; live feed resumes
6. **AI Readiness** — calibrate eye-gaze and speech as before.
7. **Exam** — exam page now checks `bridge:get-enrollment-status`; if `enrolled: true`, proceeds.
8. **Submit** — after submission, `unenroll` is called automatically (fire-and-forget).

---

## Step 4: Verify Enrollment in Router Log

The AI router writes to stderr. Check the Electron dev console (F12 → Main Process) or run the router directly:

```powershell
echo '{"jsonrpc":"2.0","method":"enrollReference","params":{"frame":"data:image/jpeg;base64,/9j/4AAQSkZJRg==","sessionId":"test-001"},"id":1}' | .venv\Scripts\python.exe python_bridge\router.py
```

Expected response:
```json
{"jsonrpc":"2.0","id":1,"result":{"ok":true}}
```
or
```json
{"jsonrpc":"2.0","id":1,"result":{"ok":false,"error":{"code":"NO_FACE_DETECTED","message":"..."}}}
```

---

## Mock Testing (Offline — No Modal Connection)

To test the UI flow without a live Modal endpoint:

1. In `router.py`, stub `handle_enroll_reference` to immediately return `{"ok": True}`.
2. Load `frontend/pages/identity-verification/index.html` directly in Electron DevTools → Sources.
3. Use the browser console to simulate:
   ```js
   window.bridge.enrollReference('data:image/jpeg;base64,/9j/...')
   ```
4. Verify the page transitions to "ENROLLED" state and navigates to ai-readiness.

Mock fixtures for the JSON-RPC layer are in `specs/010-identity-verification/mocks/`.

---

## Verify Unenroll on Exam Exit

After exam submission, verify the Modal embedding is cleared:

1. Submit the exam.
2. Check Electron main process logs for: `unenrollReference sent for session <id>`.
3. Attempt to call `POST /analysis/verify-file` manually with the same `session_id` — it should return a 404 or "session not found" response from Modal (embedding cleared).

---

## Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Webcam doesn't activate | Camera permission denied in OS settings | Grant camera access to Electron in OS Privacy settings |
| "No face detected" on every capture | Modal face-detection endpoint unreachable | Check network; verify `face_detect_endpoint_url` in config.json |
| Enrollment spinner never resolves | Modal cold start >30s (httpx timeout) | Increase `timeout` in `ModalClient.__init__` or wait for Modal warm-up |
| Exam page redirects to identity-verification | `enrollmentState` is null | Complete the full verification flow; check router logs for errors |
| Exam page loads without verification guard | `bridge:get-enrollment-status` handler missing | Verify `main.js` IPC handler is registered |
