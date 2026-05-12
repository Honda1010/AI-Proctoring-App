# CheatingReport API — AI Proctoring Integration Guide

This document describes every endpoint exposed by `CheatingReportController` and the exact workflow an AI proctoring desktop/web application must follow to record, manage, and query cheating evidence.

---

## Base URL

```
/api/CheatingReport
```

All requests must carry a valid **JWT Bearer token** in the `Authorization` header:

```
Authorization: Bearer <token>
```

---

## Permission Roles

| Permission policy | Who should hold it |
|---|---|
| `CheatingReport:add` | AI Proctoring agent / proctor service account |
| `CheatingReport:read` | Instructor, admin, proctor |
| `CheatingReport:delete` | Admin, proctor |

---

## Endpoints

---

### 1. Create a Cheating Report for a Quiz Attempt

**Triggered when:** the AI proctoring system detects the student has started a proctored quiz attempt and needs a "container" to attach violations to.

```
POST /api/CheatingReport/attempt/{attemptId}
```

**Permission required:** `CheatingReport:add`

**Path parameter:**

| Name | Type | Description |
|---|---|---|
| `attemptId` | `int` | ID of the `QuizAttempt` that is being monitored |

**Request body:** none

**Behaviour:**
- If a report already exists for this `attemptId`, the existing report is returned (idempotent — safe to call on reconnect).
- Otherwise a new empty `CheatingReport` is created and linked to the attempt and student.

**Success response — `201 Created`**

```json
{
  "id": 12,
  "quizAttemptId": 45,
  "studentId": "auth0|abc123",
  "studentName": "Ali Hassan",
  "violations": []
}
```

**Location header** points to `GET /api/CheatingReport/attempt/{attemptId}`.

---

### 2. Add a Violation to a Report

**Triggered when:** the AI proctoring model detects a cheating event (eye tracking deviation, phone detected, tab switch, voice detected, etc.) and uploads the evidence clip to Bunny CDN first, then sends the CDN URL here.

```
POST /api/CheatingReport/{reportId}/violations
```

**Permission required:** `CheatingReport:add`

**Path parameter:**

| Name | Type | Description |
|---|---|---|
| `reportId` | `int` | The `id` returned from the Create endpoint above |

**Request body — `application/json`:**

```json
{
  "evidenceUrl": "https://cdn.bunny.net/proctoring/attempt-45/clip-001.mp4",
  "timestamp": "2026-05-07T10:23:11Z",
  "description": "Student looked away from screen for 8 seconds"
}
```

| Field | Type | Description |
|---|---|---|
| `evidenceUrl` | `string` | Bunny CDN URL of the evidence file (`.mp4` video or `.mp3` audio) |
| `timestamp` | `DateTime` (ISO 8601 UTC) | Exact moment the violation occurred during the attempt |
| `description` | `string` | Human-readable (or AI-generated) description of the incident |

**Success response — `200 OK`**

```json
{
  "id": 7,
  "evidenceUrl": "https://cdn.bunny.net/proctoring/attempt-45/clip-001.mp4",
  "timestamp": "2026-05-07T10:23:11Z",
  "description": "Student looked away from screen for 8 seconds"
}
```

> **Tip:** Call this endpoint once per detected event. Do not batch multiple events into one call; each violation gets its own record and evidence URL.

---

### 3. Get Cheating Report by Attempt

**Triggered when:** an instructor or the proctoring dashboard wants to review the full report for a specific quiz attempt.

```
GET /api/CheatingReport/attempt/{attemptId}
```

**Permission required:** `CheatingReport:read`

**Path parameter:**

| Name | Type | Description |
|---|---|---|
| `attemptId` | `int` | ID of the quiz attempt |

**Success response — `200 OK`**

