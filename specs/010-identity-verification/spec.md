# Feature Specification: Identity Verification Page

**Feature Branch**: `010-identity-verification`  
**Created**: 2026-04-23  
**Status**: Draft  
**Input**: User description: "Identity Verification page that captures a live webcam photo from the student before the exam begins and uses it as the reference image for the face-recognition Modal service, replacing the current hardcoded warmup image"

## Clarifications

### Session 2026-04-23

- Q: If enrollment fails (no face found, Modal unreachable) after the student clicks "Confirm & Continue", what happens? → A: Show an error pill on the Identity Verification page ("Verification failed — please retake your photo") and require a new capture.
- Q: How is face presence checked to gate the Capture button / catch bad frames? → A: Call `POST /analysis/face-detection-file` once when the student clicks "Capture Photo"; if no face is detected, show an inline error ("No face detected — adjust your position") and stay on the page without freezing the feed.
- Q: When should `POST /analysis/unenroll` be called to clear the Modal server embedding? → A: On exam submit success AND on any logout/back-to-home navigation — all exit paths from the exam must trigger unenroll.
- Q: What IPC pattern connects the Identity Verification renderer to the Electron main process for enrollment? → A: Single `bridge:enroll-reference` channel — renderer sends the captured frame (base64); main process chains `POST /analysis/face-detection-file` then `POST /analysis/enroll-file` internally and returns `{ok, error?}` to the renderer.
- Q: What UX is shown during the in-flight `bridge:enroll-reference` IPC call (face-detection + enroll network roundtrip)? → A: Freeze the captured preview, disable all buttons, show a loading spinner with "Verifying identity…" text — consistent with existing loading patterns on login and exam-code pages.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Student Captures Reference Photo (Priority: P1)

A student has entered a valid exam code and is directed to the Identity Verification page before the exam begins. Their webcam activates automatically and shows a live preview. The student positions their face within the outlined frame, waits for quality indicators to confirm adequate lighting and face detection, then clicks "Capture Photo." The captured image is stored as their reference and the student is forwarded to the AI Readiness calibration page.

**Why this priority**: This is the core action of the feature. Without a successfully captured reference image, face recognition cannot function. Every other story depends on this one succeeding first.

**Independent Test**: Can be tested by loading the identity-verification page directly, observing the live webcam feed, clicking "Capture Photo," and confirming the photo is stored and the page navigates to AI Readiness.

**Acceptance Scenarios**:

1. **Given** the student has started an exam session, **When** they reach the Identity Verification page, **Then** the webcam activates automatically and a live preview is shown inside the face-outline frame.
2. **Given** the webcam is live and a face is detected, **When** the student clicks "Capture Photo," **Then** the live feed freezes on the captured frame, a preview thumbnail is shown, and the "Capture Photo" button is replaced by a confirmation button.
3. **Given** a photo has been captured, **When** the student clicks "Confirm & Continue," **Then** the page enters a loading state ("Verifying identity…" spinner, all buttons disabled), and on enrollment success the student is navigated to the AI Readiness page.

---

### User Story 2 — Student Retakes an Unsatisfactory Photo (Priority: P2)

After capturing a photo, the student sees the preview and decides the image is blurry, poorly lit, or their face is not fully visible. They click "Retake Photo" to discard the captured image and return to the live webcam feed so they can capture a new one.

**Why this priority**: Without retake capability, a student locked into a bad reference image will experience false "face mismatch" violations throughout the entire exam.

**Independent Test**: Capture a photo, then click "Retake Photo" and verify the live feed resumes and the stored reference is cleared until a new capture is confirmed.

**Acceptance Scenarios**:

1. **Given** a photo has been captured and a preview is shown, **When** the student clicks "Retake Photo," **Then** the live webcam feed resumes and the captured image is discarded.
2. **Given** the student is on the live feed after retaking, **When** they click "Capture Photo" again, **Then** a new image is captured and stored as the reference.

---

### User Story 3 — Quality Indicators Guide the Student (Priority: P3)

While the webcam is active and before capture, three real-time environment quality indicators (Lighting, Focus, Face Detected) update to help the student understand whether the current frame is suitable for capture. The "Capture Photo" button is only fully active when at least a face is detected.

