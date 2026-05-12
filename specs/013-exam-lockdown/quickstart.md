# Quickstart: Exam Lockdown (013)

**Purpose**: Manual verification steps for each lockdown concern after implementation.  
**Prerequisites**: App running via `npm start`, Python bridge running, a valid exam session reachable.

---

## Concern 1 — Fullscreen Enforcement

**Steps:**
1. Launch the app and log in.
2. Enter a valid exam code and start the exam.
3. Verify the window is frameless and fills the entire screen (no title bar, no borders).
4. Attempt to resize the window — drag attempts should have no effect.
5. Attempt to move the window — drag attempts should have no effect.
6. Press the Windows taskbar — it should not bring the window to a non-fullscreen state.
7. Press the window's close gesture (if visible) — nothing should happen while the exam is active.
8. Submit the exam or navigate back to the home page. Verify the window returns to normal Chrome (title bar visible, resizable).

**Expected:** All constraints active during exam; fully released after session ends.

---

## Concern 2 — Keyboard Shortcut Blocking

**Steps (during active exam session):**

| Shortcut | Expected result |
|----------|----------------|
| Ctrl+C | No text copied to clipboard |
| Ctrl+V | No paste effect |
| Ctrl+A | No select-all effect |
| Ctrl+X | No cut effect |
| Ctrl+W | Page does not close |
| Escape | Nothing happens |
| F11 | Page does not toggle fullscreen |
| Ctrl+Shift+I | DevTools panel does not open |
| F12 | DevTools panel does not open |
| PrintScreen | Clipboard not updated with exam content |
| Alt+PrintScreen | Clipboard not updated |

**Steps (after exam session ends):**
- Press each shortcut above — verify normal OS/browser behaviour is restored.
- Press F12 — DevTools should open normally.

---

## Concern 3 — VM and Remote Desktop Detection

**VM detection test (requires a VM):**
1. Run the app inside VirtualBox or VMware.
2. Start an exam session.
3. Within ~5 seconds, verify a blocking modal appears containing a reason string such as `"VirtualBox detected via registry SCSI key"`.
4. Open `sessions/{attemptId}.jsonl` and verify a `VIRTUAL_ENVIRONMENT` record was appended.
5. Click "Acknowledge" — verify exam interaction resumes immediately.
6. Wait 60 seconds — verify the modal re-appears (violation still present).

**Remote desktop test:**
1. Run the app on a physical machine.
2. Start an exam session.
3. Launch TeamViewer or AnyDesk.
4. Within 60 seconds, verify the blocking modal appears with the process name in the reason.
5. Verify a `VIRTUAL_ENVIRONMENT` alert is appended to the session JSONL.

**Bridge unavailability test:**
1. Stop the Python bridge process.
2. Start an exam session.
3. Verify no modal appears and no error is surfaced — exam continues silently.

---

## Concern 4 — Screenshot and Screen Capture Blocking

**Content protection test:**
1. Start an exam session.
2. Press PrintScreen.
3. Open an image editor (e.g., Paint) and paste (Ctrl+V) — the exam window should appear as a solid black rectangle.
4. Open the Snipping Tool (if accessible via Start menu — Win+Shift+S will be blocked) and attempt to snip the exam window — it should appear black.
5. End the exam session and verify the window is capturable normally (paste in Paint shows the app).

**Screen-capture process test:**
1. Open OBS Studio or ShareX before starting the exam.
2. Start an exam session.
3. Within ~5 seconds, verify a blocking modal appears with the process name in the reason.
4. Verify a `SCREEN_CAPTURE_DETECTED` alert is appended to the session JSONL.
5. Close OBS/ShareX. Wait for the next 60-second check — modal should not re-appear.

---

## Full Session Log Verification

After completing a test run involving violations, open the session JSONL file:

```
sessions/{attemptId}.jsonl
```

Expected record types visible:
- `VIRTUAL_ENVIRONMENT` — one per VM/RDP detection cycle that found a violation
- `SCREEN_CAPTURE_DETECTED` — one per screen-capture detection cycle that found a violation
- `FULLSCREEN_ESCAPE_ATTEMPT` — one per OS-forced fullscreen exit

Each record must have: `type`, `timestamp` (UTC ISO), `sessionId` (string), `reason` (string or null).

---

## Periodic Check Cancellation Verification

1. Start an exam session — verify the environment check runs immediately.
2. Submit the exam (or log out, or back-to-home).
3. Wait 65 seconds after session end — verify no environment check runs (no console output from `/check-environment` calls, no modals on non-exam pages).
