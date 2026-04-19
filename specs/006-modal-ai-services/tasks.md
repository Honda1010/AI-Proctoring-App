# Tasks: Modal AI Services

**Feature**: `006-modal-ai-services`
**Date**: 2026-04-19

---

## Phase 1: Setup
- [x] T001 Add `modal` and `httpx` to `python_bridge/requirements.txt`
- [x] T002 Update `config.example.json` with Modal endpoint placeholders

---

## Phase 2: Modal Server-Side Implementation
- [x] T003 [P] Create `python_bridge/services/face_recognition_modal.py`
- [x] T004 [P] Create `python_bridge/services/object_detection_modal.py`

---

## Phase 3: Bridge Client Implementation
- [x] T005 Implement `python_bridge/modal_client.py` for async communication
- [x] T006 Add cold-start error mapping to `modal_client.py`

---

## Phase 4: Integration
- [x] T007 Refactor `python_bridge/face_recognition.py` to use `ModalClient`
- [x] T008 Refactor `python_bridge/object_detection.py` to use `ModalClient`
- [x] T009 Verify that `router.py` correctly handles the new service implementations

---

## Phase 5: Testing
- [x] T010 Create `python_bridge/test_modal_client.py` with mocked Modal responses
- [x] T011 Run full test suite with `py -m pytest`