```json
{
  "id": 12,
  "quizAttemptId": 45,
  "studentId": "auth0|abc123",
  "studentName": "Ali Hassan",
  "violations": [
    {
      "id": 7,
      "evidenceUrl": "https://cdn.bunny.net/proctoring/attempt-45/clip-001.mp4",
      "timestamp": "2026-05-07T10:23:11Z",
      "description": "Student looked away from screen for 8 seconds"
    },
    {
      "id": 8,
      "evidenceUrl": "https://cdn.bunny.net/proctoring/attempt-45/clip-002.mp4",
      "timestamp": "2026-05-07T10:31:45Z",
      "description": "Phone detected in frame"
    }
  ]
}
```

**Error — `404 Not Found`** when no report exists for the given attempt.

---

### 4. Get All Cheating Reports for a Quiz

**Triggered when:** an instructor wants an overview of all suspicious attempts across an entire quiz.

```
GET /api/CheatingReport/quiz/{quizId}
```

**Permission required:** `CheatingReport:read`

**Path parameter:**

| Name | Type | Description |
|---|---|---|
| `quizId` | `int` | ID of the quiz |

**Success response — `200 OK`** — array of `CheatingReportResponse`:

```json
[
  {
    "id": 12,
    "quizAttemptId": 45,
    "studentId": "auth0|abc123",
    "studentName": "Ali Hassan",
    "violations": [ ... ]
  },
  {
    "id": 13,
    "quizAttemptId": 47,
    "studentId": "auth0|xyz789",
    "studentName": "Sara Ahmed",
    "violations": [ ... ]
  }
]
```

Returns an empty array `[]` when no reports exist for the quiz.

---

### 5. Delete a Single Violation

**Triggered when:** a false-positive violation needs to be removed after manual review.

```
DELETE /api/CheatingReport/violations/{violationId}
```

**Permission required:** `CheatingReport:delete`

**Path parameter:**

| Name | Type | Description |
|---|---|---|
| `violationId` | `int` | ID of the violation to remove |

**Success response — `204 No Content`**

**Error — `404 Not Found`** when the violation does not exist.

---

### 6. Delete an Entire Cheating Report

**Triggered when:** a full report must be dismissed (e.g., confirmed false alarm, or the quiz attempt was voided).

```
DELETE /api/CheatingReport/{reportId}
```

**Permission required:** `CheatingReport:delete`

**Path parameter:**

| Name | Type | Description |
|---|---|---|
| `reportId` | `int` | ID of the cheating report to delete |

**Success response — `204 No Content`**

> **Note:** Deleting a report cascades and removes all its violations as well (enforced at database level).

---

## AI Proctoring — Recommended Workflow

```
Student starts quiz attempt
        │
        ▼
POST /api/CheatingReport/attempt/{attemptId}
  → store returned reportId locally
        │
        ▼
┌───────────────────────────────────┐
│  AI model runs during the attempt │
│                                   │
│  On each detected event:          │
│  1. Upload clip to Bunny CDN      │
│  2. POST .../violations           │
│     with evidenceUrl + timestamp  │
│     + AI-generated description    │
└───────────────────────────────────┘
        │
        ▼
Attempt ends
        │
        ▼
(Optional) GET /api/CheatingReport/attempt/{attemptId}
  → send summary notification to instructor
```

### Key rules

1. **Always create the report first** before logging violations. The `reportId` returned by step 1 is required for all subsequent `AddViolation` calls.
2. **Upload evidence to Bunny CDN before calling the API.** The endpoint only stores the CDN URL, not the file itself.
3. **One violation per event.** Never merge multiple incidents into one record.
4. **Use UTC timestamps** in ISO 8601 format (`2026-05-07T10:23:11Z`).
5. **Handle idempotency:** if the proctoring agent restarts mid-attempt, calling `POST .../attempt/{attemptId}` again is safe — it returns the existing report without creating a duplicate.

---

## Error Reference

| HTTP Status | Meaning |
|---|---|
| `400 Bad Request` | Invalid request body or missing required fields |
| `401 Unauthorized` | Missing or invalid JWT token |
| `403 Forbidden` | Token is valid but the user lacks the required permission policy |
| `404 Not Found` | The requested report, attempt, or violation does not exist |
| `204 No Content` | Successful delete |
| `201 Created` | Report created successfully |
| `200 OK` | Successful read or violation added |
