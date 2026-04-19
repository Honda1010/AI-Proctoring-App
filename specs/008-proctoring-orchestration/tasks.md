# Tasks: Proctoring Orchestration Layer

**Feature**: `008-proctoring-orchestration`
**Date**: 2026-04-19

---

## Phase 1: Core Setup
- [x] T001 Create `python_bridge/orchestrator.py` skeleton
- [x] T002 Implement thread-safe JSONL logger for session files
- [x] T003 Update `python_bridge/config.py` to parse orchestration config

---

## Phase 2: Rule Engine Implementation
- [x] T004 Implement time-based rule logic for `MissingFaceRule`
- [x] T005 Implement state-based rule logic for `OffScreenGazeRule`
- [x] T006 Implement immediate rule logic for objects and speech
- [x] T007 Add JSON schema validation for alert rules in `specs/alert-rules-schema.json`

---

## Phase 3: Risk Scorer Implementation
- [x] T008 Implement weighted score calculation
- [x] T009 Implement score decay logic
- [x] T010 Add periodic `riskScore` update emission

---

## Phase 4: Integration
- [x] T011 Wire Orchestrator into `router.py` (all entry points)
- [x] T012 Ensure `alert` events are correctly serialized to JSON-RPC stdout
- [x] T013 Verify session logs are correctly generated in `sessions/`

---

## Phase 5: Testing
- [x] T014 Unit tests for individual rules
- [x] T015 Unit tests for risk score aggregation
- [x] T016 Integration test: simulate session and verify log + alert emission
