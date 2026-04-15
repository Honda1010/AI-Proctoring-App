# Exam AI-Proctoring Desktop App — LMS Endpoint Reference

> This document covers every **LMS API** endpoint the desktop proctoring app needs across its three pages:
> 1. **Login Page** — authenticate the student
> 2. **Exam Code Page** — validate the code and start the attempt
> 3. **Exam Page** — display questions, submit answers, and view results

---

## Table of Contents

1. [Base URL](#1-base-url)
2. [Authentication Header](#2-authentication-header)
3. [Error Envelope](#3-error-envelope)
4. [Page 1 — Login](#4-page-1--login)
5. [Page 2 — Enter Exam Code](#5-page-2--enter-exam-code)
6. [Page 3 — Solve Exam](#6-page-3--solve-exam)
   - [6.1 Submit Answers](#61-submit-answers)
   - [6.2 Get Result](#62-get-result)
7. [Token Refresh](#7-token-refresh)
8. [App Flow Diagram](#8-app-flow-diagram)

---

## 1. Base URL

| Service | Base URL |
|---------|----------|
| **LMS REST API (.NET 8)** | `https://<your-domain>/api` |

> All routes follow the convention `api/[controller]`

---

## 2. Authentication Header

All endpoints marked 🔒 require a JWT Bearer token obtained from the login endpoint.

```
Authorization: Bearer <access_token>
```

---

## 3. Error Envelope

Every error response — regardless of endpoint — returns this exact JSON shape:

```json
{
  "statusCode": 401,
  "errorMessage": "Invalid Email/password"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `statusCode` | `int` | The HTTP status code |
| `errorMessage` | `string` | Human-readable description of the error |

---

## 4. Page 1 — Login

### `POST /api/Authuantication/login`

Authenticates the student and returns a JWT access token plus a refresh token.

**Request Body** `application/json`

```json
{
  "email": "student@example.com",
  "password": "P@ssword123"
}
```

---

### ✅ `200 OK` — Login successful

```json
{
  "id": "a3f1c2d4-0000-0000-0000-000000000000",
  "email": "student@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "profilePictureUrl": "https://cdn.example.com/pics/john.jpg",
  "token": "<JWT access token>",
  "expinresIn": 3600,
  "refreshToken": "<refresh token>",
  "refreshTokenExpiration": "2026-04-21T10:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Student's unique user ID — store this for the session |
| `email` | `string` | Student's email address |
| `firstName` | `string` | Student's first name |
| `lastName` | `string` | Student's last name |
| `profilePictureUrl` | `string?` | CDN URL of the student's profile picture — can be `null` |
| `token` | `string` | JWT — attach as `Authorization: Bearer <token>` on all 🔒 requests |
| `expinresIn` | `int` | Access token lifetime in **seconds** |
| `refreshToken` | `string` | Used to silently obtain a new access token when it expires |
| `refreshTokenExpiration` | `DateTime` | UTC expiry of the refresh token (valid for **14 days**) |

---

### ❌ `401 Unauthorized` — Wrong email or password

```json
{
  "statusCode": 401,
  "errorMessage": "Invalid Email/password"
}
```

---

### ❌ `401 Unauthorized` — Email address not confirmed yet

```json
{
  "statusCode": 401,
  "errorMessage": "student@example.com is not confirmed"
}
```

---

### ❌ `401 Unauthorized` — Account is locked out (too many failed attempts)

```json
{
  "statusCode": 401,
  "errorMessage": "User with Email student@example.com is locked out."
}
```

---

### ❌ `500 Internal Server Error` — Account is administratively disabled

```json
{
  "statusCode": 500,
  "errorMessage": "User with email student@example.com is disabled."
}
```

---

## 5. Page 2 — Enter Exam Code

The student types the quiz code. This single call validates the code, creates the attempt record in the database, starts the server-side timer, and returns all questions.

### `GET /api/QuizAttempts/attempt/{quizCode}` 🔒

**Path Parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `quizCode` | `string` | The unique exam code provided by the instructor |

> ⚠️ **Important:** Call this endpoint **exactly once** per exam session. Every call creates a new attempt record and starts the timer.

---

### ✅ `200 OK` — Valid code, attempt created

```json
{
  "attemptId": 42,
  "title": "Midterm Exam — Introduction to AI",
  "duration": "01:30:00",
  "questions": [
    {
      "questionText": "What is supervised learning?",
      "choices": [
        { "choiceText": "Learning with labelled data" },
        { "choiceText": "Learning without labelled data" },
        { "choiceText": "Reinforcement from an environment" },
        { "choiceText": "None of the above" }
      ]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `attemptId` | `int` | **Save this.** Required for submitting answers and fetching the result |
| `title` | `string` | Exam title to show on the exam page |
| `duration` | `string` (`HH:mm:ss`) | Total allowed time — use this to drive the countdown timer |
| `questions[].questionText` | `string` | The question text |
| `questions[].choices[].choiceText` | `string` | The text of each answer choice |

> ⚠️ Question and choice IDs are intentionally **hidden** in this response to prevent cheating. The backend team must expose them as internal fields for the desktop client to use when submitting answers.

---

### ❌ `401 Unauthorized` — No token or expired token

```json
{
  "statusCode": 401,
  "errorMessage": "Unauthorized. Please provide a valid token."
}
```

---

### ❌ `404 Not Found` — Exam code does not exist

```json
{
  "statusCode": 404,
  "errorMessage": "Quiz with code 'EXAM2026' was not found."
}
```

---

### ❌ `409 Conflict` — Student has already attempted this quiz

```json
{
  "statusCode": 409,
  "errorMessage": "Student with id <studentId> has already attempted quiz with id EXAM2026."
}
```

---

## 6. Page 3 — Solve Exam

### 6.1 Submit Answers

### `POST /api/QuizAttempts/submit/{attemptId}` 🔒

Submits the student's answers. Call this when the student clicks **Submit** or when the countdown timer reaches zero.

**Path Parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `attemptId` | `int` | The `attemptId` returned from the start endpoint |

**Request Body** `application/json`

```json
{
  "answers": [
    {
      "questionId": 101,
      "choiceId": 205
    },
    {
      "questionId": 102,
      "choiceId": 210
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answers[].questionId` | `int` | Server-side ID of the question |
| `answers[].choiceId` | `int` | Server-side ID of the selected choice |

---

### ✅ `200 OK` — Answers accepted and graded

```json
{
  "quizCode": "EXAM2026",
  "quizTitle": "Midterm Exam — Introduction to AI",
  "score": 7,
  "totalQuestions": 10,
  "percentage": 70.0,
  "questions": [
    {
      "questionText": "What is supervised learning?",
      "studentChoice": "Learning with labelled data",
      "correctChoice": "Learning with labelled data",
      "isCorrect": true
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `quizCode` | `string` | The exam code |
| `quizTitle` | `string` | The exam title |
| `score` | `int` | Number of correct answers |
| `totalQuestions` | `int` | Total number of questions in the exam |
| `percentage` | `double` | Score as a percentage — `(score / totalQuestions) * 100` |
| `questions[].questionText` | `string` | The question text |
| `questions[].studentChoice` | `string` | The answer the student selected |
| `questions[].correctChoice` | `string` | The correct answer |
| `questions[].isCorrect` | `bool` | Whether the student's selection was correct |

---

### ❌ `400 Bad Request` — Exam time has already expired

```json
{
  "statusCode": 400,
  "errorMessage": "you exceeded the allowed quiz duration."
}
```

---

### ❌ `400 Bad Request` — A submitted `choiceId` is invalid (≤ 0)

```json
{
  "statusCode": 400,
  "errorMessage": "Selected choice for question with id <questionId> is not found."
}
```

---

### ❌ `401 Unauthorized` — No token or expired token

```json
{
  "statusCode": 401,
  "errorMessage": "Unauthorized. Please provide a valid token."
}
```

---

### ❌ `404 Not Found` — Attempt ID does not belong to this student

```json
{
  "statusCode": 404,
  "errorMessage": "Quiz Attempt Not Found to student with id <studentId>"
}
```

---

### ❌ `404 Not Found` — A submitted `questionId` does not exist in this quiz

```json
{
  "statusCode": 404,
  "errorMessage": "Question with this Id : <questionId> is Not Found"
}
```

---

### ❌ `409 Conflict` — Quiz has already been submitted

```json
{
  "statusCode": 409,
  "errorMessage": "This Quiz has already been submitted for student with ID : <studentId>."
}
```

---

### 6.2 Get Result

Use this if the student navigates away after submitting and needs to view their result again without re-submitting.

### `GET /api/QuizAttempts/result/{attemptId}` 🔒

**Path Parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `attemptId` | `int` | The attempt ID |

---

### ✅ `200 OK` — Result retrieved successfully

Same response shape as the submit endpoint:

```json
{
  "quizCode": "EXAM2026",
  "quizTitle": "Midterm Exam — Introduction to AI",
  "score": 7,
  "totalQuestions": 10,
  "percentage": 70.0,
  "questions": [
    {
      "questionText": "What is supervised learning?",
      "studentChoice": "Learning with labelled data",
      "correctChoice": "Learning with labelled data",
      "isCorrect": true
    }
  ]
}
```

---

### ❌ `400 Bad Request` — Attempt exists but has not been submitted yet

```json
{
  "statusCode": 400,
  "errorMessage": "Student with id <studentId> has not submitted the quiz yet."
}
```

---

### ❌ `400 Bad Request` — Attempt exists, not submitted, and time has expired

```json
{
  "statusCode": 400,
  "errorMessage": "you exceeded the allowed quiz duration."
}
```

---

### ❌ `401 Unauthorized` — No token or expired token

```json
{
  "statusCode": 401,
  "errorMessage": "Unauthorized. Please provide a valid token."
}
```

---

### ❌ `404 Not Found` — Attempt ID does not belong to this student

```json
{
  "statusCode": 404,
  "errorMessage": "Quiz Attempt Not Found to student with id <studentId>"
}
```

---

## 7. Token Refresh

When the JWT access token expires, silently exchange it for a new pair using the refresh token.

### `POST /api/Authuantication/refresh`

**Request Body** `application/json`

```json
{
  "token": "<expired JWT access token>",
  "refreshToken": "<refresh token>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `token` | `string` | The expired (or still valid) JWT access token |
| `refreshToken` | `string` | The active refresh token from the last login or refresh call |

---

### ✅ `200 OK` — New token pair issued

Same shape as the login `200 OK` response — store the new `token` and `refreshToken` and discard the old ones.

```json
{
  "id": "a3f1c2d4-0000-0000-0000-000000000000",
  "email": "student@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "profilePictureUrl": "https://cdn.example.com/pics/john.jpg",
  "token": "<new JWT access token>",
  "expinresIn": 3600,
  "refreshToken": "<new refresh token>",
  "refreshTokenExpiration": "2026-05-05T10:00:00Z"
}
```

---

### ❌ `401 Unauthorized` — JWT is invalid or cannot be parsed

```json
{
  "statusCode": 401,
  "errorMessage": "Invalid Jwt token"
}
```

---

### ❌ `401 Unauthorized` — Refresh token is expired, revoked, or not found

```json
{
  "statusCode": 401,
  "errorMessage": "Invalid Jwt token"
}
```

---

### ❌ `401 Unauthorized` — Account is locked out

```json
{
  "statusCode": 401,
  "errorMessage": "User with Email student@example.com is locked out."
}
```

---

### ❌ `500 Internal Server Error` — Account is administratively disabled

```json
{
  "statusCode": 500,
  "errorMessage": "User with email student@example.com is disabled."
}
```

---

## 8. App Flow Diagram


