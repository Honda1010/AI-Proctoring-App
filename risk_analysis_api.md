# Risk Analysis API — Integration Guide
> **Audience:** AI Proctoring Desktop Application Team  
> **Version:** 1.0 · **Last updated:** 2026-05-13

---

## Overview

After a student finishes an exam, the desktop app sends one violation report per attempt to this endpoint. The backend immediately acknowledges receipt (`202 Accepted`) and processes the risk score **asynchronously** in a background job. The final score is stored on the `CheatingReport` entity and is visible to instructors through the LMS dashboard.

```
Desktop App  ──POST──▶  /api/risk-analysis  ──▶  202 Accepted
                                                      │
                                               [Hangfire Job]
                                                      │
                                          Cohort min-max normalization
                                          + weight application
                                                      │
                                          CheatingReport.RiskScore ← saved
```

---

## Endpoint

| Property | Value |
|---|---|
| **Method** | `POST` |
| **URL** | `{BASE_URL}/api/risk-analysis` |
| **Content-Type** | `application/json` |
| **Authentication** | None required (internal service call) |
| **Expected Response** | `202 Accepted` |

> **Development base URL:** `https://localhost:{port}`  
> **Production base URL:** Provided by the backend team at deployment.

---

## Prerequisites

Before calling this endpoint, a `CheatingReport` must already exist for the given `Attempt_Id`. It is created automatically by the LMS when the student starts the exam. If no report exists, the API returns `404 Not Found`.

---

## Request Body

Send a JSON object with the following structure.

### Full Schema

```json
{
  "report_metadata": {
    "generated_at": "string (ISO 8601 datetime with timezone)",
    "student_id":   "string (UUID of the student)",
    "Attempt_Id":   "string (integer ID of the quiz attempt)",
    "mode":         "string (e.g. 'per_question')",
    "normalisation":"string (e.g. 'pending — apply min-max across exam cohort')"
  },
  "session_summary": {
    "total_questions":    "integer",
    "questions_violated": "integer",
    "questions_clean":    "integer",
    "violation_rate":     "float  (0.0 – 1.0)",
    "weights_used": {
      "face_absence_mismatch": "float",
      "suspicious_movement":   "float",
      "conversation_noise":    "float",
      "forbidden_objects":     "float"
    }
  },
  "questions": [
    {
      "question_id":      "integer",
      "face_detection":   "integer (0 or 1)",
      "face_recognition": "integer (0 or 1)",
      "eye_gaze":         "integer (0 or 1)",
      "speech_detection": "integer (0 or 1)",
      "object_detection": "integer (0 or 1)",
      "violation_total":  "integer"
    }
  ]
}
```

### Field Reference

#### `report_metadata`

| Field | Type | Required | Description |
|---|---|---|---|
| `generated_at` | ISO 8601 string | ✅ | Timestamp when the report was generated on the desktop |
| `student_id` | UUID string | ✅ | The student's unique identifier from the LMS |
| `Attempt_Id` | string (integer) | ✅ | **Must match an existing `QuizAttempt` ID in the LMS database** |
| `mode` | string | ✅ | Processing mode — use `"per_question"` |
| `normalisation` | string | ✅ | Descriptor — use `"pending — apply min-max across exam cohort"` |

> [!IMPORTANT]
> `Attempt_Id` must be sent as a **string** but must contain a **valid integer** (e.g. `"2077"`). The backend parses it to `int` and validates it against the database.

#### `session_summary`

| Field | Type | Required | Description |
|---|---|---|---|
| `total_questions` | int | ✅ | Total questions in the exam |
| `questions_violated` | int | ✅ | Count of questions with at least one violation |
| `questions_clean` | int | ✅ | Count of questions with zero violations |
| `violation_rate` | float | ✅ | `questions_violated / total_questions` — stored as-is on the report |
| `weights_used` | object | ✅ | See below |

#### `session_summary.weights_used`

The weight for each violation category. The backend applies these to normalize violation counts. Default for all fields is `1.0`.

| Field | Maps To Violation Columns | Typical Value |
|---|---|---|
| `face_absence_mismatch` | `face_detection` + `face_recognition` | `1.0` |
| `suspicious_movement` | `eye_gaze` | `1.0` |
| `conversation_noise` | `speech_detection` | `1.0` |
| `forbidden_objects` | `object_detection` | `1.0` |

#### `questions[]` — Per-Question Entry

Each object represents one question answered during the exam.

| Field | Type | Required | Description |
|---|---|---|---|
| `question_id` | int | ✅ | The LMS question ID (must be the **real** ID from the quiz, not an index) |
| `face_detection` | int | ✅ | `1` if no face was detected during this question, otherwise `0` |
| `face_recognition` | int | ✅ | `1` if the face did not match the registered student, otherwise `0` |
| `eye_gaze` | int | ✅ | `1` if suspicious eye movement was detected, otherwise `0` |
| `speech_detection` | int | ✅ | `1` if conversation noise was detected, otherwise `0` |
| `object_detection` | int | ✅ | `1` if a forbidden object was detected, otherwise `0` |
| `violation_total` | int | ✅ | Sum of all flags for this question |

