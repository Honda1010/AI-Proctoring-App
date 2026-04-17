# Feature Specification: Exam Page

**Feature Branch**: `004-exam-page`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "004-exam-page"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load and Browse Questions (Priority: P1)

A student has successfully entered the exam access code on the previous page. The app navigates to the Exam page, where all exam questions and choices are displayed. The student can move forward to the next question, go back to a previous question, jump to any question via a navigator panel, and see which questions they have and haven't answered yet.

**Why this priority**: This is the foundation of the entire exam experience. Without the ability to load questions and navigate between them, no other exam functionality is testable or deliverable.

**Independent Test**: Can be fully tested by launching the app to the Exam page (with a valid `examSession` in main.js containing multiple questions), verifying the first question and its choices are displayed, and confirming that Previous/Next buttons navigate correctly, navigator pills reflect answered/unanswered states, and the "Jump to" input moves to the specified question.

**Acceptance Scenarios**:

1. **Given** the Exam page loads with a valid `examSession`, **When** the page finishes initialising, **Then** the exam title is shown in the header, the first question text is displayed, all choices are rendered with letter labels (A, B, C, D), and the "Question 1 of N" badge is visible.
2. **Given** a student is on question 1, **When** they click "Next Question", **Then** the page transitions to question 2 and the "Question 2 of N" badge updates accordingly.
3. **Given** a student is on question 1, **When** they view the Previous button, **Then** the Previous button is disabled (cannot be clicked).
4. **Given** a student is on the last question, **When** they view the Next button, **Then** the Next button is disabled (cannot be clicked).
5. **Given** a student is on any question, **When** they click a question number pill in the navigator, **Then** the page navigates directly to that question.
6. **Given** a student types a valid question number (e.g., "5") in the "Jump to" input and presses Enter, **When** the input is processed, **Then** the page navigates directly to question 5.
7. **Given** main.js has no `examSession` (student navigated directly to the URL), **When** the page initialises, **Then** the student is immediately redirected to the Login page with no exam content shown.

---

### User Story 2 - Select and Change Answers (Priority: P1)

A student reads a question and selects one of the available choices. The selection is visually highlighted. If they navigate away and return, their selection is still present. They can change their selection at any time before submitting.

**Why this priority**: Answer capture is the core deliverable of an exam. Without it, the exam cannot be submitted with meaningful data.

**Independent Test**: Can be fully tested by selecting a choice on question 1, navigating to question 2, returning to question 1, and verifying the choice is still selected. Then changing the selection and confirming the new choice is captured.

**Acceptance Scenarios**:

1. **Given** a student is viewing a question, **When** they click a choice, **Then** that choice is visually selected (filled circle, border highlight), the other choices are deselected, and the question's navigator pill changes to its "answered" state.
2. **Given** a student has selected choice B on question 3, **When** they navigate to question 4 and return to question 3, **Then** choice B is still selected.
3. **Given** a student has selected choice A, **When** they click choice C for the same question, **Then** choice C becomes selected, choice A is deselected, and the `answerMap` holds only `choiceId` of C for this question.
4. **Given** a student has selected a choice, **When** they view the question navigator, **Then** that question's pill appears in the "answered" style (filled primary colour) distinct from unanswered pills.

---

### User Story 3 - Submit Exam (Priority: P2)

A student has finished answering questions and is ready to submit. They click "Submit Exam" in the header. A confirmation modal appears, showing how many questions remain unanswered and asking them to confirm. Once confirmed, the answers are sent to the server and the student is taken to the result page.

**Why this priority**: Submission is the goal of the exam session. It depends on US1 and US2 being complete but delivers the final outcome students expect.

**Independent Test**: Can be fully tested by answering some (not all) questions, clicking "Submit Exam", verifying the modal shows the correct unanswered count, confirming, and verifying navigation to the result page with the result data available.

**Acceptance Scenarios**:

1. **Given** a student clicks "Submit Exam" in the header, **When** the button is clicked, **Then** a confirmation modal appears with the exam title, the number of unanswered questions, and Cancel / Confirm buttons.
2. **Given** the confirmation modal is showing, **When** the student clicks Cancel, **Then** the modal closes and the exam resumes from where they left off with the timer still running.
3. **Given** the confirmation modal is showing, **When** the student clicks Confirm, **Then** the submission request is sent, a loading state (spinner, disabled controls) is applied to the page, and on success the student is navigated to the result page.
4. **Given** zero questions have been answered, **When** the student clicks Submit and the modal appears, **Then** the modal's message changes to "You haven't answered any questions yet" to give clearer guidance.
5. **Given** the submission request fails due to a network or bridge error, **When** the error response arrives, **Then** the loading state is cleared, the timer resumes, an inline error message is shown, and the student can retry.

---

### User Story 4 - Countdown Timer (Priority: P2)

