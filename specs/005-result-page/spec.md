# Feature Specification: Result Page

**Feature Branch**: `005-result-page`  
**Created**: 2026-04-17  
**Status**: Draft  
**Input**: User description: "005-result-page"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Exam Score and Grade (Priority: P1)

After successfully submitting an exam, the student is automatically navigated to the Result page. The page displays a clear summary of their performance: exam title, exam code, score (e.g., 7 / 10), percentage (e.g., 70%), and whether they passed or failed.

**Why this priority**: The score summary is the primary reason the student waits for the result. Without it, the Result page delivers no value.

**Independent Test**: Can be fully tested by navigating directly to the Result page with a mock `submitResult` set in main.js and verifying that score, total, percentage, pass/fail status, and exam title are all displayed correctly.

**Acceptance Scenarios**:

1. **Given** the student has just submitted an exam and is navigated to the Result page, **When** the page loads, **Then** the exam title, exam code, score (e.g., "7 / 10"), percentage (e.g., "70%"), and a pass/fail indicator are all visible.
2. **Given** the student passed (percentage is at or above the threshold), **When** the page renders the pass/fail indicator, **Then** it shows a "Passed" state in a visually distinct positive style.
3. **Given** the student failed (percentage is below the threshold), **When** the page renders the pass/fail indicator, **Then** it shows a "Failed" state in a visually distinct negative style.
4. **Given** the Result page loads with no `submitResult` in memory but a known `attemptId` is available, **When** the page initialises, **Then** the page calls `GET /api/QuizAttempts/result/{attemptId}` to recover the result and displays it normally.
5. **Given** the Result page loads with no `submitResult` in memory and no `attemptId` is available, **When** the page initialises, **Then** the student is redirected to the Login page with no result content shown.

---

### User Story 2 - Review Per-Question Breakdown (Priority: P2)

Below the score summary, a question-by-question breakdown is always visible without any toggle or expand interaction. Each row shows the question text, the answer the student selected, the correct answer, and whether they got it right or wrong.

**Why this priority**: Students need feedback on which questions they got wrong so they can learn from the exam. This depends on US1 but adds significant educational value.

**Independent Test**: Can be fully tested by loading the Result page with a `submitResult` containing multiple questions of both `isCorrect: true` and `isCorrect: false` and verifying each row's content and styling matches expectations.

**Acceptance Scenarios**:

1. **Given** the Result page is loaded with a `submitResult` containing a `questions` array, **When** the page renders, **Then** a question breakdown section is displayed listing every question.
2. **Given** a question entry with `isCorrect: true`, **When** rendered in the breakdown, **Then** the row shows the question text, the student's selected answer, the correct answer, and a "Correct" indicator in a positive style.
3. **Given** a question entry with `isCorrect: false`, **When** rendered in the breakdown, **Then** the row shows the question text, the student's incorrect selection, the correct answer, and an "Incorrect" indicator in a negative style.
4. **Given** a student is viewing the breakdown, **When** the list is long (more than 10 questions), **Then** the breakdown is scrollable and all questions are accessible without the page layout breaking.

---

### User Story 3 - Exit to Home After Reviewing (Priority: P3)

After reviewing their result the student can exit back to the Exam Access (exam code entry) page without logging out. Their authenticated session remains intact so they can immediately enter another exam code or choose to log out from the Exam Access page.

**Why this priority**: Students need a way out of the result state. However it has lower priority since the exam workflow is already complete at this point.

**Independent Test**: Can be fully tested by viewing the Result page and clicking the exit/home button, then verifying navigation lands on the Exam Access (exam code) page.

**Acceptance Scenarios**:

1. **Given** the student is viewing the Result page, **When** they click the "Back to Home" (or equivalent) button, **Then** they are navigated to the Exam Access page.
2. **Given** the student exits to home, **When** main.js processes the navigation, **Then** both the in-memory `submitResult` and `examSession` are cleared so that navigating back to the Result page redirects to Login (no stale attempt data persists).

---

### Edge Cases

- What happens when `submitResult` is `null` but `attemptId` is known? → Call `GET /api/QuizAttempts/result/{attemptId}` to recover; display result on success.
- What happens when `submitResult` is `null` and `attemptId` is unknown (cold navigation with no session)? → Redirect to Login.
- What happens when the `questions` array in `submitResult` is empty? → Show score summary only, hide the breakdown section gracefully.
- What happens when `percentage` is exactly at the pass threshold (e.g., 50%)? → System must consistently treat it as "Passed" (threshold is inclusive).
- What happens when the student closes and reopens the app after submitting? → No `submitResult` survives app restart (in-memory only); student is redirected to Login.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Result page MUST display the exam title, exam code, numeric score (e.g., "7"), total questions (e.g., "10"), percentage (e.g., "70.0%"), and a pass/fail indicator. In the visual redesign (Phase 7), percentage is shown inside an SVG progress ring; the pass/fail indicator is rendered as a compact chip directly below the ring — both are required.
- **FR-002**: The pass/fail indicator MUST derive its state by comparing the `percentage` field against a fixed client-side threshold of 50% (inclusive). No server-provided threshold field is expected. The indicator is a "Passed" / "Failed" chip rendered below the SVG progress ring in the hero card (not a separate chip in the score summary as in the base design); its positive and negative visual styles MUST use only CSS custom property tokens.
- **FR-003**: The Result page MUST display a per-question breakdown that is always visible (no collapse/expand toggle for the section) below the score summary, listing every question's text, the student's selected answer, the correct answer, and a correct/incorrect indicator. Per-item filtering via All / Correct / Incorrect tabs is acceptable — the section container is always on screen and all questions remain accessible by switching back to "All".
- **FR-004**: On load, the Result page MUST first check for in-memory `submitResult`; if absent, it MUST attempt to recover by calling `GET /api/QuizAttempts/result/{attemptId}` (using the stored `attemptId` and access token). If recovery succeeds, the result is displayed normally. Error handling MUST cover all failure branches: (a) if no `attemptId` is available → redirect silently to Login; (b) if the LMS returns HTTP 401 → clear session (keytar + sessionMemory) and redirect silently to Login; (c) if the LMS returns any other error (HTTP 4xx/5xx, network failure, or malformed response) → redirect to Login. The `#back-btn` element MUST be disabled while the recovery request is in-flight to prevent concurrent navigation. **Cross-spec prerequisite (spec 004)**: `bridge:submit-exam` MUST NOT null `examSession` on success — `examSession.attemptId` must remain populated until `bridge:clear-submit-result` is invoked.
- **FR-005**: A "Back to Home" button MUST navigate the student to the Exam Access page, clear both the in-memory `submitResult` and `examSession` in main.js, and leave the authenticated session (keytar / sessionMemory) intact.
- **FR-006**: All visual styles MUST conform to the existing "Ethereal Authority" design system using only CSS custom property tokens — no hardcoded colour or typography values.
- **FR-007**: The Result page MUST be fully readable with the breakdown list rendered when the `questions` array contains 50 or more entries without layout breaking.
- **FR-008**: When the `questions` array is empty or absent, the breakdown section MUST be hidden and the score summary alone is shown.
- **FR-009**: A `bridge:get-result` IPC channel MUST be added to main.js and exposed via preload.js to call `GET /api/QuizAttempts/result/{attemptId}` with the stored access token and return the result shape or a typed error.