**Why this priority**: Without guidance, students may capture an unusable reference image that causes persistent false violations. This prevents that problem proactively.

**Independent Test**: Cover the camera to simulate no-face, observe the Face indicator turn to "Not Detected" and the capture button become disabled; then uncover and observe it re-enable.

**Acceptance Scenarios**:

1. **Given** the webcam is live, **When** the frame is analyzed client-side, **Then** the Face Detected indicator shows "Detected" or "Not Detected" based on a best-effort client-side check (informational only).
2. **Given** the student clicks "Capture Photo," **When** `POST /analysis/face-detection-file` returns no face detected, **Then** an inline error is shown and the live feed continues uninterrupted.
3. **Given** adequate ambient lighting, **When** the frame is analyzed client-side, **Then** the Lighting indicator shows "Adequate."

---

### User Story 4 — Captured Reference Used by Face Recognition During Exam (Priority: P1)

The reference image captured during identity verification is automatically sent alongside every live exam frame to the face-recognition Modal service, replacing the current hardcoded warmup image. The Modal service compares the live frame against the student's own captured reference to determine identity match.

**Why this priority**: This is the end-to-end purpose of the feature. The reference capture is meaningless unless it is actually used by the face-recognition service.

**Independent Test**: Capture a reference image, start the exam, and confirm the session log (JSONL) contains `face-recognition` detection events with `is_matched` field populated based on a real comparison (not a stub).

**Acceptance Scenarios**:

1. **Given** a reference image was captured on the Identity Verification page, **When** the exam begins and face-recognition runs, **Then** each prediction call includes both the reference image and the live frame.
2. **Given** the student's face matches the reference, **When** a face-recognition prediction is processed, **Then** the detection event payload contains `is_matched: true`.
3. **Given** a different person's face is shown during the exam, **When** face-recognition runs, **Then** the detection event contains `is_matched: false` and the risk score increases.

---

### Edge Cases

- What happens when the student's camera is unavailable or denied? → Capture is blocked; an error message is shown explaining camera access is required. The student cannot proceed without granting access.
- What happens if `POST /analysis/enroll-file` returns an error or the reference image contains no detectable face? → An error pill is shown ("Verification failed — please retake your photo"), the captured image is discarded, and the live webcam feed resumes. The student must capture a new photo and try again.
- What happens if the student closes the app or navigates away before confirming the capture? → No reference image is stored. Returning to the identity verification page restarts the capture flow.
- What happens if the face-recognition Modal endpoint is unreachable when the exam starts? → The service starts in a degraded state. Proctoring continues for other services (eye-gaze, speech, object-detection); face-recognition shows "Inactive" in the exam panel.
- What happens if the captured reference image is sent but the Modal service returns a verification error? → The detection event is logged with `is_matched: false`; risk score accumulates normally. The student is not blocked from continuing the exam.
- What happens if the student has already captured a reference but returns to the identity verification page (e.g., via Back)? → The existing reference is shown as a preview; the student can confirm it or retake.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display an Identity Verification page between the Exam Access page and the AI Readiness page in the navigation flow.
- **FR-002**: The Identity Verification page MUST activate the student's webcam automatically on load and display a live video feed within a face-outline frame.
- **FR-003**: The page MUST display three real-time quality indicators: Lighting, Focus, and Face Detected — updating continuously while the webcam is active using client-side heuristics (brightness for Lighting, canvas sharpness estimate for Focus, browser face-detection API or MediaPipe for Face Detected).
- **FR-004**: The "Capture Photo" button MUST always be active while the live feed is running. Face validation is deferred to the server-side check at capture time (FR-009a) rather than gating the button client-side.
- **FR-005**: If the face-detection check passes, the system MUST freeze the live feed, display the captured frame as a preview, and hold the image in memory pending the student's confirmation.
- **FR-006**: After capture, the "Retake Photo" button MUST become active; clicking it MUST discard the captured image and resume the live webcam feed.
- **FR-007**: After capture, a "Confirm & Continue" button MUST be shown. When clicked, the page MUST enter a loading state: freeze the preview, disable all buttons, and show a spinner with "Verifying identity…" text. On IPC success (`ok: true`), navigate to the AI Readiness page. On failure, show the appropriate error pill and return to the live feed.
- **FR-008**: The stored reference image MUST be accessible to the face-recognition service for the entire duration of the exam session and MUST be cleared when the session ends.
- **FR-009**: After the student confirms their captured photo, the renderer MUST invoke the `bridge:enroll-reference` IPC channel, sending the captured frame as a base64 data URL. The Electron main process MUST chain two Modal calls internally: first `POST /analysis/face-detection-file` (face gate), then `POST /analysis/enroll-file` (embedding registration). The IPC call returns `{ ok: boolean, error?: { code: string } }` to the renderer.
- **FR-009a**: If `face-detection-file` returns no face detected, the main process MUST return `{ ok: false, error: { code: "NO_FACE_DETECTED" } }` without calling `enroll-file`. The renderer MUST show an inline error ("No face detected — adjust your position and try again") and resume the live feed.
- **FR-010**: If enrollment (`POST /analysis/enroll-file`) fails for any reason (no face detected, endpoint unreachable, error response), the page MUST display an error pill ("Verification failed — please retake your photo"), discard the captured image, return to the live webcam feed, and NOT navigate forward.
- **FR-010a**: The face-recognition service MUST NOT perform a hardcoded warmup pre-call on `startService`; the Modal endpoint is warmed by the enrollment call from the Identity Verification page.
- **FR-010b**: When the exam session ends (submit success) OR when the student navigates back to home (logout, "Back to Home" button), the system MUST call `POST /analysis/unenroll` with the `session_id` to clear the server-side face embedding. This call covers all exit paths from the exam.
- **FR-011**: If no reference image has been captured for the current session, the exam page MUST redirect the student back to the Identity Verification page rather than allowing the exam to begin.
- **FR-012**: The page design MUST follow the Ethereal Authority design system: soft minimalism, glassmorphism overlay on the video, corner-accent frame indicators, and the three-column quality checklist, as specified in `Designs/Identity_Verification_Page/`.

