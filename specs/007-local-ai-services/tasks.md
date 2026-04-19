# Tasks: Local AI Services

**Feature**: `007-local-ai-services`
**Date**: 2026-04-19

---

## Phase 1: Setup
- [x] T001 Add `opencv-python` and `PyAudio` to `python_bridge/requirements.txt`
- [x] T002 Update `config.example.json` with local service parameters (FPS, chunk_size)
- [x] T003 Update `python_bridge/config.py` to parse new service configuration fields

---

## Phase 2: Local Eye Gaze Service
- [x] T004 Implement capture loop in `python_bridge/services/eye_gaze_local.py`
- [x] T005 Integrate local gaze estimation model (threaded)
- [x] T006 Implement async event callback for gaze detections

---

## Phase 3: Local Speech Detection Service
- [x] T007 Implement audio stream in `python_bridge/services/speech_local.py`
- [x] T008 Implement energy-based or VAD speech detection (threaded)
- [x] T009 Implement async event callback for speech detections

---

## Phase 4: Router Integration
- [x] T010 Update `router.py` to support background notification emission from threads
- [x] T011 Register new local services in `router.py` `service_classes`
- [x] T012 Verify `startService` and `stopService` lifecycle works for local modules

---

## Phase 5: Testing
- [x] T013 Create `python_bridge/test_local_services.py` with mocked camera/mic input
- [x] T014 Run full test suite with `py -m pytest`
