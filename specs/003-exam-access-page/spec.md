# Feature Specification: Exam Access Page

**Feature Branch**: `003-exam-access-page`  
**Created**: 2026-04-15  
**Status**: Draft  
**Input**: User description: "003-exam-access-page"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enter Exam Code and Start Exam (Priority: P1)

A student who has successfully logged in arrives at the Exam Access page. They type in the unique exam code provided by their instructor and press the Start Exam button. The system validates the code, creates an attempt record, and navigates the student to the active exam.

**Why this priority**: This is the sole purpose of the page. Without it, students cannot reach the exam at all.

**Independent Test**: Can be fully tested by entering a valid exam code from a logged-in session and verifying that the app transitions to the exam page with the correct title, duration, and questions loaded.

**Acceptance Scenarios**:

1. **Given** a logged-in student on the Exam Access page, **When** they enter a valid exam code and click "Start Exam", **Then** the app transitions to the Exam page displaying the correct exam title, countdown timer, and questions.
2. **Given** the code is being validated, **When** the request is in progress, **Then** the input is disabled, the submit button is disabled with its arrow icon replaced by a spinner and its label changed to "Checking…", matching the loading pattern from the Login page.
3. **Given** the validation succeeds, **When** the full response has been received, **Then** the app navigates to the Exam page — navigation does not occur until the complete response (attempt ID, title, duration, questions) is available, so the Exam page never renders in a partially-loaded state.

---

### User Story 2 - Receive Clear Error Feedback (Priority: P2)

A student enters an incorrect, expired, or already-used exam code. The page displays a specific, actionable error message so they know exactly what went wrong and what to do next.

**Why this priority**: Without meaningful errors, students are stuck with no guidance — high support burden and failure scenarios.

**Independent Test**: Can be tested independently by submitting invalid / duplicate / not-found codes and verifying that the correct error message is displayed for each case, without navigating away.

**Acceptance Scenarios**:

1. **Given** a student enters a code that does not exist, **When** they submit, **Then** an error message states the code was not found and they can try again.
2. **Given** a student has already completed an attempt for this exam, **When** they submit the code, **Then** an error message informs them the exam has already been attempted.
3. **Given** the student's session token has expired, **When** they submit, **Then** they are redirected to the Login page to re-authenticate rather than seeing a generic error.
4. **Given** the server cannot be reached, **When** they submit, **Then** a network error message is shown, the input is re-enabled with its value preserved, and the error message clears as soon as the student begins typing again.

---

### User Story 3 - Log Out from Exam Access Page (Priority: P3)

A student on the Exam Access page realises they are on the wrong account and wants to log out before starting an exam.

**Why this priority**: Users must always have an escape path from any authenticated screen.

**Independent Test**: Can be tested by clicking the logout control and verifying the session is cleared and the app returns to the Login page.

**Acceptance Scenarios**:

1. **Given** a logged-in student on the Exam Access page, **When** they trigger the logout action, **Then** their stored session (token, refresh token, profile) is cleared and the app returns to the Login page.

---

### Edge Cases

- What happens when the student submits an empty code field?  
  → Submission is blocked; an inline validation message asks them to enter a code.
- What happens when the student double-clicks or rapidly re-submits?  
  → The button is disabled immediately on first click; subsequent clicks are ignored until the response arrives.
- What happens if the network call succeeds but returns malformed data?  
  → A generic error message is shown; the student is not navigated away.
- What happens if the exam code contains leading/trailing whitespace?  
  → Whitespace is trimmed before submission so `" EXAM2026 "` is treated as `"EXAM2026"`.
- What happens if the API call does not return within the expected time?  
  → After 15 seconds the request is treated as a network failure: the loading state is cleared, the input is re-enabled with its value preserved, and a network error message is shown.
- What should the page display while the keychain session read is in progress on first load?  
  → A placeholder is shown in place of the student’s name until the keychain read resolves; the rest of the page (input, button) is rendered and usable immediately.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a single text input for the exam code and a submit button.
