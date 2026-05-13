# Contract: Offline IPC Channels

**Feature**: `014-offline-resilience`
**Date**: 2026-05-13
**Direction**: `main.js` ↔ renderer (`exam.js` / `offline.js`) via `preload.js` contextBridge

---

## Overview

All offline state management lives in `main.js`. The renderer is a pure consumer of state events and a producer of snapshot-trigger events. No renderer code reads the filesystem or makes ping requests directly.

---

## Channels: main.js → renderer (RECEIVE)

These channels must be added to `ALLOWED_RECEIVE_CHANNELS` in `preload.js`.

### `offline:state-changed`

Fired on every state transition: `ONLINE → OFFLINE`, `OFFLINE → ONLINE`, `OFFLINE → LOCKED`.

**Payload**:
```json
{
  "state": "OFFLINE | ONLINE | LOCKED",
  "budgetRemainingMs": 480000,
  "budgetTotalMs": 600000,
  "disconnectionCount": 1,
  "maxDisconnections": 3,
  "answeredCount": 7,
  "lockReason": "budget_exhausted | disconnection_limit | null"
}
```

**Renderer behaviour per state**:

| State | exam.js action | offline.js action |
|-------|----------------|-------------------|
| `OFFLINE` | Stop all polling intervals; freeze timer display; navigate to offline page | Show offline page; start countdown render |
| `ONLINE` | Restart all polling intervals; unfreeze timer; navigate back to exam page | Fade out offline page |
| `LOCKED` | — | Transform page into lock screen |

---

### `offline:snapshot-request`

Fired by `main.js` heartbeat (every 30s) requesting the renderer send current state for snapshotting.

**Payload**: `null` (no data)

**Renderer behaviour**: `exam.js` responds with `offline:snapshot-data`.

---

### `proctoring:pause`

Fired when transitioning to `OFFLINE`. Renderer stops all AI polling intervals.

**Payload**: `null`

---

### `proctoring:resume`

Fired when transitioning from `OFFLINE → ONLINE` (non-locked). Renderer restarts all AI polling intervals using config values.

**Payload**: `null`

---

## Channels: renderer → main.js (SEND)

These channels must be in the `send`/`invoke` allowlist in `preload.js`.

### `offline:snapshot-data`

Sent by `exam.js` in response to `offline:snapshot-request` OR on every answer change.

**Payload**:
```json
{
  "currentQuestionIndex": 3,
  "answers": { "q5": "B", "q7": "A", "q9": "D" },
  "frozenTimerSeconds": 1740
}
```

> `frozenTimerSeconds` is the current displayed timer value at time of send. Main process uses this to overwrite the snapshot field.

---

## contextBridge API (preload.js additions)

```js
// Additions to the existing contextBridge.exposeInMainWorld('bridge', {...}) block:

onOfflineStateChanged: (callback) =>
  ipcRenderer.on('offline:state-changed', (_, payload) => callback(payload)),

onSnapshotRequest: (callback) =>
  ipcRenderer.on('offline:snapshot-request', (_, payload) => callback(payload)),

onProctoringPause: (callback) =>
  ipcRenderer.on('proctoring:pause', () => callback()),

onProctoringResume: (callback) =>
  ipcRenderer.on('proctoring:resume', () => callback()),

sendSnapshotData: (data) =>
  ipcRenderer.send('offline:snapshot-data', data),
```

---

## Ping Endpoint

`main.js` uses `net.fetch()` to ping:

```
HEAD {config.baseUrl}
```

- **Success**: HTTP 2xx or 3xx response within `ping_interval_seconds` → connectivity confirmed
- **Failure**: Network error, timeout, or HTTP 5xx → connectivity lost
- **Interval**: `config.offline_resilience.ping_interval_seconds` (default: 5)

No new Flask endpoint required on the Python bridge side.