---

## Complete Example Request

```json
{
  "report_metadata": {
    "generated_at": "2026-05-12T23:01:28.446104+00:00",
    "student_id": "b9f61814-ca5a-4e7b-855c-35d5d4e36d9c",
    "Attempt_Id": "2077",
    "mode": "per_question",
    "normalisation": "pending — apply min-max across exam cohort"
  },
  "session_summary": {
    "total_questions": 19,
    "questions_violated": 4,
    "questions_clean": 15,
    "violation_rate": 0.210526,
    "weights_used": {
      "face_absence_mismatch": 1.0,
      "suspicious_movement": 1.0,
      "conversation_noise": 1.0,
      "forbidden_objects": 1.0
    }
  },
  "questions": [
    { "question_id": 3,  "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 4,  "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 5,  "face_detection": 0, "face_recognition": 0, "eye_gaze": 1, "speech_detection": 0, "object_detection": 1, "violation_total": 2 },
    { "question_id": 6,  "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 1, "violation_total": 1 },
    { "question_id": 7,  "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 8,  "face_detection": 0, "face_recognition": 0, "eye_gaze": 1, "speech_detection": 0, "object_detection": 0, "violation_total": 1 },
    { "question_id": 9,  "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 10, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 11, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 12, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 13, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 14, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 15, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 16, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 17, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 18, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 19, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 20, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 0, "violation_total": 0 },
    { "question_id": 21, "face_detection": 0, "face_recognition": 0, "eye_gaze": 0, "speech_detection": 0, "object_detection": 1, "violation_total": 1 }
  ]
}
```

---

## Responses

### `202 Accepted` — Report Received, Job Enqueued

The report was valid and the background calculation has started. The body is a lightweight acknowledgement.

```json
{
  "studentId":               "b9f61814-ca5a-4e7b-855c-35d5d4e36d9c",
  "attemptId":               "2077",
  "originalViolationRate":   0.210526,
  "questionsRisk":           [],
  "overallSessionRiskScore": 0.0
}
```

> [!NOTE]
> `questionsRisk` is empty and `overallSessionRiskScore` is `0` in the immediate response — this is expected. The actual values are computed in the background job and saved to the `CheatingReport`. The desktop app does **not** need to poll for results.

### `400 Bad Request` — Invalid `Attempt_Id`

Returned when `Attempt_Id` cannot be parsed as an integer.

```json
{
  "status": 400,
  "message": "Attempt_Id 'abc' must be a valid integer."
}
```

### `404 Not Found` — No CheatingReport for Attempt

Returned when `Attempt_Id` is valid but no `CheatingReport` exists for it in the LMS database.

```json
{
  "status": 404,
  "message": "No CheatingReport found for QuizAttempt 2077. Create one first via POST /api/cheating-reports."
}
```

> [!WARNING]
> If you receive a `404`, it means the student's attempt was never registered in the LMS, or the exam session was not properly initialized. Contact the backend team before retrying.

---

## Background Job — What Happens After 202

The desktop app does not need to do anything further. The backend job runs these steps automatically:

```
1. Persist raw violation counts
   └── One row per (Attempt_Id x question_id) in the RiskAnalyses table

2. Cohort aggregation per question_id
   └── Query MIN and MAX for each violation column across ALL students
       who answered the same question_id

3. Min-Max normalization per violation type
   └── Normalized = (student_count - min) / (max - min)
   └── If max == min  →  Normalized = 0.0  (avoids division by zero)

4. Weight application
   |-- face_detection   x face_absence_mismatch weight
   |-- face_recognition x face_absence_mismatch weight
   |-- eye_gaze         x suspicious_movement weight
   |-- speech_detection x conversation_noise weight
   +-- object_detection x forbidden_objects weight

5. Sum  →  student_risk_score per question

6. Cohort average risk score per question (benchmark)

7. overall_session_risk_score = avg(all question student_risk_scores)

8. CheatingReport.RiskScore  ←  overall_session_risk_score  (saved to DB)
```

---

## Code Samples

### Python (`requests`)

```python
import requests
from datetime import datetime, timezone

BASE_URL = "https://your-api-host.com"

def build_question(qid, fd=0, fr=0, eg=0, sd=0, od=0):
    return {
        "question_id": qid,
        "face_detection": fd,
        "face_recognition": fr,
        "eye_gaze": eg,
        "speech_detection": sd,
        "object_detection": od,
        "violation_total": fd + fr + eg + sd + od
    }

payload = {
    "report_metadata": {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "student_id":   "b9f61814-ca5a-4e7b-855c-35d5d4e36d9c",
        "Attempt_Id":   "2077",               # must be a string containing an integer
        "mode":         "per_question",
        "normalisation": "pending — apply min-max across exam cohort"
    },
    "session_summary": {
        "total_questions":    19,
        "questions_violated": 4,
        "questions_clean":    15,
        "violation_rate":     0.210526,
        "weights_used": {
            "face_absence_mismatch": 1.0,
            "suspicious_movement":   1.0,
            "conversation_noise":    1.0,
            "forbidden_objects":     1.0
        }
    },
    "questions": [
        build_question(3),
        build_question(5, eg=1, od=1),   # violated
        build_question(6, od=1),          # violated
        # ... rest of questions
    ]
}

response = requests.post(
    f"{BASE_URL}/api/risk-analysis",
    json=payload,
    headers={"Content-Type": "application/json"},
    timeout=10
)

if response.status_code == 202:
    print("Report accepted:", response.json())
elif response.status_code == 404:
    print("CheatingReport not found — was the quiz started through the LMS?")
elif response.status_code == 400:
    print("Bad request:", response.json())
else:
    print(f"Unexpected status: {response.status_code}")
```

