# Tasks: AI Frontend — Dashboard & Session Report

**Feature**: `009-ai-frontend`
**Date**: 2026-04-19

---

## Phase 1: IPC & Setup
- [x] T001 Update `main.js` to spawn `router.py` and capture its `stdout`
- [x] T002 Implement JSONL log retrieval in `main.js` (`bridge:get-session-log`)
- [x] T003 Implement PDF export bridge in `main.js` (`bridge:export-pdf`)
- [x] T004 Update `preload.js` with new AI-specific IPC channels
- [x] T005 Create `frontend/pages/session-report/` directory

---

## Phase 2: Live Dashboard (Exam Page)
- [x] T006 [P] Redesign `exam/index.html` proctoring panel to include Alert Feed and Risk Gauge
- [x] T007 Implement `DashboardController.js` to handle real-time IPC events
- [x] T008 Update `exam.js` to integrate `DashboardController`
- [x] T009 Add CSS for alert card severity states (low, medium, high)

---

## Phase 3: Session Report Page
- [x] T010 [P] Implement `session-report/index.html` with Timeline skeleton
- [x] T011 Implement `report.js` for JSONL parsing and summary computation
- [x] T012 Implement Timeline rendering logic (chronological event list)
- [x] T013 Implement PDF generation trigger and layout styles

---

## Phase 4: Integration & Polish
- [x] T014 Link Session Report from the Result page
- [x] T015 Add "View Report" button to Exam Code page (for completed sessions)
- [x] T016 Verify risk score gauge color transitions (green -> yellow -> red)
- [x] T017 Final end-to-end test with real AI bridge signals
