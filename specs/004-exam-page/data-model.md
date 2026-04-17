# Data Model: Exam Page

**Branch**: `004-exam-page` | **Date**: 2026-04-16  
**Input**: entities from `spec.md` + research decisions in `research.md`

---

## Entities

### 1. ExamSession *(read-only in this spec)*

Retrieved from main.js module scope via `bridge:get-exam-session` on page load. Written by spec 003 (`bridge:start-exam`). This spec does not modify it.

| Field       | Type      | Notes                                                              |
|-------------|-----------|--------------------------------------------------------------------|
| `attemptId` | `number`  | LMS-generated integer. Required as path param in submit URL.       |
| `title`     | `string`  | Exam title. Displayed in the fixed header.                         |
| `duration`  | `string`  | `HH:mm:ss` format. Used to initialise the countdown timer.        |
| `questions` | `array`   | Array of `QuestionItem`. See below.                               |

**QuestionItem** (nested inside `ExamSession.questions`):

| Field         | Type     | Notes                                                              |
|---------------|----------|--------------------------------------------------------------------|
| `id`          | `number` | Hidden server-side ID. Required as `questionId` in submit payload. |
| `questionText`| `string` | Question text to display.                                          |
| `choices`     | `array`  | Array of `ChoiceItem`. See below.                                  |

**ChoiceItem** (nested inside `QuestionItem.choices`):

| Field        | Type     | Notes                                                              |
|--------------|----------|--------------------------------------------------------------------|
| `id`         | `number` | Hidden server-side ID. Required as `choiceId` in submit payload.  |
| `choiceText` | `string` | Choice label to display.                                           |

**Lifecycle**:
```
Spec 003 bridge:start-exam success → examSession = { ... } (main.js)
Exam page loads                    → bridge:get-exam-session → renderer reads examSession
Submission success                 → examSession = null (main.js, spec 004 logic)
App quit                           → examSession lost (in-memory only)
```

---

### 2. AnswerMap *(renderer-scope, in-memory)*

Plain JavaScript object in `exam.js` module scope. Maps question IDs to the student's selected choice IDs. Never persisted. Drives the submit payload and navigator pill "answered" state.

```
const answerMap = {};          // { [questionId: number]: choiceId: number }
// Example after selecting answers:
// { 101: 205, 102: 210, 103: 209 }
```

**Operations**:
- `answerMap[question.id] = choice.id` — record a selection (overwrites any previous)
- `delete answerMap[question.id]` — remove a selection (not used in the UI; documented for completeness)
- `question.id in answerMap` — check if a question has been answered
- `Object.entries(answerMap).map(([qId, cId]) => ({ questionId: +qId, choiceId: cId }))` — build submit payload

**Validation rules**:
- No format validation on values — IDs are whatever the LMS returned. If the LMS returns non-numeric IDs, the submit will fail at bridge level with `BRIDGE_ERROR`.
- Empty `answerMap` (zero answered questions) is valid — results in `answers: []` payload sent to LMS.

---

### 3. FlagSet *(renderer-scope, in-memory)*

`Set<number>` in `exam.js` module scope. Tracks question IDs the student has flagged for review. Never persisted, never submitted.

```
const flagSet = new Set();
// Toggling:
flagSet.has(id) ? flagSet.delete(id) : flagSet.add(id);
```

**Priority rule**: If a question is both answered and flagged, the navigator pill shows the "flagged" style, not the "answered" style.

---

### 4. SubmitRequest

Assembled by main.js immediately before calling the Python bridge. The `answers` array comes from `AnswerMap`, the `attemptId` from `examSession`, and the `token` from `sessionMemory` or keytar.

| Field       | Type                              | Notes                                                        |
|-------------|-----------------------------------|--------------------------------------------------------------|
| `attemptId` | `number`                          | LMS attempt ID from `examSession`. Used as URL path param on the LMS side; included in body for the bridge route. |
| `answers`   | `Array<{questionId, choiceId}>`   | All answered questions. Empty array is valid.                |
| `token`     | `string`                          | JWT access token. Never logged, never echoed in responses.   |

**Bridge HTTP body** (sent by main.js to `POST /submit-exam`):
```json
{
  "attemptId": 42,
  "answers": [
    { "questionId": 101, "choiceId": 205 },
    { "questionId": 102, "choiceId": 210 }
  ],
  "token": "<JWT — stripped by bridge before any response>"
}
```

---

### 5. SubmitResult

The graded result returned by the LMS `POST /api/QuizAttempts/submit/{attemptId}` and relayed via the bridge and IPC to main.js. Stored as `submitResult` in main.js module scope. Retrieved by the result page (spec 005) via `bridge:get-submit-result`.

| Field            | Type      | Notes                                                       |
|------------------|-----------|-------------------------------------------------------------|
| `quizCode`       | `string`  | The exam code used (echoed by LMS).                         |
| `quizTitle`      | `string`  | Exam title. Can be displayed on result page.                |
| `score`          | `number`  | Number of correct answers.                                  |
| `totalQuestions` | `number`  | Total number of questions in the exam.                      |
| `percentage`     | `number`  | `(score / totalQuestions) * 100` — a floating-point value.  |
| `questions`      | `array`   | Array of `SubmitResultItem`. See below.                     |