The header displays a countdown timer that starts from the exam duration and counts down to 0:00. When the timer reaches 0:00, the exam is automatically submitted with whatever answers have been given — no confirmation dialog is shown.

**Why this priority**: Time-limited exams are a core proctoring requirement. Auto-submit on expiry ensures fairness and prevents students from taking extra time.

**Independent Test**: Can be tested by loading a short-duration mock exam (e.g., `"duration": "00:00:10"`) and verifying the timer counts down to 0:00 and then auto-submission fires without any user interaction.

**Acceptance Scenarios**:

1. **Given** the exam page has loaded, **When** the timer starts, **Then** it displays the full exam duration (e.g., "01:30:00") and decrements every second.
2. **Given** the timer is running, **When** it reaches "00:05:00" (5 minutes remaining), **Then** the timer changes to a warning colour to alert the student that time is running short.
3. **Given** the timer reaches "00:00:00", **When** the auto-submit fires, **Then** all current answers are sent to the server without a confirmation dialog, and the student is navigated to the result page on success.
4. **Given** the exam is in the loading/submission state, **When** the timer would normally decrement, **Then** the timer is paused and does not continue during the submission round-trip.

---

### User Story 5 - Flag Questions for Review (Priority: P3)

A student wants to revisit a question they are unsure about. They can flag it using the flag button on the question. Flagged questions appear with a distinct indicator in the question navigator, making them easy to find later.

**Why this priority**: Flagging improves exam experience but is not essential to completing or submitting an exam. It is a quality-of-life feature.

**Independent Test**: Can be tested by clicking the flag button on question 2, verifying its navigator pill changes to the "flagged" state, navigating away and back, and confirming the flag persists. Then unflagging and verifying the pill reverts.

**Acceptance Scenarios**:

1. **Given** a student is on a question, **When** they click the flag button, **Then** the flag button changes to its active state and the corresponding navigator pill reflects the "flagged" style.
2. **Given** a question is already flagged, **When** the student clicks the flag button again, **Then** the question is unflagged and the navigator pill reverts to its previous state (answered or unanswered).
3. **Given** a student has both answered and flagged a question, **When** they view the navigator, **Then** the pill shows the "flagged" style (taking priority over "answered" styling) so they know it still needs review.

---

### User Story 6 - Proctoring Panel (Priority: P3)

The right side of the exam page shows a proctoring panel. A live webcam feed is displayed so the student can see they are being monitored. The panel also lists AI analysis status rows (Face Detection, Eye Tracking, Object Detection, etc.) as static indicators. The student's camera is released when they leave the exam page.

**Why this priority**: The webcam feed is a visible proctoring signal. The AI processing itself is out of scope for this spec; the panel is a visual placeholder for future AI integration.

**Independent Test**: Can be tested by verifying the `<video>` element shows the live webcam feed after getUserMedia is granted, verifying the "Camera unavailable" placeholder appears when permission is denied, and verifying the video tracks are stopped on page navigation.

**Acceptance Scenarios**:

1. **Given** the exam page loads and the browser grants camera permission, **When** initialisation completes, **Then** the `<video>` element in the proctoring panel shows the live webcam feed with a "LIVE FEED" badge.
2. **Given** the browser denies camera access, **When** the getUserMedia call fails, **Then** a "Camera unavailable" placeholder is shown in the video area; the rest of the exam operates normally.
3. **Given** the webcam is active, **When** the student navigates away from the exam page (on submit, timeout, or logout), **Then** all MediaStreamTrack instances are stopped so the camera indicator light goes off.

---

### Edge Cases

- What happens when a student submits with zero answered questions?  
  → The confirmation modal shows "You haven't answered any questions yet" instead of the normal unanswered count message; submission is still allowed and the empty payload is sent.
- What happens if the "Jump to" input contains a number outside the valid range (e.g., 0 or > total questions)?  
  → The navigation is ignored; the input is cleared and focus returns to it; no error message is shown.
- What happens if the "Jump to" input contains non-numeric text?  
  → The navigation is ignored; the input is cleared.
- What happens if the submission returns UNAUTHORIZED (e.g., token expired during exam)?  
  → The session is cleared and the student is redirected to the Login page silently; no error is shown on the exam page.
- What happens if the ExamSession returned from main.js has no questions?  
  → An error state is shown ("This exam has no questions."); no navigation occurs.
- What does the student see while the initial `bridge:get-exam-session` IPC call is resolving?  
  → A full-page loading skeleton (spinner and dimmed placeholder) is shown until the call resolves. On success it is replaced with the real exam content; on failure the app redirects to Login.
- What happens if the student rapidly clicks "Next" multiple times?  
  → Navigation is synchronous and immediate; no duplicate renders occur; the minimum question index is 0 and maximum is `questions.length - 1`.