### Key Entities

- **SubmitResult**: The result object returned by the LMS after exam submission, stored in main.js `submitResult`. Fields: `quizCode` (string), `quizTitle` (string), `score` (int), `totalQuestions` (int), `percentage` (double), `questions` (array of QuestionResult).
- **QuestionResult**: One entry in `SubmitResult.questions`. Fields: `questionText` (string), `studentChoice` (string), `correctChoice` (string), `isCorrect` (bool).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Students can see their score, percentage, and pass/fail status within 1 second of the Result page loading.
- **SC-002**: All questions (up to 100) in the breakdown are visible and correctly labelled as correct or incorrect without any truncation or overflow.
- **SC-003**: 100% of direct URL navigations (no `submitResult` in memory) redirect to the Login page — no result content is ever shown without a valid result.
- **SC-004**: The "Back to Home" action consistently clears `submitResult` so that navigating back to the Result page immediately re-redirects to Login.
- **SC-005**: The Result page uses zero hardcoded colour or font values — all visual tokens come from the design system.

## Clarifications

### Session 2026-04-17

- Q: Is the per-question breakdown always visible or hidden behind a toggle? → A: Always visible below the score summary — no collapse/expand toggle.
- Q: What happens to the authenticated session when the student clicks "Back to Home"? → A: Stay logged in and navigate to the Exam Access page — session tokens are not cleared.
- Q: How is the pass/fail threshold determined — hardcoded client-side or read from the server? → A: Hardcoded 50% client-side; no server threshold field is expected.
- Q: If `submitResult` is absent in memory, should the Result page re-fetch from the LMS or redirect to Login? → A: Re-fetch via `GET /api/QuizAttempts/result/{attemptId}` if `attemptId` is known; redirect to Login only if `attemptId` is also unavailable.
- Q: Should `examSession` be cleared alongside `submitResult` when "Back to Home" is clicked? → A: Yes — clear both `submitResult` and `examSession` on exit to prevent stale attempt data.

### Session 2026-04-17 (Phase 7 Visual Redesign)

- Q: Should the redesigned page retain a "Passed" / "Failed" text label now that the score summary uses an SVG progress ring instead of the original pass/fail chip? → A: Yes — keep a compact "Passed" / "Failed" chip directly below the SVG ring inside the hero card. Percentage alone is not sufficient; the chip is required to satisfy FR-001 and FR-002.
- Q: Does FR-003 "always visible" mean all questions must be simultaneously rendered, or only that the breakdown section is always present? → A: The section container is always present and cannot be collapsed — per-item filtering via All / Correct / Incorrect tabs is acceptable since all questions remain accessible via the "All" tab.

## Assumptions

- The LMS `percentage` field is calculated server-side as `(score / totalQuestions) * 100`; the Result page does not recalculate it.
- Pass threshold is hardcoded at 50% (inclusive) on the client side. The LMS API does not return a threshold field and no server-provided value is expected or read.
- The `submitResult` is available in main.js in-memory state immediately after the Exam page submission — the Result page retrieves it via the existing `bridge:get-submit-result` IPC handler.
- The `bridge:get-submit-result` IPC channel is already implemented in main.js and preload.js (spec 004).
- A `bridge:clear-submit-result` IPC channel will need to be added to main.js and exposed via preload.js to support FR-005 (clearing result on exit).
- A `bridge:get-result` IPC channel (FR-009) will need to be added to main.js and preload.js; it calls `GET /api/QuizAttempts/result/{attemptId}` on the Python bridge.
- The Python bridge will need a corresponding `GET /result/<attempt_id>` route added to `exam_bp` in `python_bridge/exam.py`.
- The `attemptId` used for recovery will be sourced from `examSession?.attemptId` in main.js (still populated during the exam even after submission completes).
- The Result page is the terminal screen of the exam workflow — no navigation deeper is required.
- The design system tokens (CSS custom properties) are defined in `frontend/assets/design-tokens.css` and available to all pages via their stylesheet link.
- Mobile/tablet form factors are out of scope; the target is the Electron desktop window (minimum 1200×800).
