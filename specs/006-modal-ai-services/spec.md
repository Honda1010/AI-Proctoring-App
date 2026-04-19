# Feature Specification: Modal AI Services

**Feature Branch**: `006-modal-ai-services`
**Created**: 2026-04-19
**Status**: Draft

## Context
Deploy GPU-accelerated AI services to Modal (Face Recognition and Object Detection) to improve performance and offload computation from the student's machine. These services must integrate with the existing `router.py` IPC bridge and emit events matching the `DetectionEvent` schema.

## User Scenarios & Testing

### User Story 1 - AI Detection in the Cloud
The AI bridge routes frames to Modal-hosted services instead of local stubs. Detection results are returned in real-time.

**Acceptance Scenarios**:
1. **Given** the Object Detection service is started, **When** a frame is sent to the bridge, **Then** the bridge calls the Modal endpoint and returns a `DetectionEvent` with detected objects.
2. **Given** the Face Recognition service is started, **When** a frame is sent to the bridge, **Then** the bridge calls the Modal endpoint and returns a `DetectionEvent` with match status.

### User Story 2 - Cold Start Handling
If the Modal container is not warm, the app receives a `service_unavailable` state instead of timing out or crashing.

**Acceptance Scenarios**:
1. **Given** a Modal service is cold, **When** a request is made, **Then** the client returns an error payload after a short timeout, and the router emits a `serviceError` notification.

## Requirements

### Functional Requirements
- **FR-001**: Implement `python_bridge/services/face_recognition_modal.py` and `python_bridge/services/object_detection_modal.py` as Modal-deployable scripts.
- **FR-002**: Implement `python_bridge/modal_client.py` to handle async communication with Modal web endpoints/functions using `httpx` or `aiohttp`.
- **FR-003**: The Modal client MUST handle authentication using tokens stored in `config.json`.
- **FR-004**: The client MUST return a specific `DetectionEvent` or error payload when a Modal cold start exceeds a defined threshold (e.g., 5 seconds).
- **FR-005**: The `router.py` interface MUST remain unchanged; it should simply instantiate the new Modal-backed service classes instead of the local stubs.

### Non-Functional Requirements
- **NFR-001**: Latency for a warm Modal request should ideally be under 500ms (network + inference).
- **NFR-002**: Modal secret management must be used for any sensitive keys on the server side.
- **NFR-003**: The system MUST support a frame processing rate of 5 FPS (High fidelity).

## Clarifications

### Session 2026-04-19

- Q: What is the target sampling frequency (FPS) for frames sent to Modal? → A: 5 FPS (High fidelity, high cost).
- Q: If a Modal cold start exceeds 5 seconds, should the bridge emit a serviceError and skip that frame, or should it block and retry until the service is warm? → A: Block and retry until service is warm.
- Q: How should Modal service scaling be configured? → A: Fixed scaling (1-1) — limit to one appropriate container per service per student.
- Q: Should the bridge explicitly "pre-warm" the Modal service? → A: Trigger on startService — call endpoint once upon service start to initiate warming.
- Q: How should the Modal bridge client authenticate with the Modal web endpoints? → A: JSON body token — token included in the request body.

## Assumptions
- The student has a stable internet connection for cloud AI features.
- Modal API keys and app names are correctly configured in `config.json`.
- `python_bridge/router.py` is the only entry point for AI requests.

## Out of Scope
- Local fallback if Modal is down (Phase 3).
- Fine-tuning models (Phase 2 uses off-the-shelf or pre-trained models).
- UI/UX indicators for "Cloud AI" status.
