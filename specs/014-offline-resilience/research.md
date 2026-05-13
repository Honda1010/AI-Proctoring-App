# Research: Offline Resilience

**Feature**: `014-offline-resilience`
**Date**: 2026-05-13
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## 1. Connectivity Detection in Electron

### Decision
Use a periodic `net.fetch()` ping from the **Electron main process** to the LMS `baseUrl` (e.g., `GET {baseUrl}/health` or `HEAD {baseUrl}`) every 5 seconds as the sole connectivity signal. `navigator.onLine` is explicitly NOT used.

### Rationale
- `navigator.onLine` reflects local network adapter state only. A student on a local network with no internet access will see `true` — a false positive that would mask a real outage.
- `net.fetch()` in the main process uses Electron's own network stack (Chromium's net module), which correctly resolves DNS and establishes a TCP connection to the target host, confirming actual reachability of the exam server.
- Using the LMS `baseUrl` as the target means a positive result also implicitly confirms the exam server is up, not just that the student has generic internet.

### Alternatives Considered
- **`navigator.onLine` + ping**: Adds complexity for no benefit since ping alone is sufficient and more reliable.
- **WebSocket keep-alive**: Would require a persistent WebSocket server on the LMS — out of scope and architecturally invasive.
- **Third-party connectivity libraries**: Not justified; `net.fetch()` covers the use case with zero new dependencies.

---

## 2. Local Snapshot Persistence

### Decision
Use `fs.writeFileSync` (synchronous atomic-ish overwrite) from the **Electron main process** to write `sessions/{attemptId}_offline_snapshot.json`. Triggered on every answer change (IPC from renderer) and every 30 seconds via a `setInterval` heartbeat in `main.js`.

### Rationale
- Synchronous write ensures the file is complete before the function returns — critical for crash safety. An async write that is interrupted mid-crash would leave a corrupt file.
- Single-file overwrite (not append) keeps crash recovery simple: read the one file, restore state. No log replay or conflict resolution needed.
- The `sessions/` directory already exists and is writable in all exam scenarios — no new directory creation required.
- 30-second heartbeat guarantees at most 30 seconds of exam-timer drift in the worst crash scenario (student reading without answering).

### Alternatives Considered
- **SQLite / better-sqlite3**: Overkill for a single flat document. Adds a native module dependency that complicates packaging.
- **`localStorage` / IndexedDB in the renderer**: Not accessible from the main process and not crash-safe across unexpected process termination.
- **Append-only JSONL** (like the existing session log): Makes recovery more complex (must replay entire log); single-file is simpler.

---

## 3. Offline State Machine

### Decision
A simple three-state machine owned by `main.js`:

```
ONLINE → OFFLINE (ping fails after 5s interval; only if offline ≥ 2s — flicker guard)
OFFLINE → ONLINE (ping succeeds; exam resumes if not LOCKED)
OFFLINE → LOCKED (budget exhausted OR disconnection count exceeded)
LOCKED  → LOCKED (terminal state; only exit is auto-submit on reconnect)
```

Each state transition fires an IPC event to the renderer via `preload.js` contextBridge.

### Rationale
- Three states cover all spec scenarios with no ambiguity.
- The flicker guard (ignore disconnections < 2s) is implemented by recording `disconnectStartTime` and only transitioning to OFFLINE if `Date.now() - disconnectStartTime >= 2000` at the next ping cycle.
- `LOCKED` is a terminal state — the state machine never transitions back to `ONLINE` from `LOCKED`, only to auto-submit.

### Flicker Guard Implementation
```
Ping fails at T=0  → record disconnectStartTime = T
Ping fails at T=5  → elapsed = 5s ≥ 2s threshold → transition ONLINE→OFFLINE
```
```
Ping fails at T=0  → record disconnectStartTime = T
Ping succeeds at T=5 → elapsed = 5s but reconnected → discard, no transition
```
```
Ping fails at T=0  → record disconnectStartTime = T
Ping fails at T=1* → elapsed = 1s < 2s threshold → stay ONLINE
(* hypothetical sub-5s ping cycle; at 5s intervals the minimum counted offline time is 5s)
```

> **Note**: At a 5-second ping interval, the minimum detectable offline duration is one interval (5s), which is already above the 2-second flicker threshold. The flicker guard therefore primarily protects against rapid reconnect/disconnect scenarios detected within the same interval window.

---

## 4. Exam Timer Freeze

### Decision
The exam timer countdown in the renderer is **paused** (clearInterval) immediately upon receiving the `offline:state-changed { state: 'OFFLINE' }` IPC event. The current timer value is recorded in the snapshot. On reconnect, the renderer restarts the interval from the saved value.

### Rationale
- Freezing the timer is fairer: the student is already consuming their offline budget. Double-penalising them by also consuming exam time would be unjust.
- The saved frozen value in the snapshot also handles crash recovery — if the app crashes while offline, reopening restores the frozen timer rather than a drifted value.

---

## 5. Proctoring Pause/Resume

### Decision
On `ONLINE → OFFLINE` transition:
1. `main.js` sends `proctoring:pause` IPC to the renderer.
2. The renderer's `exam.js` stops all polling intervals (`clearInterval` for each service).
3. No new frames/audio are sent to the Python bridge.

On `OFFLINE → ONLINE` transition (non-locked):
1. `main.js` sends `proctoring:resume` IPC.
2. `exam.js` restarts all polling intervals from `config.json` values.

No changes to the Python bridge are required — it simply stops receiving requests during the offline period.

### Rationale
- Avoids recording spurious violations (face not detected, suspicious gaze) while the student is on the offline page rather than the exam.
- The existing polling architecture in `exam.js` already uses `setInterval` — pausing is a `clearInterval` and resuming is a new `setInterval`. No structural changes needed.

---

## 6. Auto-Submit on Reconnect After Lock

### Decision
When `LOCKED → reconnect` occurs, `main.js` reads the local snapshot, extracts the `answers` array, and calls the existing submit IPC path (`bridge:submit-exam` equivalent) using `net.fetch()` to POST answers to the LMS. No renderer involvement required.

### Rationale
- Reusing the existing submit path minimises new code and ensures the same LMS API contract is respected.
- Doing this in main process (not renderer) means auto-submit works even if the renderer is showing the lock screen UI — no user action needed.

---

## 7. Visual Escalation Thresholds

### Decision
Three visual states on the offline page, driven by `percentRemaining = offlineBudgetRemainingMs / offlineBudgetTotalMs`:

| State | Threshold | CSS class |
|-------|-----------|-----------|
| Neutral | > 50% remaining | `offline--neutral` |
| Warning | ≤ 50% remaining | `offline--warning` |
| Critical | ≤ 20% remaining | `offline--critical` |

CSS custom properties from `design-tokens.css` map to the appropriate color ramp. No hardcoded hex values.

---

## 8. Config.json Schema Addition

### Decision
Add a top-level `"offline_resilience"` section to `config.json`:

```json
"offline_resilience": {
  "_comment": "Offline resilience policy. Adjust without touching code.",
  "max_offline_minutes": 10,
  "max_disconnections": 3,
  "ping_interval_seconds": 5,
  "flicker_threshold_seconds": 2
}
```

### Rationale
- Follows the existing `config.json` pattern (lockdown, orchestration, clip_recording sections all use this convention).
- `ping_interval_seconds` and `flicker_threshold_seconds` are exposed as config values to allow institutions to tune sensitivity without code changes.