- What happens if the timer runs out during the submit loading state (e.g., a delayed response)?  
  → The timer is already paused during submission; auto-submit does not re-trigger if submission is already in progress.
- What happens if the auto-submit (triggered at 00:00:00) itself fails with a network or bridge error?  
  → The loading state is dismissed, an inline error message with a "Retry" button is shown, and the timer remains frozen at 00:00:00. The student can manually click Retry until the submission succeeds. The timer does not resume because time has already expired.
- What happens if the student closes the window mid-exam?  
  → The `beforeunload` handler stops all camera tracks; no auto-save of answers occurs; the `examSession` in main.js is not persisted — the student must re-enter their code on next launch.
- Is there a logout option during an active exam?  
  → No. The only exits from the Exam page are submitting the exam or timer expiry. There is no logout button on the Exam page; the proctoring panel and header contain no logout control.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST retrieve the `ExamSession` (attemptId, title, duration, questions) via `bridge:get-exam-session` on `DOMContentLoaded`; while the IPC call is in progress, a full-page loading skeleton (spinner + dimmed placeholder) MUST be shown; if the result returns `{ ok: false }`, the system MUST immediately redirect to the Login page; on success the skeleton MUST be replaced with the full exam content.
- **FR-002**: System MUST display the exam title in the fixed header and a running countdown timer initialised from `examSession.duration` (formatted as `HH:mm:ss`).
- **FR-003**: System MUST render the current question's text and all of its choices, each labelled with a sequential letter (A, B, C, … for up to the number of choices provided), one question at a time.
- **FR-004**: System MUST display a "Question X of N" badge above the question text, where X is the 1-based current question index and N is the total number of questions.
- **FR-005**: System MUST allow the student to select exactly one choice per question; selecting a choice records the choice's ID in an in-memory `answerMap` keyed by the question's ID.
- **FR-006**: System MUST allow the student to change their answer at any time before submission; changing a selection replaces the previous `choiceId` in the `answerMap` for that question.
- **FR-007**: System MUST provide "Previous" and "Next Question" navigation buttons; "Previous" MUST be disabled when the student is on question 1; "Next Question" MUST be disabled when the student is on the last question.
- **FR-008**: System MUST display a question navigator (pill row) showing one button per question; each button MUST visually reflect the question's state: **unanswered** (neutral), **answered** (primary fill), **current** (primary fill + ring), **flagged** (warning/orange — takes priority over answered state).
- **FR-009**: System MUST provide a "Jump to" input in the navigator; entering a valid question number and pressing Enter MUST navigate to that question; invalid input MUST be silently ignored and the field cleared.
- **FR-010**: System MUST provide a flag/unflag toggle button on each question; toggling MUST update the question's state in a `flagSet` and immediately reflect the change in the corresponding navigator pill.
- **FR-011**: System MUST display a "Submit Exam" button in the fixed header that is always visible and clickable (except during active submission).
- **FR-012**: System MUST show a confirmation modal when "Submit Exam" is clicked; the modal MUST display the exam title, the number of unanswered questions (or a "no answers" message if zero), and Cancel / Confirm buttons.
- **FR-013**: System MUST collect all entries from `answerMap` as `[{ questionId, choiceId }]`, call `bridge:submit-exam` with this payload, apply a full loading/disabled state to all interactive controls, and on success navigate to the result page; questions not present in `answerMap` MUST be omitted from the payload.
- **FR-014**: System MUST start the countdown timer from `examSession.duration` immediately after the `ExamSession` is loaded; the timer MUST decrement by one second each second using a drift-corrected interval.
- **FR-015**: System MUST change the timer display to a warning colour when 5 minutes or fewer remain.
- **FR-016**: System MUST auto-submit when the timer reaches `00:00:00`, using the same submission path as FR-013, without displaying a confirmation modal; if a submission is already in progress, the auto-submit MUST NOT re-trigger.
- **FR-017**: System MUST request the webcam via `getUserMedia({ video: true })` on page load; the stream MUST be assigned to a `<video>` element in the proctoring panel; if permission is denied or the call fails, a "Camera unavailable" placeholder MUST be shown and the exam MUST continue normally.
- **FR-018**: System MUST stop all active MediaStreamTrack instances when the student navigates away from the exam page (on submit success, timeout redirect, or any other navigation); this MUST be handled in a `beforeunload` handler.
- **FR-019**: System MUST handle UNAUTHORIZED errors during submission by clearing the session via `bridge:clear-session` and redirecting to the Login page.
- **FR-020**: System MUST handle network/bridge errors during submission by dismissing the loading state and showing an inline error message with a "Retry" button. If the failure occurred during a **manual submit** (timer still running), the timer MUST resume. If the failure occurred during **auto-submit** (timer already at 00:00:00), the timer MUST remain frozen at 00:00:00; the student can retry manually until submission succeeds or they close the app.
- **FR-021**: The Exam page MUST NOT provide any logout control; the only valid exits are exam submission (FR-013) and timer-triggered auto-submit (FR-016). No logout button or link MUST appear in the header, proctoring panel, or elsewhere on the page.