### C# (`HttpClient`)

```csharp
using System.Net.Http.Json;

var client = new HttpClient { BaseAddress = new Uri("https://your-api-host.com") };

var payload = new
{
    report_metadata = new
    {
        generated_at  = DateTimeOffset.UtcNow,
        student_id    = "b9f61814-ca5a-4e7b-855c-35d5d4e36d9c",
        Attempt_Id    = "2077",          // string, not int
        mode          = "per_question",
        normalisation = "pending — apply min-max across exam cohort"
    },
    session_summary = new
    {
        total_questions    = 19,
        questions_violated = 4,
        questions_clean    = 15,
        violation_rate     = 0.210526,
        weights_used = new
        {
            face_absence_mismatch = 1.0,
            suspicious_movement   = 1.0,
            conversation_noise    = 1.0,
            forbidden_objects     = 1.0
        }
    },
    questions = new[]
    {
        new { question_id = 3,  face_detection = 0, face_recognition = 0, eye_gaze = 0, speech_detection = 0, object_detection = 0, violation_total = 0 },
        new { question_id = 5,  face_detection = 0, face_recognition = 0, eye_gaze = 1, speech_detection = 0, object_detection = 1, violation_total = 2 },
        // ... rest of questions
    }
};

var response = await client.PostAsJsonAsync("/api/risk-analysis", payload);

switch ((int)response.StatusCode)
{
    case 202: Console.WriteLine("Report accepted."); break;
    case 400: Console.WriteLine("Bad request — check Attempt_Id format."); break;
    case 404: Console.WriteLine("No CheatingReport for this attempt."); break;
    default:  Console.WriteLine($"Error: {response.StatusCode}"); break;
}
```

---

## Timing & Retry Guidelines

| Scenario | Recommendation |
|---|---|
| When to call | Immediately after the student submits the exam |
| Retry on `202` | Do **not** retry — the job is already running |
| Retry on `5xx` | Retry up to **3 times** with exponential back-off (1 s, 3 s, 9 s) |
| Retry on `404` | Do **not** retry — report the issue to the backend team |
| Retry on `400` | Do **not** retry — fix the payload (`Attempt_Id` must be an integer string) |
| HTTP timeout | Set to **10 seconds** — the endpoint responds in under 1 second |

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `Attempt_Id` sent as JSON number (`2077` not `"2077"`) | `400 Bad Request` | Wrap in quotes: `"Attempt_Id": "2077"` |
| `Attempt_Id` doesn't exist in the LMS | `404 Not Found` | Ensure the student started the quiz through the LMS first |
| Missing `weights_used` object | `400 Bad Request` (model validation) | Always include all 4 weight fields, even when value is `1.0` |
| Sending empty `questions` array | Job runs but score = `0` | Include all questions, even clean ones (all flags = `0`) |
| `question_id` set to local array index (0, 1, 2 ...) | Incorrect cohort grouping | Use the **real LMS question ID** received from the quiz API |

---

## Data Flow Diagram

```
+----------------------------------+
|  AI Proctoring Desktop App       |
|                                  |
|  POST /api/risk-analysis         |
|  Body: {                         |
|    report_metadata,              |
|    session_summary,              |
|    questions[]                   |
|  }                               |
+----------------+-----------------+
                 |
                 | HTTP 202 Accepted  (< 1 second)
                 v
+----------------------------------+
|         Lumina API               |
|                                  |
|  1. Parse + validate Attempt_Id  |
|  2. Find CheatingReport          |
|  3. Enqueue Hangfire Job         |
|  4. Return 202                   |
+----------------+-----------------+
                 |
                 | (async — seconds later)
                 v
+----------------------------------+
|   RiskScoreCalculationJob        |
|                                  |
|  1. Upsert RiskAnalysis rows     |
|  2. Cohort MIN/MAX per question  |
|  3. Min-Max normalize            |
|  4. Apply weights                |
|  5. Compute cohort averages      |
|  6. Update CheatingReport        |
|     .RiskScore                   |
+----------------+-----------------+
                 |
                 v
        +----------------+
        |   SQL Server   |
        |                |
        | RiskAnalyses   |
        | CheatingReports|
        | .RiskScore     |
        +----------------+
```
