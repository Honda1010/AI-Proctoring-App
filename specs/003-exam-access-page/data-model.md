# Data Model: Exam Access Page

**Branch**: `003-exam-access-page` | **Date**: 2026-04-15  
**Input**: entities from `spec.md` + research decisions in `research.md`

---

## Entities

### 1. ExamCodeRequest

The exam code submitted by the student from the renderer to main.js via IPC, then enriched with the access token and forwarded to the Python bridge.

| Field      | Type     | Constraints                                                        |
|------------|----------|--------------------------------------------------------------------|
| `quizCode` | `string` | Non-empty after trimming; whitespace trimmed before validation     |

**Validation layers**:
- Layer 1 (renderer, pre-IPC): non-empty check only (codes are instructor-defined, no format constraint). Shows inline error if blank.
- Layer 2 (Python bridge, pre-LMS): non-empty check; returns `BRIDGE_ERROR` if blank.
- Layer 3 (LMS): authoritative code validation; 404 if not found, 409 if already attempted.

**Token enrichment** (main.js only, never renderer):  
Before forwarding to the bridge, main.js appends `{ "token": accessToken }` to the request body. The token is read from `sessionMemory` (not-remembered sessions) or keytar (`access-token` key, remembered sessions).

---

### 2. ExamSession

The exam data returned by the LMS `GET /api/QuizAttempts/attempt/{quizCode}` and relayed via the bridge and IPC to main.js. Stored in main.js module scope as `examSession`. Retrieved by the Exam page via `bridge:get-exam-session`.

| Field       | Type      | Notes                                                                      |
|-------------|-----------|----------------------------------------------------------------------------|
| `attemptId` | `number`  | Server-generated integer. Required for answer submission (spec 004).       |
| `title`     | `string`  | Exam title. Displayed on the Exam page header.                             |
| `duration`  | `string`  | `HH:mm:ss` format. Drives the countdown timer on the Exam page.            |
| `questions` | `array`   | Array of `QuestionItem`. See below.                                        |

**QuestionItem** (nested inside `ExamSession.questions`):

| Field         | Type     | Notes                                                                  |
|---------------|----------|------------------------------------------------------------------------|
| `questionText`| `string` | The question text to display.                                          |
| `choices`     | `array`  | Array of `ChoiceItem`. See below.                                      |
| `id` *(expected)* | `number` | Hidden server-side ID required for answer submission (spec 004). Expected in live response despite being absent from public API docs (research.md Decision 5). |

**ChoiceItem** (nested inside `QuestionItem.choices`):

| Field        | Type     | Notes                                                                   |
|--------------|----------|-------------------------------------------------------------------------|
| `choiceText` | `string` | The choice label to display.                                            |
| `id` *(expected)* | `number` | Hidden server-side ID required for answer submission (spec 004). Same caveat as above. |

**Lifecycle**:
```
Successful exam-start → store in module-scope examSession
Exam page loads       → bridge:get-exam-session returns examSession
Exam submitted/done   → examSession = null (cleared by spec 004 logic)
App quit              → examSession lost (in-memory only, not persisted)
```

---

### 3. BridgeExamError

Typed error returned by the Python bridge when the exam-start call fails. Sanitised — no raw LMS error text forwarded.

| Field     | Type     | Allowed values                                                       |
|-----------|----------|----------------------------------------------------------------------|
| `code`    | `string` | `EXAM_NOT_FOUND`, `ALREADY_ATTEMPTED`, `UNAUTHORIZED`, `BRIDGE_ERROR` |
| `message` | `string` | Safe, sanitised display string (no student IDs, no LMS internals)    |

**Static message map** — renderer displays these exact strings:

| `code`             | Display message                                                              |
|--------------------|------------------------------------------------------------------------------|
| `EXAM_NOT_FOUND`   | "Exam code not found. Please check the code and try again."                  |
| `ALREADY_ATTEMPTED`| "You have already attempted this exam."                                      |
| `UNAUTHORIZED`     | *(never shown to renderer — main.js catches 401 and redirects to Login)*     |
| `BRIDGE_ERROR`     | "Unable to reach the server. Please check your connection and try again."    |

---

### 4. IPC Channel Contracts

#### `bridge:start-exam` (ipcMain.handle)

- **Direction**: renderer → main → bridge → LMS → bridge → main → renderer  
- **Input** (from renderer): `{ quizCode: string }`  
- **Enrichment** (main.js only): reads `accessToken` from `sessionMemory` or keytar; adds to bridge request  
- **Output (success)**: `{ ok: true, data: ExamSession }`  
- **Output (failure)**: `{ ok: false, error: BridgeExamError }`  
- **Special case**: if `error.code === 'UNAUTHORIZED'`, main.js clears the session and routes to Login; the IPC call never returns `{ ok: false }` to the renderer in this case  

#### `bridge:get-exam-session` (ipcMain.handle)

- **Direction**: renderer (Exam page) → main  
- **Input**: none  
- **Output (success)**: `{ ok: true, session: ExamSession }`  
- **Output (no session)**: `{ ok: false }`  

---

### 5. Python Bridge Endpoint: `POST /exam-access`

- **Route**: `POST /exam-access`  
- **Request body** (from main.js): `{ "quizCode": "...", "token": "<JWT>" }`  
- **LMS call**: `GET {BASE_URL}/api/QuizAttempts/attempt/{quizCode}` with `Authorization: Bearer {token}`  
- **Success (200)**: relay full LMS response body as-is  
- **LMS 404**: return `{ "code": "EXAM_NOT_FOUND", "message": "..." }` with HTTP 404  
- **LMS 409**: return `{ "code": "ALREADY_ATTEMPTED", "message": "..." }` with HTTP 409  
- **LMS 401**: return `{ "code": "UNAUTHORIZED", "message": "..." }` with HTTP 401  
- **Network failure**: return `{ "code": "BRIDGE_ERROR", "message": "..." }` with HTTP 503  

**Security**:
- The `token` value is never logged, never echoed in any response, and used only for the outbound Authorization header.
- `quizCode` is validated as non-empty; no other format validation at bridge level.

---

### 6. DesignToken additions (Phase 1 check)

No new tokens required. The full design maps to existing `design-tokens.css` properties. (Confirmed by research.md Decision 6.)
