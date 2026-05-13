# Quickstart: Testing Offline Resilience

**Feature**: `014-offline-resilience`
**Date**: 2026-05-13

---

## Prerequisites

- App running via `npm start`
- Python bridge running via `py python_bridge\server.py --port 5050 --config config.json`
- A valid exam session active (student logged in, exam started)
- `config.json` has `offline_resilience` section added (see Step 0 below)

---

## Step 0 — Add Config Section

Add the following to `config.json` before running any tests:

```json
"offline_resilience": {
  "_comment": "Offline resilience policy. Adjust without touching code.",
  "max_offline_minutes": 1,
  "max_disconnections": 2,
  "ping_interval_seconds": 5,
  "flicker_threshold_seconds": 2
}
```

> Using `max_offline_minutes: 1` and `max_disconnections: 2` makes the lock scenario testable quickly. Restore production values after testing.

---

## Test 1 — Graceful Offline Transition (FR-001, FR-002, FR-003, FR-004)

1. Start an exam session and answer 3+ questions.
2. Disable your network adapter (Windows → Network & Internet Settings → Disable adapter).
3. **Within 10 seconds**, verify:
   - App exits fullscreen.
   - Offline page appears showing a live countdown (budget remaining) and answered question count.
   - The countdown matches `max_offline_minutes` minus any elapsed offline time.
4. Re-enable your network adapter.
5. Verify the offline page fades out and the exam resumes on the same question.

**Pass**: All 4 checks succeed.

---

## Test 2 — Timer Freeze on Disconnect (FR-012, clarification Q4)

1. Note the exam timer value (e.g., 28:30).
2. Disable the network adapter.
3. Wait exactly 30 seconds.
4. Re-enable the network adapter.
5. Verify the exam timer resumes from approximately 28:30 (not 28:00).

**Pass**: Timer delta ≤ 2 seconds from the frozen value (accounting for ping detection latency).

---

## Test 3 — Budget Exhaustion → Lock Screen (FR-008, FR-010)

1. Set `max_offline_minutes: 1` in config.json and restart the app.
2. Start an exam, answer 2+ questions.
3. Disable the network adapter.
4. Wait 65 seconds (> 1 minute budget).
5. Verify the offline page transforms into a lock screen with a clear "exam locked" message.
6. Re-enable the network adapter.
7. Verify answered questions are submitted automatically (check LMS or server logs).

**Pass**: Lock screen appears at budget exhaustion; auto-submit fires on reconnect.

---

## Test 4 — Disconnection Limit → Lock Screen (FR-009)

1. Set `max_disconnections: 2` in config.json and restart the app.
2. Disconnect → wait 6s → reconnect. (Disconnection 1)
3. Disconnect → wait 6s → reconnect. (Disconnection 2)
4. Disconnect again. (Disconnection 3 — exceeds limit of 2)
5. Verify the lock screen appears immediately on the 3rd disconnection regardless of remaining budget.

**Pass**: Lock triggers on the 3rd disconnection.

---

## Test 5 — Visual Escalation (FR-019, SC-008)

1. Set `max_offline_minutes: 5` in config.
2. Disconnect and observe the offline page.
3. After ~2.5 minutes offline (50% consumed), verify the page switches to amber/warning style.
4. After ~4 minutes offline (80% consumed / 20% remaining), verify the page switches to red/critical style.

**Pass**: Both transitions occur at the correct thresholds.

---

## Test 6 — Crash Recovery (FR-014, FR-015)

**Sub-test A — Active session recovery**:
1. Start an exam, answer 5 questions.
2. Force-quit the app (Task Manager → End Task).
3. Reopen via `npm start`.
4. Verify the exam resumes at the same question with all 5 answers intact and the timer at the frozen value.

**Sub-test B — Locked session recovery**:
1. Let the exam lock (via Test 3 or 4 above).
2. Force-quit the app.
3. Reopen.
4. Verify the lock screen appears — the exam does NOT resume.

**Pass**: Both sub-tests produce the expected state.

---

## Test 7 — Flicker Guard (Clarification Q2 note)

1. Disconnect your network adapter.
2. Reconnect within 2 seconds.
3. Verify the offline page does NOT appear and no disconnection is counted.

> At a 5-second ping interval this may be hard to trigger precisely. You can lower `ping_interval_seconds` to 1 temporarily for this test.

**Pass**: No offline page; disconnection count remains 0.

---

## Test 8 — Proctoring Pause During Offline (FR-018)

1. Open DevTools on the exam renderer page.
2. Disconnect the network adapter.
3. Verify in DevTools console that polling intervals (eye gaze, face recognition, etc.) are cleared (no fetch calls firing to Python bridge).
4. Reconnect.
5. Verify polling resumes (fetch calls reappear in network tab).

**Pass**: No proctoring calls during offline period; all resume after reconnect.

---

## Snapshot File Inspection

The snapshot file can be found at:
```
sessions\{attemptId}_offline_snapshot.json
```

Open with any text editor to verify `lockStatus`, `frozenTimerSeconds`, `answers`, and `offlineStats` are correct after each test scenario.
