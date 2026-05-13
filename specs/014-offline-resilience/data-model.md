# Data Model: Offline Resilience

**Feature**: `014-offline-resilience`
**Date**: 2026-05-13

---

## 1. `LocalExamSnapshot` — Local Persistence File

**File path**: `sessions/{attemptId}_offline_snapshot.json`
**Write trigger**: Every answer change (IPC from renderer) + every 30s heartbeat
**Write mode**: Synchronous atomic overwrite (`fs.writeFileSync`)

```json
{
  "attemptId": "string — exam attempt ID (e.g. '2077')",
  "studentId": "string — UUID",
  "currentQuestionIndex": "number — 0-based index of the active question",
  "answers": {
    "questionId": "student answer value (string | number | string[])"
  },
  "frozenTimerSeconds": "number — exam timer value (seconds remaining) at last save",
  "lockStatus": "enum: 'active' | 'locked'",
  "savedAt": "ISO 8601 timestamp of last write",
  "offlineStats": {
    "cumulativeOfflineMs": "number — total offline milliseconds accumulated this session",
    "disconnectionCount": "number — number of confirmed offline events (≥ flicker threshold)",
    "lastDisconnectAt": "ISO 8601 | null",
    "lastReconnectAt": "ISO 8601 | null"
  }
}
```

**Validation rules**:
- `lockStatus` must be `'active'` to restore an active exam on reopen. If `'locked'`, the lock screen is shown immediately.
- `frozenTimerSeconds` must be ≥ 0. If missing or negative (corrupt), treat as 0 and show lock screen.
- `answers` may be an empty object `{}` for a student who answered nothing before the crash.
- If the file is missing or JSON parse fails, treat as no prior session (no restore).

**State transitions**:
```
(file absent)  → no restore; start fresh
lockStatus = 'active' → restore exam at currentQuestionIndex with frozenTimerSeconds
lockStatus = 'locked' → show lock screen; do not restore exam
```

---

## 2. `OfflineConfig` — Config.json Section

**Source**: `config.json` → `offline_resilience` key, read by `main.js` at startup.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_offline_minutes` | number | `10` | Maximum cumulative offline time (minutes) allowed per session |
| `max_disconnections` | number | `3` | Maximum number of confirmed disconnection events allowed |
| `ping_interval_seconds` | number | `5` | How often (seconds) to ping the LMS to check connectivity |
| `flicker_threshold_seconds` | number | `2` | Disconnections shorter than this (seconds) are ignored |

---

## 3. `OfflineSessionStats` — In-Memory Runtime Object

Maintained in `main.js` during an active session. Persisted as `offlineStats` inside the snapshot file.

| Field | Type | Description |
|-------|------|-------------|
| `cumulativeOfflineMs` | number | Total ms spent offline (accumulated across all disconnections) |
| `disconnectionCount` | number | Number of confirmed offline events so far |
| `lastDisconnectAt` | Date \| null | Timestamp of the most recent ONLINE→OFFLINE transition |
| `lastReconnectAt` | Date \| null | Timestamp of the most recent OFFLINE→ONLINE transition |
| `budgetRemainingMs` | number (derived) | `(max_offline_minutes * 60000) - cumulativeOfflineMs` |
| `percentRemaining` | number (derived) | `budgetRemainingMs / (max_offline_minutes * 60000)` — used for visual escalation |

---

## 4. `OfflineStateEvent` — IPC Payload (main → renderer)

Sent on every state transition via `offline:state-changed` IPC channel.

```json
{
  "state": "enum: 'OFFLINE' | 'ONLINE' | 'LOCKED'",
  "budgetRemainingMs": "number",
  "budgetTotalMs": "number",
  "disconnectionCount": "number",
  "maxDisconnections": "number",
  "answeredCount": "number — count of non-null entries in answers object",
  "lockReason": "enum: 'budget_exhausted' | 'disconnection_limit' | null"
}
```

---

## 5. Session Flag — LMS / JSONL Record

When a locked session is never submitted, a flag record is appended to `sessions/{attemptId}.jsonl` (existing log format):

```json
{
  "type": "OFFLINE_SESSION_FLAGGED",
  "timestamp": "ISO 8601",
  "sessionId": "attemptId",
  "reason": "never_reconnected",
  "cumulativeOfflineMs": "number",
  "disconnectionCount": "number",
  "answeredCount": "number"
}
```

This record is written when the app closes with `lockStatus = 'locked'` and no auto-submit has been triggered.

---

## State Transition Diagram

```
                    ┌────────────┐
          ┌────────▶│   ONLINE   │◀────────────────┐
          │         └─────┬──────┘                 │
          │     ping ok   │ ping fails             │
          │               │ (≥ flicker threshold)  │ ping ok
          │               ▼                        │ (budget ok)
          │         ┌────────────┐                 │
          │         │  OFFLINE   │─────────────────┘
          │         └─────┬──────┘
          │               │ budget exhausted
          │               │  OR disconnections > max
          │               ▼
          │         ┌────────────┐
          │         │   LOCKED   │
          │         └─────┬──────┘
          │               │ reconnect
          │               ▼
          │         auto-submit → done
          └── (crash recovery skips to ONLINE or LOCKED based on snapshot.lockStatus)
```
