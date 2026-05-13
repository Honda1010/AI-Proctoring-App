# Feature Specification: Offline Resilience

**Feature Branch**: `014-offline-resilience`
**Created**: 2026-05-13
**Status**: Draft
**Input**: User description: "Add offline resilience feature to an AI proctoring desktop application."

## Clarifications

### Session 2026-05-13

- Q: How often should the local snapshot be saved — only on every answer change, or also on a time-based interval as a fallback? → A: Save on every answer change AND every 30 seconds as a heartbeat interval.
- Q: Which mechanism should be used as the primary connectivity detector? → A: Periodic ping to the exam server/backend every 5 seconds.
- Q: Should AI proctoring services continue running while the student is offline? → A: Pause all proctoring services while the offline page is shown; resume them when the exam resumes.
- Q: Should the exam countdown timer keep running during the offline period? → A: Freeze the exam timer while offline; resume it from exactly where it paused upon reconnection.
- Q: Should the offline page visually escalate its urgency as the remaining offline budget decreases? → A: Yes — neutral state initially, amber warning at ~50% budget remaining, red critical state at ~20% remaining.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Graceful Offline Transition (Priority: P1)

A student loses internet connection mid-exam. Instead of crashing or freezing, the app immediately exits fullscreen and shows a dedicated offline page. The page displays how much time the student has left before their exam is locked and how many questions they have already answered, reassuring them that their progress is safe.

**Why this priority**: This is the core safety net of the entire feature. Without it, students have no feedback and no protection. Every other story depends on this being solid.

**Independent Test**: Can be fully tested by disabling the network adapter mid-exam and verifying the offline page appears with accurate time-remaining and answered-question counts.

**Acceptance Scenarios**:

1. **Given** a student is actively taking an exam in fullscreen, **When** they lose internet connection, **Then** the app exits fullscreen within 3 seconds and displays the offline page.
2. **Given** the offline page is showing, **When** the student views it, **Then** they can see a countdown of remaining offline time budget and a count of already-answered questions.
3. **Given** the offline page is showing, **When** the student's answers were saved locally before going offline, **Then** no answers are lost and the count shown is accurate.

---

### User Story 2 - Seamless Reconnection & Exam Resume (Priority: P1)

A student goes offline and then restores their connection before the offline time budget or disconnection count is exhausted. The offline page fades away, the app returns to fullscreen, and the exam resumes on exactly the same question with the same time remaining on the exam clock.

**Why this priority**: This is the success-path of the feature. If reconnection does not restore state correctly, the feature is broken for every student who reconnects in time.

**Independent Test**: Can be fully tested by disconnecting and reconnecting within the allowed budget and confirming the resumed state matches the pre-disconnection state exactly (same question, same timer value).

**Acceptance Scenarios**:

1. **Given** the student is on the offline page with time budget remaining, **When** their internet connection is restored, **Then** the offline page fades out and the exam resumes within 3 seconds.
2. **Given** the exam resumes after reconnection, **When** the student views the exam, **Then** they are on exactly the same question they were on before going offline.
3. **Given** the exam timer was at T seconds when connection was lost, **When** the exam resumes after reconnection, **Then** the exam timer resumes from exactly T seconds — it was frozen during the offline period and no exam time was consumed.

---

### User Story 3 - Exam Lock on Budget Exhaustion or Excess Disconnections (Priority: P2)

A student remains offline until either the total offline time budget is exhausted or they have disconnected more times than the configured maximum. The offline page transforms into a lock screen informing the student that their exam is locked and asking them to reconnect to submit. When they reconnect, their already-answered questions are submitted automatically without any action from the student.

**Why this priority**: This enforces exam integrity. It must work correctly before any UI polish or recovery features are built.

**Independent Test**: Can be fully tested by configuring a short offline budget (e.g., 1 minute) and staying offline until the timer hits zero, then verifying the lock screen appears and auto-submission occurs on reconnect.

**Acceptance Scenarios**:

1. **Given** the student is offline and the time budget reaches zero, **When** the budget is exhausted, **Then** the offline page immediately transforms into a lock screen without requiring any student action.
2. **Given** the student has disconnected more times than the configured maximum, **When** the next disconnection occurs, **Then** the exam is immediately locked regardless of remaining time budget.
3. **Given** the exam is locked and the student reconnects, **When** the connection is restored, **Then** all already-answered questions are submitted automatically without any student interaction.
4. **Given** the exam was locked, **When** the student views the lock screen, **Then** it displays a clear message that the exam is locked and instructs them to reconnect to submit.

---

### User Story 4 - App Crash & Session Recovery (Priority: P2)

The app crashes or is closed unexpectedly during an active exam. When the student reopens the app, their session is fully restored to exactly where it was — same question, same answers, same exam time remaining. If the exam was already locked before the crash, reopening shows the locked state rather than restoring an active session.

**Why this priority**: Crash recovery protects students from data loss due to system instability. It also ensures the lock state is permanent and cannot be bypassed by closing the app.

**Independent Test**: Can be fully tested by force-quitting the app mid-exam, reopening it, and verifying the session restores correctly. A second test force-quits after a lock and verifies the locked state is preserved on reopen.

**Acceptance Scenarios**:

1. **Given** a student is mid-exam with answered questions, **When** the app is unexpectedly closed and then reopened, **Then** the student is returned to exactly the same question with all previous answers intact.
2. **Given** the exam was locked before the app crashed, **When** the student reopens the app, **Then** the app displays the lock screen rather than restoring an active exam.
3. **Given** the exam timer was at T seconds when the app crashed, **When** the session is restored, **Then** the timer resumes from the correct remaining time.

---

### User Story 5 - Never-Reconnected Session Flagging (Priority: P3)

If a student's exam is locked but they never reconnect to submit, their session is flagged so the instructor can review it and decide on the appropriate outcome.

**Why this priority**: This is an administrative safety net. It does not affect the student experience directly but ensures no session falls through the cracks.

**Independent Test**: Can be fully tested by locking an exam session and never reconnecting, then checking the session data to confirm the session is flagged for instructor review.

**Acceptance Scenarios**:

1. **Given** an exam session is locked, **When** the student never reconnects within the exam's active window, **Then** the session is marked with a flag indicating it requires instructor review.
2. **Given** a flagged session, **When** the instructor views it, **Then** they can see the flag and all answered questions available for review.

---

### Edge Cases

- What happens when the offline budget is exactly 0 minutes? The exam should lock immediately on the first disconnection.
- What happens if the device clock is changed while offline? The system should use elapsed wall-clock time measured from the moment of disconnection, not a value derived from the system clock alone.
- What happens if the student disconnects and reconnects in under 2 seconds? Short flickers below this threshold are treated as noise and do not count against the disconnection count or the time budget.
- What happens if the app restores a session but the exam window has already expired server-side? The app should show the lock screen, not an active exam.
- What happens if the local state is corrupted or missing on crash recovery? The system should fail gracefully with an informative message rather than crashing again.
- What happens to any proctoring events that were in-flight (e.g., a face alert being processed) at the exact moment of disconnection? In-flight events already captured before the offline trigger are retained; no new events are recorded from the point the offline page is shown.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect internet connectivity loss within 5 seconds of it occurring.
- **FR-002**: The system MUST exit fullscreen and display a dedicated offline page immediately upon detecting a disconnection.
- **FR-003**: The offline page MUST display the remaining offline time budget as a live countdown.
- **FR-004**: The offline page MUST display the number of questions the student has already answered.
- **FR-005**: The maximum total offline time budget (in minutes) MUST be a configurable value in the application config file, changeable without modifying code.
- **FR-006**: The maximum number of allowed disconnections MUST be a configurable value in the application config file, changeable without modifying code.
- **FR-007**: The offline time budget MUST be cumulative across all disconnections within the same exam session; it MUST NOT reset between reconnections.
- **FR-008**: The system MUST lock the exam when the cumulative offline time budget is exhausted.
- **FR-009**: The system MUST lock the exam when the number of disconnections exceeds the configured maximum.
- **FR-010**: Upon exam lock, the offline page MUST transform into a lock screen informing the student their exam is locked and instructing them to reconnect to submit.
- **FR-011**: When the student reconnects after the exam is locked, the system MUST automatically submit all already-answered questions without requiring any student action.
- **FR-012**: When the student reconnects before the exam is locked, the app MUST restore fullscreen and resume the exam on the same question. The exam timer MUST resume from exactly the value it held at the moment of disconnection — the timer is frozen during the entire offline period and no exam time is deducted.
- **FR-013**: The student's answers and exam progress MUST be saved locally on the device on every answer change AND on a 30-second heartbeat interval, so no progress is lost due to a connection issue or idle reading period.
- **FR-014**: On app crash or unexpected close during an active exam, reopening the app MUST restore the student's session to exactly where they left off.
- **FR-015**: If the exam was already locked before the app closed, reopening MUST display the lock screen and MUST NOT restore an active exam session.
- **FR-016**: If a locked exam session is never submitted by reconnection, the system MUST flag the session for instructor review.
- **FR-017**: The system MUST detect connectivity by sending a lightweight ping to the exam server every 5 seconds; a failed ping is the trigger for the offline state, not the OS-level network status.
- **FR-018**: All AI proctoring services (face detection, eye gaze, speech detection, object detection) MUST be paused when the offline page is shown and MUST resume automatically when the exam resumes after reconnection. No proctoring violations MUST be recorded during the offline period.
- **FR-019**: The offline page MUST visually escalate its urgency as the remaining offline time budget decreases: neutral appearance when more than 50% of the budget remains, amber/warning appearance when 50% or less remains, and red/critical appearance when 20% or less remains.