- **FR-002**: System MUST trim leading and trailing whitespace from the exam code before validation or submission.
- **FR-003**: System MUST prevent form submission when the code field is empty, showing an inline validation message.
- **FR-004**: System MUST disable the code input and submit button while a validation request is in progress; the button MUST replace its arrow icon with an inline spinner and change its label to "Checking…" (same pattern as the Login page submit button).
- **FR-005**: System MUST call the exam-start endpoint exactly once per submission attempt; duplicate calls for the same submission must not occur.
- **FR-006**: System MUST remain on the Exam Access page in the loading state until the full server response (attempt ID, title, duration, questions) is received; only then navigate to the Exam page, passing all data through so no additional network call is required.
- **FR-007**: System MUST display a specific, user-friendly error message for each failure case: code not found (404), already attempted (409), and network/bridge failure. After any error, the input MUST be re-enabled with its value preserved, and the error message MUST clear on the student's next keystroke.
- **FR-012**: System MUST enforce a 15-second client-side timeout on the exam-start request; if no response arrives within 15 seconds the loading state MUST be cancelled, the input re-enabled, and a network error message shown.
- **FR-008**: System MUST redirect to the Login page when the session token is invalid or expired (401 from the server).
- **FR-009**: System MUST display the logged-in student’s name or identifier so they can confirm they are on the correct account. While the keychain read is in progress on page load, a placeholder MUST be shown in place of the name; the input and button MUST be rendered and usable immediately without waiting for the name to resolve.
- **FR-010**: System MUST provide a logout action that clears all stored session data and returns the student to the Login page.
- **FR-011**: System MUST attach the student's JWT access token to the exam-start request via the Authorization header.

### Key Entities

- **ExamSession**: The attempt data returned on success — `attemptId` (int), `title` (string), `duration` (HH:mm:ss string), `questions` (array of question objects with text and choices). Passed to the Exam page; not persisted beyond the session.
- **StoredSession**: The authenticated session in the OS keychain — `token`, `refreshToken`, `userId`, `firstName`, `lastName`, `profilePictureUrl`. Read on page load to acquire the Bearer token; cleared on logout.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A student with a valid exam code can progress from the Exam Access page to the first question in under 5 seconds on a local network; in all cases the loading state resolves (success or error) within 15 seconds.
- **SC-002**: All relevant error cases (empty input, code not found, already attempted, network failure, expired token) are handled with distinct, non-generic messages — 0 unhandled error paths.
- **SC-003**: The form cannot be submitted more than once per attempt; duplicate API calls on rapid re-click are prevented 100% of the time.
- **SC-004**: The exam data (attempt ID, title, duration, questions) is fully available on the Exam page without requiring any additional network call after navigation.
- **SC-005**: Logout completes (session cleared + Login page shown) in under 1 second.

---

## Assumptions

- The student is always authenticated before reaching this page; there is no unauthenticated path to this screen.
- The stored session contains a valid JWT that can be read directly; token refresh on this page is out of scope (an expired token triggers redirect to login instead).
- The exam code is case-sensitive as provided by the instructor; the app does not alter case — only whitespace is trimmed.
- Questions and choices returned by the server carry hidden server-side IDs needed for answer submission; the Exam page spec will handle their usage.
- Only one exam attempt per session is in scope; concurrent multi-exam management is out of scope.
- The page follows the same "Ethereal Authority" visual design language established in the Login page (spec 002).

---

## Clarifications

### Session 2026-04-15

- Q: What form should the loading indicator take while the API call is in progress? → A: Spinner inside the button + button text → "Checking…", input disabled (matches Login page pattern — spec 002).
- Q: After an error is shown, what happens to the input field? → A: Input re-enabled, value preserved, error clears on next keystroke.
- Q: What should the transition feel like between Exam Access page and Exam page? → A: Stay on Exam Access page in loading state until full response received, then navigate (no flash of blank Exam page).
- Q: What happens if the API call takes too long? → A: Timeout after 15 s, cancel request, re-enable input with value preserved, show network error message.
- Q: Should there be a visible loading state during page initialisation (keychain read)? → A: Show a placeholder for the student name while keychain read resolves, then reveal; input and button are usable immediately (no full-page block).