### Key Entities

- **ExamSession**: The exam data retrieved from main.js — `attemptId` (number), `title` (string), `duration` (HH:mm:ss string), `questions` (array of `QuestionItem`). Read-only in this spec; populated by spec 003.
- **QuestionItem**: A single question — `id` (number, required for submission), `questionText` (string), `choices` (array of `ChoiceItem`).
- **ChoiceItem**: A single answer option — `id` (number, required for submission), `choiceText` (string).
- **AnswerMap**: An in-memory renderer-scope plain object `{ [questionId: number]: choiceId: number }`. Never persisted. Drives the submit payload and navigator pill states.
- **FlagSet**: An in-memory renderer-scope `Set<number>` of flagged question IDs. Never persisted.
- **SubmitResult**: The result returned by the LMS on successful submission — `quizCode`, `quizTitle`, `score`, `totalQuestions`, `percentage`, `questions` (array with per-question correctness). Stored in main.js module scope for retrieval by spec 005.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The exam page loads and the first question is visible within 2 seconds of page navigation on a local network; the IPC round-trip to retrieve `examSession` completes in under 500 ms.
- **SC-002**: 100% of answer selections survive forward, backward, and non-sequential (pill/jump) navigation — no answer is lost or reset by navigating between questions.
- **SC-003**: The submit payload conforms exactly to `{ "answers": [{ "questionId": N, "choiceId": N }] }` for every answered question; unanswered questions are never included in the payload.
- **SC-004**: The countdown timer remains accurate to within ±1 second over a 90-minute exam duration; drift correction prevents accumulated offset.
- **SC-005**: Auto-submit fires within 1 second of the timer displaying `00:00:00` with no user interaction required.
- **SC-006**: All active webcam tracks are fully released (camera indicator light off) within 1 second of the student navigating away from the exam page.

---

## Assumptions

- The `ExamSession` is always present in main.js when this page is navigated to; the navigation from the Exam Access page (spec 003) guarantees this. Direct URL navigation without a session results in redirect to Login.
- Question and choice `id` fields are present in the ExamSession payload (confirmed per spec 003 research Decision 5); if absent, the submit payload will be malformed — this is a spec 003/005 dependency tracked separately.
- Token refresh is out of scope; a 401 during submission triggers a redirect to Login rather than an automatic token exchange.
- AI proctoring processing (face detection, eye tracking, object detection, face anti-spoofing) is fully out of scope; the proctoring panel renders static status rows as a placeholder for future integration.
- Only one exam can be in progress at a time; multi-exam management is not supported.
- The result page (spec 005) is responsible for displaying the full score and question-by-question review; storage of `SubmitResult` in main.js is the hand-off mechanism.
- The page follows the same "Ethereal Authority" visual design language established in specs 001–003, using only existing CSS custom properties from `design-tokens.css`.
- Students use the Electron desktop app on Windows 10+; there is no browser/web version of this page.
- The exam session is not persisted outside of main.js memory; if the Electron process is restarted mid-exam, the student must re-enter their code.

---

## Clarifications

### Session 2026-04-16

- Q: Should the proctoring panel (AI status indicators) be fully implemented in spec 004? → A: No — webcam feed via `getUserMedia` is implemented; AI status rows (Face Detection, Eye Tracking, etc.) are static placeholder labels with hardcoded "Active/Inactive" states. Live AI processing is deferred to a future spec.
- Q: What should happen after the student submits the exam? → A: Navigate to the result page at `../result/index.html` (spec 005). The `SubmitResult` is stored in main.js module scope as `submitResult` and retrieved by spec 005 via a new `bridge:get-submit-result` IPC channel.
- Q: When the countdown timer hits 0:00, should answers auto-submit? → A: Yes — all current answers in `answerMap` are automatically submitted without any confirmation dialog. The student is then navigated to the result page.
- Q: Should there be a logout option during an active exam? → A: No. The Exam page has no logout button; the only exits are exam submission and timer expiry. If the student needs to leave, they must close the Electron window.
- Q: What should happen when auto-submit (at 00:00:00) fails with a network/bridge error? → A: Dismiss loading state, show inline error with a "Retry" button; timer stays frozen at 00:00:00. Student manually retries until success or app is closed.
- Q: What should the student see while the initial `bridge:get-exam-session` IPC call is resolving on page load? → A: A full-page loading skeleton (spinner + dimmed placeholder) is shown until the call resolves; replaced with real exam content on success, or redirect to Login on failure.
