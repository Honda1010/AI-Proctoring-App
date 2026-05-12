# Feature Specification: Violation Clip Recording & Upload

**Feature Branch**: `013-violation-clip-upload`  
**Created**: 2026-05-05  
**Status**: Draft  
**Input**: User description: "We need to add a violation clip recording and upload feature to Lumina AI Proctoring. When the AI orchestrator detects a cheating violation during an active exam session, the system must automatically capture a video clip that provides forensic evidence for proctor review."

## Clarifications

### Session 2026-05-05

- Q: What is the exact lock model for capture windows? → A: Once a capture is triggered, the system is locked — no new capture window can start until the current clip is fully composed and uploaded. Violations during the lock are silently absorbed into the active clip's metadata.
- Q: When must the pre-violation buffer be populated? → A: Continuously at all times during an active exam session, before any violation occurs, so 10 seconds of footage is always available instantly on trigger with no delay.
- Q: Is the uploaded clip one file or two separate files (pre + post)? → A: One single continuous video file, composed by merging pre-buffer footage with post-violation footage before upload.
- Q: Do buffered footage chunks carry individual timestamps? → A: Yes — every second of buffered footage carries an ISO 8601 UTC timestamp at capture time; clip start and end timestamps are derived from real chunk timestamps, not estimated.
- Q: What is the uploaded filename convention? → A: `{studentId}/{captureStartTimestamp}_{primaryViolationType}.mp4` where captureStartTimestamp uses dashes instead of colons for URL safety, and primaryViolationType is the violation type that triggered the capture.
- Q: What is the format and derivation of the AI confidence score in the payload? → A: A float between 0.0 and 1.0, derived by dividing the orchestrator's integer risk score (0–100) by 100.
- Q: How should multiple violations be represented in the payload description? → A: An `allViolations` array contains all violations; the human-readable description summarizes them (e.g., "Phone detected in frame + 2 additional violations in clip").
- Q: What exactly happens when the exam session ends during an active capture window? → A: Force-finalize the clip immediately with whatever post-violation footage was collected up to that point, then upload normally.
- Q: What is the exact upload retry policy? → A: Retry once after 3 seconds. If the retry fails, log the failure and notify the frontend via a structured error event. Do not crash or hang.
- Q: Must temporary files be cleaned up after encoding/upload? → A: Yes — all temp files created during encoding or upload must be deleted after the operation completes, regardless of success or failure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Proctor Reviews Forensic Clip Evidence (Priority: P1)

A proctor investigating a suspected cheating incident needs to watch a short video clip showing exactly what happened at the moment a violation was flagged. The clip must show what led up to the violation so the proctor can judge intent, not just consequence.

**Why this priority**: The forensic clip is the primary deliverable of this feature. Without it, all other work is infrastructure with no user-visible value. This story proves the entire end-to-end pipeline is working.

**Independent Test**: Can be fully tested by triggering a violation during a test exam session, then navigating to the violation record in the proctor dashboard and verifying the linked video plays from a CDN URL showing the 10s before and 10s after the violation moment.

**Acceptance Scenarios**:

1. **Given** a student is taking an active exam, **When** the AI orchestrator detects a violation (e.g., looking away, phone detected, unauthorized speech), **Then** the system automatically begins recording a clip that includes at least 10 seconds of footage that preceded the violation moment.
2. **Given** a clip has been captured, **When** the upload process completes, **Then** the proctor can access the clip via a direct CDN-hosted URL without requiring any credentials or local file access.
3. **Given** the clip is accessible, **When** the proctor opens the violation record, **Then** they see structured metadata including: student ID, exam attempt ID, AI confidence score, a human-readable description of the detected behavior, and the full list of violations captured in the clip's time window.

---

### User Story 2 - System Deduplicates Rapid Violations into One Clip (Priority: P2)

Multiple AI signals can fire within seconds of each other during a single incident (e.g., a phone is detected at the same moment the student looks away). The system must treat all violations within the same 20-second capture window as a single event — not generate a flood of separate clip uploads.

**Why this priority**: Without deduplication, a single incident could produce dozens of redundant clips, overwhelming storage, clogging the backend, and confusing proctors with duplicate evidence.

**Independent Test**: Can be tested by simulating two or more violation events within a 20-second window during a test session and verifying only one clip is produced with all violations listed in its metadata.

**Acceptance Scenarios**:

1. **Given** a clip capture is already in progress (within its 20-second window), **When** a second violation is detected, **Then** no new clip capture is initiated and the second violation is appended to the in-progress clip's violation list.
2. **Given** a clip capture window has closed, **When** a new violation is detected, **Then** a fresh capture window is opened and a new clip is produced.
3. **Given** a clip capture completes with multiple violations, **When** the violation event is sent to the backend, **Then** the metadata payload includes all violation types, their individual confidence scores, and their timestamps within the clip window.

---

### User Story 3 - Credentials Are Never Exposed to the Frontend (Priority: P3)

