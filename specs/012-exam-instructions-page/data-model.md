# Data Model: Pre-Exam Instructions Page

**Phase**: 1 — Design  
**Feature**: `012-exam-instructions-page`  
**Date**: 2026-05-07

---

## Overview

This feature introduces no new entities and no database schema changes. All data on this page
is either hardcoded UI content (the 8 rules) or read from existing in-memory state
(`examSession` sourced from the OS keychain via `window.bridge.getExamSession()`).

---

## Consumed Data (read-only)

### ExamSession (existing — from OS keychain via bridge)

```
ExamSession {
  attemptId  : string   — validates that the session is active; required for guard
  quizTitle  : string   — optionally displayed in page heading (if provided)
}
```

**Source**: `window.bridge.getExamSession()` — already persisted by `003-exam-access-page`.  
**Usage**: Session guard only. The instructions page does not modify the session.

---

## Produced Data (write — none)

No data written. No IPC payloads. No keychain entries modified. No session log events
(Q2 clarification: no acknowledgment event required).

---

## UI State (ephemeral — lives only in DOM / JS closure)

| Variable | Type | Initial | Description |
|----------|------|---------|-------------|
| `agreeCheckbox.checked` | boolean | `false` | Controls `startBtn.disabled` |
| `isLoading` | boolean | `false` | Controls button text/spinner visibility |

These are not persisted, not shared via IPC, and not visible to the main process.

---

## Hardcoded Content Model

The 8 proctoring rules are static HTML — not fetched, not configurable. Structure:

```
Rule {
  icon   : inline SVG   — 24×24 viewBox, currentColor stroke
  title  : string       — e.g. "Quiet Environment"
  body   : string       — 1–2 sentence description
}
```

All 8 rule items are authored directly in `index.html`. No JSON data file, no IPC.

---

## Existing Data Not Touched

| Entity | Stored in | Status |
|--------|-----------|--------|
| JWT / refresh token | OS keychain (keytar) | Read-only — untouched |
| ExamSession | OS keychain (keytar) | Read-only — guard check only |
| Violation clips / session log | Disk / in-memory | Untouched (no recording on this page) |
