# Tasks: AI Service Bridge Layer

**Feature**: `ai-bridge` | **Branch**: `005-result-page` (current) | **Date**: 2026-04-19

---

## Phase 1: Setup

- [x] T001 Create `specs/ai-service-contract.json` with the DetectionEvent schema
- [x] T002 Create `specs/ipc-protocol.md` with the JSON-RPC 2.0 transport documentation
- [x] T003 Update `python_bridge/requirements.txt` to include `jsonschema` and `pytest`

---

## Phase 2: Core Implementation

- [x] T004 Create `python_bridge/ai_base.py` for the service interface
- [x] T005 Implement `python_bridge/eye_gaze.py` stub
- [x] T006 Implement `python_bridge/object_detection.py` stub
- [x] T007 Implement `python_bridge/face_recognition.py` stub
- [x] T008 Implement `python_bridge/speech_detection.py` stub
- [x] T009 Refactor `python_bridge/router.py` to use `jsonschema` for validating detection events before sending them to stdout

---

## Phase 3: Validation & Testing

- [x] T010 Convert `python_bridge/test_router.py` to use `pytest`
- [x] T011 Add tests for `jsonschema` validation in `test_router.py`
- [x] T012 Verify all tests pass with `py -m pytest python_bridge/test_router.py`
