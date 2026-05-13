# Contract: Offline Snapshot File

**Feature**: `014-offline-resilience`
**Date**: 2026-05-13

---

## File Location

```
sessions/{attemptId}_offline_snapshot.json
```

Where `{attemptId}` matches the `Attempt_Id` from the exam session (e.g., `2077`).

---

## Full Schema

```json
{
  "attemptId": "2077",
  "studentId": "b9f61814-ca5a-4e7b-855c-35d5d4e36d9c",
  "currentQuestionIndex": 3,
  "answers": {
    "5": "B",
    "7": "A",
    "9": "D"
  },
  "frozenTimerSeconds": 1740,
  "lockStatus": "active",
  "savedAt": "2026-05-13T07:15:00.000Z",
  "offlineStats": {
    "cumulativeOfflineMs": 120000,
    "disconnectionCount": 1,
    "lastDisconnectAt": "2026-05-13T07:10:00.000Z",
    "lastReconnectAt": "2026-05-13T07:12:00.000Z"
  }
}
```

---

## Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `attemptId` | string | ✅ | Exam attempt ID — matches session log filename |
| `studentId` | string (UUID) | ✅ | Student identifier |
| `currentQuestionIndex` | number (≥0) | ✅ | 0-based index of the question being answered at last save |
| `answers` | object | ✅ | Map of `questionId → answer`. May be `{}` if nothing answered yet |
| `frozenTimerSeconds` | number (≥0) | ✅ | Exam timer value (seconds remaining) at time of last save. Frozen when offline |
| `lockStatus` | `"active"` \| `"locked"` | ✅ | `"locked"` = exam was locked; `"active"` = exam was ongoing |
| `savedAt` | ISO 8601 string | ✅ | Timestamp of last file write |
| `offlineStats.cumulativeOfflineMs` | number (≥0) | ✅ | Total milliseconds spent offline across all disconnections |
| `offlineStats.disconnectionCount` | number (≥0) | ✅ | Number of confirmed offline events (≥ flicker threshold) |
| `offlineStats.lastDisconnectAt` | ISO 8601 \| null | ✅ | Time of most recent confirmed disconnection |
| `offlineStats.lastReconnectAt` | ISO 8601 \| null | ✅ | Time of most recent reconnection (`null` if still offline) |

---

## Recovery Logic (read by main.js on app startup)

```
1. Does sessions/{attemptId}_offline_snapshot.json exist?
   NO  → No prior session. Start fresh.
   YES → Parse JSON.
         Parse error? → Log warning. Start fresh (do not crash).

2. Is lockStatus === 'locked'?
   YES → Load lock screen page. Do NOT restore exam. Attempt auto-submit if online.
   NO  → Restore exam:
           navigate to exam page at currentQuestionIndex
           restore answers into exam state
           set timer display to frozenTimerSeconds
           restore offlineStats into OfflineManager in-memory state
           resume ping loop
```

---

## Write Safety

- Written using `fs.writeFileSync` (synchronous) to avoid partial writes on crash.
- File is fully overwritten on each write — no append, no merge.
- If `fs.writeFileSync` throws (e.g., disk full), the error is logged to the JSONL session log but does NOT crash the app. The in-memory state is still valid for the current session.

---

## Lifecycle

| Event | Action |
|-------|--------|
| Exam starts | File created with `lockStatus: 'active'`, `answers: {}`, `frozenTimerSeconds` = initial exam duration |
| Answer changes | File overwritten with updated `answers` and current `frozenTimerSeconds` |
| 30s heartbeat | File overwritten with current timer and offline stats |
| Offline detected | File overwritten with `frozenTimerSeconds` frozen at current value |
| Exam locked | File overwritten with `lockStatus: 'locked'` |
| Auto-submit succeeds | File deleted — session is complete |
| App crashes | File remains on disk for next startup to recover |
