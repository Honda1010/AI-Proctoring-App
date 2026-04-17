# Data Model: Result Page

**Branch**: `005-result-page` | **Date**: 2026-04-17  
**Input**: entities from `spec.md` + research decisions in `research.md`

---

## Entities

### 1. SubmitResult *(in-memory, main.js module scope)*

Written once by `bridge:submit-exam` on successful exam submission (spec 004). Read by the Result page via `bridge:get-submit-result`. Cleared by `bridge:clear-submit-result` when the student clicks "Back to Home".

| Field            | Type              | Source              | Notes                                                                 |
|------------------|-------------------|---------------------|-----------------------------------------------------------------------|
| `quizCode`       | `string`          | LMS response        | Exam code (e.g., `"EXAM2026"`). Shown in score summary.              |
| `quizTitle`      | `string`          | LMS response        | Exam title. Shown in score summary header.                            |
| `score`          | `number` (int)    | LMS response        | Number of questions answered correctly.                               |
| `totalQuestions` | `number` (int)    | LMS response        | Total questions in the exam. Used in "7 / 10" display.               |
| `percentage`     | `number` (double) | LMS response        | `(score / totalQuestions) * 100`. Compared to `PASS_THRESHOLD = 50`. |
| `questions`      | `QuestionResult[]`| LMS response        | Per-question review items. May be empty array — see FR-008.          |

**Lifecycle**:
```
Spec 004 bridge:submit-exam success  →  submitResult = { ...body }   (main.js)
Result page DOMContentLoaded         →  bridge:get-submit-result      →  { ok: true, data: submitResult }
Recovery path (FR-004)               →  bridge:get-result             →  submitResult = fetched body → { ok: true, data }
Back to Home clicked                 →  bridge:clear-submit-result    →  submitResult = null, examSession = null
App quit                             →  submitResult = null (in-memory only)
```

**Validation**: Shape is trusted to come from the LMS. No frontend re-validation beyond presence checks.

---

### 2. QuestionResult *(nested in SubmitResult.questions)*

| Field            | Type     | Notes                                                                   |
|------------------|----------|-------------------------------------------------------------------------|
| `questionText`   | `string` | Full text of the question.                                              |
| `studentChoice`  | `string` | The answer text the student selected. May differ from `correctChoice`. |
| `correctChoice`  | `string` | The answer text that is correct.                                        |
| `isCorrect`      | `boolean`| `true` if `studentChoice === correctChoice`. Drives indicator style.   |

**Display rule**: If `isCorrect === true` → render a "Correct" indicator in the positive accent colour token. If `isCorrect === false` → render an "Incorrect" indicator in the destructive colour token.

---

### 3. ExamSession *(read-only in this spec — used for recovery `attemptId` only)*

The `examSession` object is written by spec 003 and carried forward through spec 004 submission **without being nulled** (research.md Decision 2). This spec reads only `examSession.attemptId` in the recovery path and clears the entire object on Back to Home.

| Field       | Type     | Notes                                                                       |
|-------------|----------|-----------------------------------------------------------------------------|
| `attemptId` | `number` | LMS attempt ID. Used as path param in `GET /api/QuizAttempts/result/{id}`. |

Only `attemptId` is consumed by this spec. All other `examSession` fields are irrelevant to the Result page.

**Lifecycle change from spec 004** (research.md Decision 2):
```
Before this spec:  bridge:submit-exam success → examSession = null
After this spec:   bridge:submit-exam success → examSession unchanged (null set only on Back to Home)
```

---

### 4. PassThreshold *(compile-time constant, result.js)*

| Name              | Value  | Type     | Location       |
|-------------------|--------|----------|----------------|
| `PASS_THRESHOLD`  | `50`   | `number` | `result.js:1`  |

Pass condition: `submitResult.percentage >= PASS_THRESHOLD`  
Fail condition: `submitResult.percentage < PASS_THRESHOLD`  
Threshold comparison is inclusive — exactly 50% is treated as "Passed".

---

## State Transitions

```
[App Start]
     │
     ▼
[Login Page] ──login success──▶ [Exam Code Page] ──start-exam success──▶ [Exam Page]
                                                                               │
                                                              submit or timeout │
                                                                               ▼
                                                                      [Result Page]
                                                                       │        │
                                                             submitResult    no submitResult
                                                              present        + attemptId present
                                                                │                 │
                                                           render            GET /result/{id}
                                                           result               ▼
                                                                │          render result
                                                                │               │
                                                      ◄─────Back to Home────────┘
                                                                │
                                                      clear submitResult + examSession
                                                                │
                                                       [Exam Code Page]

[No submitResult + no attemptId] ──▶ redirect to [Login Page]
```