An exam taker or a malicious actor inspecting the frontend application must never be able to extract cloud storage credentials from the client-side layer. All uploads must be performed exclusively by the backend process.

**Why this priority**: Credential exposure is a security vulnerability that could allow unauthorized uploads, storage exhaustion attacks, or data exfiltration. It must be architecturally enforced, not just policy-enforced.

**Independent Test**: Can be tested by inspecting all IPC messages, renderer-accessible APIs, and network requests from the frontend process and confirming no cloud credentials, signed URLs containing secrets, or storage tokens are ever transmitted to or accessible from the user-facing layer.

**Acceptance Scenarios**:

1. **Given** the frontend initiates or observes a clip upload, **When** the communication channel between frontend and backend is inspected, **Then** no cloud storage credentials, API keys, or pre-signed tokens exposing credentials are present in any message.
2. **Given** the backend is responsible for uploading, **When** an upload completes, **Then** only the resulting public CDN URL is returned to any frontend-accessible layer — never the credentials used to produce it.

---

### Edge Cases

- What happens when the 10-second pre-violation buffer has less than 10 seconds of footage (e.g., violation occurs 3 seconds after exam start)? → Clip captures whatever footage is available from the start of the session up to the violation moment, plus 10 seconds after.
- What happens when the cloud upload fails? → Retry once after 3 seconds. If the retry also fails, log the failure and notify the frontend layer via a structured error event; the violation event is still emitted to the backend with an `upload_failed` status so the record is not silently lost. The system must not crash or hang.
- What happens if the student's webcam feed is unavailable or frozen at the moment of violation? → The violation event is still emitted to the backend, but the clip is marked as unavailable with a reason code; no upload is attempted.
- What happens when two violations fire at exactly the same millisecond (e.g., from two different AI models returning simultaneously)? → Both violations are coalesced into the same locked capture window; only one clip is produced.
- What happens when an exam session ends while a clip capture window is still open? → The system force-finalizes the clip immediately with whatever post-violation footage was collected up to that point, then uploads normally; the lock is then released.
- What happens when the clip upload produces a URL but the backend event emission fails? → The system logs the orphaned URL and retries the backend emission; the clip is not discarded.
- What happens to temporary files created during encoding or upload? → All temp files must be deleted after the operation completes, regardless of whether it succeeded or failed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST automatically initiate a clip capture when the AI orchestrator emits a violation event during an active exam session.
- **FR-002**: The system MUST maintain a rolling pre-violation buffer continuously at all times during an active exam session — before any violation occurs — so that up to 10 seconds of recent footage is always available instantly when a violation is triggered, with no capture delay. The buffer is populated from the webcam stream and held entirely in memory.
- **FR-003**: The system MUST capture 10 seconds of footage following the violation moment (post-violation buffer), for a maximum clip duration of 20 seconds.
- **FR-004**: Once a clip capture is triggered, the system MUST enter a **locked** state for the duration of the capture (all 10 post-violation seconds collected) and upload. While locked, any additional violation events MUST be silently absorbed into the active clip's violation list — they MUST NOT trigger a new capture window and MUST NOT be discarded. The locked state is released only after the upload operation completes (succeeds or fails after retry).
- **FR-005**: Each clip MUST be assigned metadata at the time of capture, including: clip window start timestamp (UTC, derived from the first buffered chunk's real timestamp), clip window end timestamp (UTC, derived from the last captured chunk's real timestamp), student ID, exam attempt ID, an `allViolations` array containing all violations captured within the window (each entry with: violation type, confidence score as a float 0.0–1.0, and UTC timestamp), the AI confidence score for the primary (triggering) violation expressed as a float between 0.0 and 1.0 (derived by dividing the orchestrator's integer risk score 0–100 by 100), and a human-readable description summarizing all violations in the clip (e.g., "Phone detected in frame + 2 additional violations in clip" when multiple violations are present).
- **FR-006**: The system MUST automatically upload the completed clip to cloud storage upon capture completion, without any manual trigger from the user or proctor.
- **FR-007**: Cloud storage credentials MUST reside exclusively in the secure backend process and MUST NOT be transmitted to or accessible from the frontend (renderer) process under any circumstances.
- **FR-008**: Upon successful upload, the system MUST obtain a publicly accessible CDN-hosted URL for the clip and include it in the violation event payload.
- **FR-009**: The system MUST emit a structured violation event to the backend API after a successful upload, associating the clip URL and all metadata with the correct student ID and exam attempt ID.
- **FR-010**: If a cloud upload fails, the system MUST retry exactly once after a 3-second delay. If the retry also fails, the upload MUST be marked as failed and the system MUST log the failure. The system MUST NOT crash or hang on upload failure.
- **FR-011**: After upload failure (both attempts exhausted), the system MUST notify the frontend layer via a structured error event AND still emit a violation event to the backend with an `upload_failed` status so the violation record is preserved even without a clip URL.
- **FR-012**: If the webcam feed is unavailable at the time of violation, the system MUST emit the violation event with a `clip_unavailable` status and a reason code, and MUST NOT attempt an upload.
- **FR-013**: If the locked capture window is active when an exam session ends, the system MUST immediately force-finalize the clip with whatever post-violation footage was collected up to that point (even if less than 10 seconds), then proceed with upload normally. The locked state is released after the upload completes.
- **FR-014**: The structured violation event payload MUST conform to the existing backend API contract for violation records.
- **FR-015**: The final uploaded clip MUST be a single continuous video file composed by merging the pre-buffer footage with the post-violation footage before upload. The system MUST NOT upload two separate files (pre and post) for the same violation clip.
- **FR-016**: Every second of footage held in the rolling buffer MUST carry an ISO 8601 UTC timestamp recorded at the moment that chunk was captured. Clip start and end timestamps in metadata MUST be derived from these real chunk timestamps, not estimated or calculated from wall-clock time at upload.
- **FR-017**: The uploaded file MUST be named following the pattern `{studentId}/{captureStartTimestamp}_{primaryViolationType}.mp4`, where `captureStartTimestamp` is the ISO 8601 UTC start timestamp of the clip window with colons replaced by dashes (to ensure URL safety), and `primaryViolationType` is the violation type of the event that originally triggered the capture.
- **FR-018**: All temporary files created during clip composition, encoding, or upload preparation MUST be deleted after the upload operation completes, regardless of whether the upload succeeded or failed.

### Key Entities

- **ViolationClip**: Represents a single recorded video segment associated with one or more violations. Key attributes: clip ID, exam attempt ID, student ID, capture window start (UTC), capture window end (UTC), CDN URL (nullable until upload succeeds), upload status (pending / success / failed / unavailable), reason code (nullable).
- **ViolationEvent**: An individual violation signal produced by an AI model. Key attributes: violation type, confidence score, UTC timestamp, human-readable description. Multiple ViolationEvents can be associated with one ViolationClip.
- **ClipMetadataPayload**: The structured data packet emitted to the backend after upload. Contains: student ID, exam attempt ID, CDN URL (nullable on failure), primary AI confidence score (float 0.0–1.0), human-readable description summarizing all violations in the clip, `allViolations` array of all ViolationEvents captured within the clip window, upload status (`pending` / `success` / `upload_failed` / `clip_unavailable`).
- **RollingBuffer**: An in-memory pre-violation footage buffer maintained continuously at all times during an active exam session, before any violation occurs. Holds up to 10 seconds of the most recent footage chunks, each tagged with an ISO 8601 UTC timestamp at the moment of capture. Never persisted to disk; discarded when the exam session ends.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of detected violations during active exam sessions result in either a clip upload or an explicit failure record — no violation is silently dropped.
- **SC-002**: A clip covering the correct 20-second window (±1 second tolerance) is produced for every successfully captured violation.
- **SC-003**: Clip upload completes and a CDN URL is available within 30 seconds of the violation moment under normal network conditions.
- **SC-004**: Zero cloud storage credentials are accessible from the frontend process — verifiable by automated inspection of IPC message logs.
- **SC-005**: When two or more violations occur within a single 20-second window, exactly one clip is produced and all violations are present in its metadata — no duplicate clips for the same window.
- **SC-006**: The violation event reaches the backend within 5 seconds of the CDN URL becoming available.
- **SC-007**: The single-retry mechanism (one retry after 3 seconds) successfully recovers from transient upload failures in at least 80% of cases where the failure is not permanent (e.g., brief network blip).
- **SC-008**: After any upload operation (success or failure), zero temporary files remain on disk — verifiable by inspecting the temp directory before and after a test capture cycle.
- **SC-009**: The uploaded filename for every clip conforms exactly to the pattern `{studentId}/{captureStartTimestamp}_{primaryViolationType}.mp4` with URL-safe timestamps — verifiable by inspecting cloud storage keys after a test upload.

## Assumptions

- The AI orchestrator already emits discrete, typed violation events with confidence scores and timestamps — this feature consumes those events and does not change how they are generated.
- A webcam feed is accessible as a continuous stream during an active exam session; the rolling pre-violation buffer is populated from this stream.
- The backend API has (or will have) an endpoint that accepts the ClipMetadataPayload structure for recording violation evidence against an exam session.
- Cloud storage provisioning (bucket/container setup, CDN configuration) is handled as infrastructure and is out of scope for this feature specification.
- The identity of the cloud storage provider is an implementation detail; the specification is provider-agnostic.
- Video encoding format and resolution are implementation details, subject to the constraint that the resulting file must be streamable from a CDN URL in a standard web browser.
- The rolling pre-violation buffer is held entirely in memory and is never written to the local disk during normal operation.
- Multi-monitor or multi-camera capture is out of scope for this feature; only the primary webcam feed is captured.
- The proctor-facing dashboard that displays the CDN URL is an existing system; this feature only populates the data it consumes.
