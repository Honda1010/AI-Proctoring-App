# Implementation Plan: Modal AI Services

**Branch**: `006-modal-ai-services`
**Spec**: [spec.md](spec.md)

## Summary
Build the cloud infrastructure for AI proctoring using Modal. This involves creating server-side Modal apps and a client-side library to bridge the local Python process with the cloud.

## Technical Context
- **Language**: Python 3.11
- **Cloud Platform**: Modal
- **Dependencies**: `modal`, `httpx`, `jsonschema`
- **Architecture**: Async client calling Modal web endpoints

## Implementation Steps

### Phase 1: Modal Server-Side
1. Create `python_bridge/services/face_recognition_modal.py` defining the Modal stub and endpoint.
2. Create `python_bridge/services/object_detection_modal.py` defining the Modal stub and endpoint.

### Phase 2: Bridge Client-Side
1. Implement `python_bridge/modal_client.py` using `httpx.AsyncClient`.
2. Map Modal response status codes (e.g., 503 for cold start) to `DetectionEvent` objects.

### Phase 3: Integration
1. Update `python_bridge/face_recognition.py` to use `ModalClient` instead of returning a mock.
2. Update `python_bridge/object_detection.py` to use `ModalClient` instead of returning a mock.
3. Ensure `router.py` remains unchanged but benefits from real detection data.

## Verification
- Unit test `ModalClient` with mocked responses.
- Deploy to Modal (staging) and verify with a test script.
