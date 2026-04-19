# Feature Specification: Local AI Services

**Feature Branch**: `007-local-ai-services`
**Created**: 2026-04-19
**Status**: Draft

## Context
Integrate Eye Gaze Detection and Speech Detection as local in-process services. Unlike the cloud-based services from Phase 2, these services run entirely on the student's machine, processing webcam frames and microphone audio in real-time. They must follow the same `DetectionEvent` contract and integrate with the async `router.py`.

## User Scenarios & Testing

### User Story 1 - Local Eye Gaze Tracking
The system tracks the student's eye gaze locally using the webcam. If the student looks away from the screen for an extended period, a detection event is emitted.

**Acceptance Scenarios**:
1. **Given** the Eye Gaze service is started, **When** the student is looking at the screen, **Then** the service emits `DetectionEvent`s with gaze coordinates and high confidence.
2. **Given** the Eye Gaze service is started, **When** the student looks away, **Then** the service emits `DetectionEvent`s reflecting the "away" status.

### User Story 2 - Local Speech Detection
The system monitors the student's microphone. If speech or suspicious audio is detected, an event is emitted.

**Acceptance Scenarios**:
1. **Given** the Speech Detection service is started, **When** the room is quiet, **Then** the service emits no events or events with low "is_speech_detected" confidence.
2. **Given** the Speech Detection service is started, **When** the student speaks or a second voice is heard, **Then** the service emits a `DetectionEvent` with `is_speech_detected: true`.
## Requirements

### Functional Requirements
- **FR-001**: Implement `python_bridge/services/eye_gaze_local.py` using OpenCV for webcam capture and a local gaze estimation model.
- **FR-002**: Implement `python_bridge/services/speech_local.py` using `pyaudio` or `sounddevice` for microphone capture and a local speech detection model (e.g., WebRTC VAD or a simple energy-based detector for this phase).
- **FR-003**: Both services MUST run their capture and inference loops in background threads to avoid blocking the `router.py` event loop.
- **FR-004**: Both services MUST emit `DetectionEvent` objects via a callback or queue that the router can then broadcast to `stdout`.
- **FR-005**: Services MUST be startable and stoppable independently via the router's JSON-RPC interface.
- **FR-006**: If hardware access (webcam or microphone) fails upon service start or during operation, the service MUST emit a `serviceError` notification and transition to a `stopped` state.

## Clarifications

### Session 2026-04-19

- Q: What should happen if a local service cannot access the required hardware (e.g., webcam or microphone in use by another app)? → A: Emit `serviceError` notification and transition service to `stopped` state.
- Q: For Eye Gaze tracking, should the local service store captured webcam frames on disk, or should they be processed entirely in-memory and discarded? → A: Processed entirely in-memory and discarded immediately (No storage).
- Q: What should be the minimum duration of audio (in seconds) required to trigger a "speech detected" event? → A: 5.0 seconds — provide broad detection windows to reduce transient noise.
- Q: Should Eye Gaze and Speech Detection be allowed to run simultaneously on the local machine? → A: Yes — support parallel execution of both local services.
- Q: To keep stdout traffic manageable, should Eye Gaze and Speech Detection emit events only when a state change is detected? → A: Yes — emit events on state change only (e.g., when the student looks away or speech starts/stops).

## Assumptions
### Non-Functional Requirements
- **NFR-001**: CPU usage for local services should be minimized to ensure the exam application remains responsive.
- **NFR-002**: Eye gaze detection should target at least 5 FPS for smooth tracking (configurable).
- **NFR-003**: Audio processing should have a latency of less than 1 second from capture to event emission.
- **NFR-004**: Speech detection MUST use a minimum aggregation window of 5.0 seconds before emitting a "speech detected" event to filter out transient noise.

## Assumptions
- The student's machine has a working webcam and microphone.
- The machine has sufficient CPU resources to run two lightweight AI models locally.
- Required Python libraries (OpenCV, PyAudio) can be installed on the target OS.

## Out of Scope
- Detailed gaze-based anti-cheat logic (Phase 4).
- High-fidelity speech-to-text (Phase 3 only detects presence of speech).
- Multi-camera or multi-mic support.
