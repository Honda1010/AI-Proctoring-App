# Feature Specification: AI Frontend — Dashboard & Session Report

**Feature Branch**: `009-ai-frontend`
**Created**: 2026-04-19
**Status**: Draft

## Context
The application now has a robust AI proctoring backend that emits detections, alerts, and risk scores. This phase focuses on surfacing these signals to the user (and proctors) via a live dashboard during the exam and a detailed session report afterwards.

## User Scenarios & Testing

### User Story 1 - Live Monitoring Dashboard
During an active exam, the student sees a side panel (the dashboard) that confirms the AI proctoring services are active and running correctly.

**Acceptance Scenarios**:
1. **Given** the Exam page is active, **When** the Eye Gaze service is started, **Then** the "Eye Gaze" status in the dashboard changes from "Stopped" to "Running".
2. **Given** an active proctoring session, **When** a "GAZE_OFF_SCREEN" alert is received, **Then** it appears at the top of the Alert Panel with a timestamp.
3. **Given** a high-severity alert is received, **When** it is rendered, **Then** its card background or border is highlighted red.
4. **Given** the Risk Score changes in the backend, **When** a `riskScore` notification is received, **Then** the visual risk meter (gauge or progress bar) updates its value and color (e.g., green to yellow to red).

### User Story 2 - Post-Session Report
After the exam ends, the student (or an auditor) can review the proctoring performance and any flagged violations.

**Acceptance Scenarios**:
1. **Given** the Result page is completed, **When** the user navigates to the Session Report, **Then** the app loads the session's JSONL log file.
2. **Given** a session log is loaded, **When** rendered, **Then** a timeline view shows every detection and alert in chronological order.
3. **Given** the Session Report view, **When** the "Export PDF" button is clicked, **Then** the current report view is saved as a PDF file on the local machine.
## Requirements

### Functional Requirements
- **FR-001**: Implement a **Live Dashboard Component** in the `exam` page sidebar.
- **FR-002**: The Dashboard MUST display the real-time status (`running`, `stopped`, `error`) for: Eye Gaze, Speech Detection, Face Recognition, and Object Detection.
- **FR-003**: Implement a **Risk Score Gauge** (semi-circular needle gauge) that visualizes the 0–100 score in real-time.
- **FR-004**: Implement an **Alert Feed** that displays a scrollable list of the last 20 `AlertEvent` objects.
- **FR-005**: Implement a **Session Report Page** (`frontend/pages/session-report/`).
- **FR-006**: The Session Report MUST parse the `.jsonl` file associated with the session ID.
- **FR-007**: Implement a **Timeline View** (vertical chronological list) in the report that displays raw detections (minimized) and alerts (expanded).
- **FR-008**: Implement **PDF Export** using Electron's `webContents.printToPDF()` or similar native method.
- **FR-009**: The Result page MUST include a "View Full Proctoring Report" button that navigates to the Session Report page for the current attempt.

## Clarifications

### Session 2026-04-19

- Q: How should the user primarily access the Session Report? → A: A "View Full Proctoring Report" button on the Result page.
- Q: What visual style should be used for the Risk Score Gauge? → A: Semi-circular Gauge (Needle movement).
- Q: How should events be visualized in the Session Report timeline? → A: Vertical Timeline (Top to bottom, chronological).
- Q: What feedback should the user receive after a successful PDF export? → A: System Toast (Notification banner).

## Assumptions
### Non-Functional Requirements
- **NFR-001**: Dashboard updates MUST occur within 100ms of receiving an IPC notification to maintain the "live" feel.
- **NFR-002**: Large session logs (e.g., 5000+ lines) MUST be loaded efficiently using streaming or virtualized lists if necessary.
- **NFR-003**: The Session Report MUST be printable to a single-column PDF that preserves the visual severity of alerts.

## Assumptions
- The `sessions/` directory contains JSONL files named `<sessionId>.jsonl`.
- The `mainWindow` in `main.js` will manage the file system access for reading logs.
- The `ai-service-contract.json` is the source of truth for event schemas.

## Out of Scope
- Interactive video playback synchronized with the timeline (Phase 10).
- Remote proctor chat.
- Advanced statistical analytics (beyond simple counts).