**SubmitResultItem** (nested inside `SubmitResult.questions`):

| Field           | Type      | Notes                                                            |
|-----------------|-----------|------------------------------------------------------------------|
| `questionText`  | `string`  | The question text (for review on the result page).              |
| `studentChoice` | `string`  | The text of the student's selected choice.                       |
| `correctChoice` | `string`  | The text of the correct answer.                                  |
| `isCorrect`     | `boolean` | Whether the student's choice was correct.                        |

**Lifecycle**:
```
Submission success     → submitResult = { ... } (main.js)
                       → examSession = null (main.js — exam is over)
Result page loads      → bridge:get-submit-result → renderer reads submitResult
Result page displayed  → (submitResult left in place for session lifetime)
App quit               → submitResult lost (in-memory only)
```

---

### 6. BridgeSubmitError

Typed error returned by the Python bridge when the submit call fails. Sanitised — no raw LMS error text forwarded.

| Field     | Type     | Allowed values                                                    |
|-----------|----------|-------------------------------------------------------------------|
| `code`    | `string` | `EXAM_NOT_FOUND`, `UNAUTHORIZED`, `BRIDGE_ERROR`                  |
| `message` | `string` | Safe, sanitised display string                                    |

**Static message map** — renderer displays these exact strings:

| `code`           | Display message                                                                   |
|------------------|-----------------------------------------------------------------------------------|
| `EXAM_NOT_FOUND` | "This exam could not be found. Please contact your instructor."                   |
| `UNAUTHORIZED`   | *(never shown — main.js catches 401 and redirects to Login silently)*            |
| `BRIDGE_ERROR`   | "Unable to reach the server. Please check your connection and try again."         |

> Note: `ALREADY_ATTEMPTED` is not a valid submit error — an attempt record already exists for this `attemptId` by definition. If the LMS returns 409 on submit, it is mapped to `BRIDGE_ERROR`.

---

### 7. IPC Channel Contracts

#### `bridge:get-exam-session` *(existing from spec 003, read-only in spec 004)*

- **Direction**: renderer → main  
- **Input**: none  
- **Output (success)**: `{ ok: true, session: ExamSession }`  
- **Output (no session)**: `{ ok: false }`  
- **Renderer action on `{ ok: false }`**: redirect to Login page immediately  

#### `bridge:submit-exam` *(NEW in spec 004)*

- **Direction**: renderer → main → bridge → LMS → bridge → main → renderer  
- **Input** (from renderer): `{ answers: Array<{questionId: number, choiceId: number}> }`  
- **Enrichment** (main.js only): reads `accessToken` from `sessionMemory?.accessToken` or keytar; reads `attemptId` from `examSession.attemptId`; builds full `SubmitRequest`  
- **Output (success)**: `{ ok: true, data: SubmitResult }`  
- **Output (UNAUTHORIZED)**: main.js clears session and loads Login page; IPC call never resolves to renderer  
- **Output (failure)**: `{ ok: false, error: BridgeSubmitError }`  

#### `bridge:get-submit-result` *(NEW in spec 004)*

- **Direction**: renderer (result page, spec 005) → main  
- **Input**: none  
- **Output (success)**: `{ ok: true, result: SubmitResult }`  
- **Output (no result)**: `{ ok: false }`  

#### `bridge:clear-session` *(existing from spec 002, used in spec 004 for 401 redirect)*

- **Direction**: main.js calls internally (not from renderer in this spec)  
- Used when `bridge:submit-exam` returns `UNAUTHORIZED`: main.js calls `clearAllKeytarEntries()` directly, then loads Login page

---

### 8. Python Bridge Endpoint: `POST /submit-exam` *(NEW in spec 004)*

- **Route**: `POST /submit-exam` (added to existing `exam_bp` Blueprint in `python_bridge/exam.py`)  
- **Request body** (from main.js):  
  ```json
  { "attemptId": 42, "answers": [{"questionId": 101, "choiceId": 205}], "token": "<JWT>" }
  ```
- **LMS call**: `POST {BASE_URL}/api/QuizAttempts/submit/{attemptId}` with `Authorization: Bearer {token}` and body `{ "answers": [...] }`  
- **Success (200)**: relay full LMS response body as-is → `SubmitResult`  
- **LMS 401**: return `{ "code": "UNAUTHORIZED", "message": "..." }` with HTTP 401  
- **LMS 404**: return `{ "code": "EXAM_NOT_FOUND", "message": "..." }` with HTTP 404  
- **Any other LMS error / network failure**: return `{ "code": "BRIDGE_ERROR", "message": "..." }` with HTTP 503  

**Security**:
- The `token` value is never logged, never echoed in any response, and used only for the outbound `Authorization` header.
- `attemptId` is validated as a positive integer; non-integer values return HTTP 400 `BRIDGE_ERROR`.
- `answers` is passed as-is to the LMS; no validation of individual `questionId`/`choiceId` values at bridge level (LMS is authoritative).

---

### 9. DesignToken additions (Phase 1 check)

No new tokens required. All visual elements map to existing `design-tokens.css` properties. (Confirmed by research.md Decision 8.) The Submit Exam button uses `linear-gradient(135deg, var(--color-error), var(--color-tertiary))` — both tokens already exist.
