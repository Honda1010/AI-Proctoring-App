# Implementation Plan: Local AI Services

**Branch**: `007-local-ai-services`
**Spec**: [spec.md](spec.md)

## Summary
Implement Eye Gaze and Speech Detection as local services running in background threads within the Python bridge. These services will interact directly with the machine's webcam and microphone and communicate with the `router.py` through an asynchronous event mechanism.

## Technical Context
- **Language**: Python 3.11
- **Libraries**: `opencv-python` (webcam), `PyAudio` (microphone), `asyncio`
- **Threading**: Use `threading.Thread` for capture loops; use `asyncio.run_coroutine_threadsafe` to emit events back to the main loop.

## Implementation Steps

### Phase 1: Local Eye Gaze Service
1. Implement `python_bridge/services/eye_gaze_local.py`.
2. Add a capture loop using `cv2.VideoCapture`.
3. Integrate a lightweight gaze estimation model or library.
4. Implement a thread-safe way to send `DetectionEvent`s to the router.

### Phase 2: Local Speech Detection Service
1. Implement `python_bridge/services/speech_local.py`.
2. Add an audio capture stream using `PyAudio`.
3. Implement speech presence detection (VAD or energy-based).
4. Integrate with the router's event broadcast system.

### Phase 3: Router Integration
1. Update `router.py` to instantiate `EyeGazeService` and `SpeechDetectionService` from the new local modules instead of stubs.
2. Add support for a "broadcast" mechanism where background threads can push notifications to `stdout` without a direct JSON-RPC request.

### Phase 4: Polish & Config
1. Update `config.py` to support new local configuration fields.
2. Document all parameters in `config.example.json`.

## Verification
- Unit test capture loops with mocked device input.
- End-to-end test via JSON-RPC `startService` and observing `stdout` notifications.