### Key Entities *(include if feature involves data)*

- **OfflineSession**: Tracks the start time of each disconnection, cumulative offline duration used so far, disconnection count for the current exam attempt, and lock status.
- **LocalExamSnapshot**: The locally persisted state of the exam — current question index, all answers given, exam timer value at last save, and lock status.
- **OfflineConfig**: The configurable policy values — `max_offline_minutes` and `max_disconnections` — read from the application config file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A student who loses and restores connection within budget can continue their exam with zero loss of answers or exam time, verified in 100% of reconnection test scenarios.
- **SC-002**: The app detects a disconnection and displays the offline page within 5 seconds of connection loss in all test cases.
- **SC-003**: The exam lock triggers within 3 seconds of the budget being exhausted or the disconnection limit being exceeded.
- **SC-004**: Auto-submission on reconnect after a lock completes successfully in 100% of test cases where the student eventually reconnects.
- **SC-005**: A crash-recovered session matches the pre-crash state exactly (same question, same answers, correct timer) in 100% of crash recovery test scenarios.
- **SC-006**: Changing `max_offline_minutes` or `max_disconnections` in the config file takes effect for the next exam session without any code changes.
- **SC-007**: Never-reconnected locked sessions are flagged and visible for instructor review.
- **SC-008**: The offline page transitions to the amber warning state at or before 50% of the budget is consumed, and to the red critical state at or before 20% remaining, in 100% of test scenarios.

## Assumptions

- The application config file (`config.json`) is an established project mechanism; `max_offline_minutes` and `max_disconnections` will be added as new fields.
- Connectivity detection uses a periodic ping to the exam server every 5 seconds. A failed ping is the definitive signal for going offline. `navigator.onLine` is NOT relied upon as it can produce false positives on local networks.
- Local persistence will use the file system already accessible in Electron; no new storage infrastructure is required.
- The exam timer is managed client-side and is frozen the moment the offline state is triggered. The saved snapshot records the frozen timer value. The server reconciles this value on reconnect.
- Answers are already tracked client-side; this feature extends the existing save path to flush to disk on every answer change and on a 30-second heartbeat interval.
- A disconnection shorter than 2 seconds (flicker threshold) does not count against the disconnection count or offline time budget.
- The instructor-facing session view already exists; this feature adds a `flagged_for_review` field to the session data model.
- Mobile support and multi-device exam sessions are out of scope for this feature.