### Key Entities

- **ReferenceImage**: A captured JPEG from the student's webcam. Attributes: `sessionId`, `capturedAt` (timestamp), `dataUrl` (base64 data URL). Stored in-memory in the Electron main process solely for transmission to `POST /analysis/enroll-file`. After successful enrollment the embedding lives on the Modal server; the local copy can be discarded (though retaining it for retake UX is acceptable).
- **Enrollment**: The act of calling `POST /analysis/enroll-file` with the student's `session_id` and reference image. On success, Modal caches the ArcFace embedding server-side. Subsequent verify calls (`POST /analysis/verify-file`) need only `session_id` + live `frame`.
- **ExamSession**: Already exists. Extended to carry `enrollmentSucceeded: boolean` so the exam page can enforce the redirect gate (FR-011). Replaces the previously proposed `referenceImageCaptured` flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A student can complete the identity verification step — from page load to confirmed capture — in under 60 seconds under normal lighting conditions.
- **SC-002**: The capture button correctly enables and disables within 1 second of a face entering or leaving the frame.
- **SC-003**: 100% of face-recognition prediction requests during an exam session include both the student's reference image and the live frame (verifiable in session JSONL logs).
- **SC-004**: Zero face-recognition prediction calls use the hardcoded 1×1 JPEG warmup image after this feature is implemented.
- **SC-005**: The exam page successfully blocks entry (redirecting to identity verification) when no reference image has been captured for the current session.
- **SC-006**: The reference image is automatically discarded when the exam session ends or the student logs out — never persisted to disk.

## Assumptions

- The student has a functioning front-facing camera and has granted browser-level camera permissions before reaching this page; the app's existing webcam access pattern (used in AI Readiness and Exam pages) applies here.
- The Modal face-recognition endpoint (`/analysis/verify-file`) accepts a `reference` file field in addition to the existing `frame` field. If the endpoint does not yet support this, a backend change to the Modal app is in scope.
- One reference image per exam session is sufficient; re-enrollment across questions is out of scope.
- Image quality analysis (lighting, focus) is done client-side using basic heuristics (brightness for lighting, face-detection availability for face presence); a dedicated focus/blur metric is a best-effort approximation.
- Mobile support and tablet optimization are out of scope for this feature.
- The reference image is stored exclusively in the Electron main-process memory (same pattern as `examSession`); it is never written to `sessions/*.jsonl` or any persistent file.
