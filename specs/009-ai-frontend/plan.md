# Implementation Plan: AI Frontend — Dashboard & Session Report

**Branch**: `009-ai-frontend`
**Spec**: [spec.md](spec.md)

## Summary
Implement the real-time proctoring dashboard and the post-session report view. This involves connecting the Electron renderer to the JSON-RPC stream from the Python bridge and providing a high-fidelity visualization of risk signals.

## Technical Context
- **Framework**: Vanilla JS / HTML / CSS (matching existing pages).
- **IPC**: Extend `main.js` and `preload.js` to pipe JSON-RPC messages from `router.py` to the renderer.
- **Visuals**: Use SVG for the risk gauge and standard CSS for the alert feed and timeline.
- **Export**: Use Electron's `printToPDF` API for generating the session report.

## Implementation Steps

### Phase 1: IPC Plumbing
1. Update `main.js` to spawn `python_bridge/router.py` alongside `server.py`.
2. Implement a listener for `router.py`'s `stdout` in `main.js`.
3. Parse incoming JSON lines and forward `detection`, `alert`, and `riskScore` notifications to the renderer via a new `bridge:ai-event` channel.
4. Add `bridge:ai-event` to the whitelist in `preload.js`.

### Phase 2: Live Dashboard (Exam Page)
1. Update `frontend/pages/exam/index.html` to include a dedicated proctoring status area and alert feed.
2. Implement `DashboardController` in `exam.js`:
   - Listens for `bridge:ai-event`.
   - Updates the status indicators for the four AI services.
   - Updates the Risk Score SVG gauge.
   - Appends new alerts to the `AlertFeed` DOM element.
3. Add styles to `exam.css` for alert cards and severity highlighting.

### Phase 3: Session Report Page
1. Create `frontend/pages/session-report/index.html`, `report.js`, and `report.css`.
2. Implement `ReportController`:
   - Fetches the session log via `bridge:get-session-log`.
   - Parses the JSONL data and computes summary statistics (total alerts, duration).
   - Renders a vertical **Timeline Component** showing all proctoring events.
3. Implement the **Export PDF** button:
   - Triggers `bridge:export-pdf` with the report's session ID.
   - Main process uses `printToPDF` and saves the file.

### Phase 4: Polish & Integration
1. Ensure the Result page includes a link to the Session Report.
2. Verify all design tokens are used correctly for consistency.
3. Test with a mock session log containing 1000+ entries to ensure performance.

## Verification
- **Automated**: Unit tests for the JSONL parsing logic in `report.js`.
- **Manual**: Run an exam session, look away from the camera, and verify the "GAZE_OFF_SCREEN" alert appears in the dashboard and later in the report.
