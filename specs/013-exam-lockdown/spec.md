# Feature Specification: Exam Lockdown

**Feature Branch**: `013-exam-lockdown`
**Created**: 2026-05-07
**Status**: Draft

## Clarifications

### Session 2026-05-07

- Q: If a violation is detected and the student dismisses the modal, does the blocking modal re-appear on the next detection cycle if the violation still exists? → A: Yes — re-show the modal on every 60-second check cycle while the violation persists. Each detection event is an independent log entry. Dismissal is an acknowledgement only, not a resolution.
- Q: When the student dismisses a violation modal, does interaction resume immediately or only after a re-check passes? → A: Immediately — exam interaction resumes on dismiss with no re-check triggered. The next 60-second periodic check handles re-detection.
- Q: When the app re-enters fullscreen after an OS-forced exit, should a visible indicator be shown to the student, or should it happen silently? → A: Silent re-entry (no student-facing message), but log a `FULLSCREEN_ESCAPE_ATTEMPT` alert to the session JSONL for the proctor's audit trail.
- Q: What is the timeout per individual subprocess call inside the environment check (WMIC, netstat, registry, process listing) before it is abandoned and treated as non-detection? → A: 3 seconds per subprocess call. A timed-out call is treated as clean (non-detection), consistent with silent failure behaviour.
- Q: If `setFullScreen(true)` fails when re-entering fullscreen after an OS-forced exit, should the app retry or make a single best-effort attempt? → A: Single best-effort attempt only — no retry loop. If the call fails, the subsequent leave-full-screen event acts as an implicit retry.

1. **Platform scope**: Windows-only. macOS and Linux are explicitly out of scope.
2. **Lockdown activation boundary**: All four lockdown concerns activate the moment `examSession` is set (exam start) and deactivate on all three exit paths: successful submission, logout, and back-to-home. No other activation trigger exists.
3. **Violation response**: Detected violations (VM, RDP, screen capture) trigger a blocking modal and are logged; they do not auto-terminate the exam. The proctor reviews logs post-exam.
4. **Detection cadence**: Environment checks run once at exam start and every 60 seconds thereafter — the same cadence for both VM/RDP and screen-capture checks.
5. **Shortcut-blocking failure handling**: If an OS-level shortcut registration fails (e.g., the OS has reserved the key), the failure is silently ignored and the remaining shortcuts are still registered.

## User Scenarios & Testing

### User Story 1 — Fullscreen Enforcement (Priority: P1)

A student starts an exam and the app enters kiosk fullscreen mode. The window has no title bar, no borders, and no OS chrome. The student cannot minimize, resize, move, or close the window. If the OS somehow forces the app out of fullscreen (e.g., multi-monitor gesture), the app detects this and immediately re-enters fullscreen.

**Why this priority**: Without fullscreen enforcement, all other lockdown controls are irrelevant — the student can simply move the window aside and use other applications freely.

**Independent Test**: Launch the app, start an exam session, and attempt to minimize, resize, move, press Alt+F4, and switch windows via OS taskbar — all must fail with no effect. Confirm the window is always-on-top and fills the screen.

**Acceptance Scenarios**:

1. **Given** an exam session becomes active, **When** the exam page loads, **Then** the window is frameless, fullscreen, always-on-top, non-resizable, non-movable, and non-minimizable.
2. **Given** an exam session is active, **When** the student attempts to close the window (Alt+F4 or OS close gesture), **Then** the close action is cancelled silently and the window remains open.
3. **Given** an exam session is active, **When** the OS forces the app out of fullscreen (multi-monitor gesture or OS override), **Then** the app re-enters fullscreen within one second.
4. **Given** no exam session is active (Login or Exam-Code pages), **When** the student closes the window, **Then** the app closes normally.
5. **Given** a successful exam submission clears the session, **When** the student closes the window, **Then** the app closes normally.

---

### User Story 2 — Keyboard Shortcut Blocking (Priority: P1)

During an exam, a student pressing shortcuts to copy content, switch apps, open developer tools, or take screenshots finds that every such shortcut is silently ignored — no clipboard data is set, no other app comes to focus, no DevTools panel opens.

**Why this priority**: Keyboard shortcuts are the most accessible cheating vector and require zero additional tools. Blocking them is a prerequisite for all other controls.

**Independent Test**: Start an exam session and press each blocked shortcut individually (Alt+Tab, Ctrl+C, PrintScreen, Win+Shift+S, etc.) — none must produce any observable effect. End the exam and verify all shortcuts function normally again.

**Acceptance Scenarios**:

1. **Given** an exam session is active, **When** the student presses Alt+Tab, Alt+F4, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+A, Ctrl+W, Win+D, Win+L, Ctrl+Shift+Esc, F11, Escape, Ctrl+Shift+I, PrintScreen, Alt+PrintScreen, Win+PrintScreen, or Win+Shift+S, **Then** the shortcut is silently consumed with no visible effect.
2. **Given** an exam session is active, **When** the student presses F12, **Then** the developer tools panel does not open.
3. **Given** no exam session is active, **When** the student presses F12, **Then** the developer tools open normally (development behaviour is preserved outside exams).
4. **Given** an exam session ends via submission, logout, or back-to-home, **When** the student presses any previously blocked shortcut, **Then** it functions normally.

---

### User Story 3 — Virtual Machine and Remote Desktop Detection (Priority: P2)

When a student runs the exam inside a virtual machine or with remote desktop software active, the app detects this at exam start and every 60 seconds, logs the violation to the session record, and displays a blocking warning modal. The student must dismiss the modal before continuing.

**Why this priority**: Virtual machines and remote desktop tools allow a third party to observe or control the student's screen, defeating all visual lockdown controls.

**Independent Test**: Run the app inside a VM (e.g., VirtualBox), start an exam session, and verify a blocking modal appears within the first check and a `VIRTUAL_ENVIRONMENT` alert entry appears in the session JSONL log.

**Acceptance Scenarios**:

1. **Given** an exam session starts on a VM, **When** the first environment check runs, **Then** a blocking modal displays a warning and the session log records a `VIRTUAL_ENVIRONMENT` alert with the detected reason.
2. **Given** an exam session is active on a clean machine, **When** the student launches a remote desktop tool (e.g., TeamViewer, AnyDesk) mid-exam, **Then** the next 60-second check detects the running process and displays the blocking modal.
3. **Given** the blocking modal is shown, **When** the student dismisses it, **Then** exam interaction resumes and the session log already contains the alert (no data is lost on dismiss).
4. **Given** an exam session is active on a clean machine with no VM or remote desktop tools, **When** the periodic check runs, **Then** no modal is displayed and the exam continues uninterrupted.
5. **Given** the exam ends via any exit path, **When** the next check interval elapses, **Then** the periodic timer has been cancelled and no check runs.

---

### User Story 4 — Screenshot and Screen Capture Blocking (Priority: P2)

When a student attempts to screenshot or record the exam window — via keyboard shortcut, OS tool, or a third-party capture application — the attempt is either silently blocked or produces a blank/black capture. Detected capture applications trigger a logged violation and a blocking modal.

**Why this priority**: Screen capture is a direct path to exfiltrating exam questions and answers for use by a third party.

**Independent Test**: Start an exam session, press PrintScreen and Win+Shift+S — the clipboard must contain nothing or a blank frame. Use the OS Snipping Tool — the app window must render as black. Launch ShareX or OBS — a blocking modal must appear.

**Acceptance Scenarios**:

1. **Given** an exam session is active, **When** the student presses PrintScreen, Alt+PrintScreen, Win+PrintScreen, or Win+Shift+S, **Then** the shortcut is silently consumed and the clipboard is not updated with exam content.
2. **Given** an exam session is active, **When** any OS screenshot tool captures the screen, **Then** the exam window renders as a black/blank surface in the captured image.
3. **Given** a screen-capture process (e.g., ShareX, OBS64) is running at exam start, **When** the first environment check runs, **Then** a blocking modal appears and a `SCREEN_CAPTURE_DETECTED` alert is written to the session log.
4. **Given** the student launches a screen-capture tool mid-exam, **When** the next 60-second check fires, **Then** the modal is shown and the alert is logged.
5. **Given** the exam session ends via any exit path, **When** the student uses OS screenshot tools, **Then** the app window is capturable normally.

---

### Edge Cases

- What happens if a shortcut registration fails at the OS level (key already reserved by OS)? The registration failure is silently ignored; the remaining shortcuts in the blocked list are still registered.
- What happens if the environment check endpoint is unreachable (Python bridge not running)? The check fails silently — no modal is shown, no alert is logged, exam continues uninterrupted.
- What happens if a student uses two monitors? The window remains fullscreen on the primary monitor and cannot be moved or repositioned.
- What happens if both a VM environment and a screen-capture process are detected simultaneously? Both are logged and both modals are displayed — sequentially, with the second shown only after the student dismisses the first.
- What happens if the periodic check is still in-flight when the exam ends? The in-flight response is discarded; no modal is shown after session clear, and the timer is not restarted.

## Requirements

### Functional Requirements

- **FR-001**: The app window MUST enter frameless kiosk fullscreen mode with no OS chrome (no title bar, no frame, no decorations) as soon as an exam session becomes active.
- **FR-002**: The app window MUST be always-on-top, non-resizable, non-movable, and non-minimizable during an active exam session.
- **FR-003**: The app MUST prevent window closure while an exam session is active; closure is only permitted when no exam session is active.
- **FR-004**: The app MUST detect any OS-forced exit from fullscreen during an active exam session, make a single best-effort attempt to re-enter fullscreen (no retry loop), perform the re-entry within one second with no student-facing message, and append a `FULLSCREEN_ESCAPE_ATTEMPT` alert record to the session JSONL log.
- **FR-005**: The app MUST block the following keyboard shortcuts during an active exam session: Alt+Tab, Alt+F4, Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+A, Ctrl+W, Win+D, Win+L, Ctrl+Shift+Esc, F11, Escape, Ctrl+Shift+I, PrintScreen, Alt+PrintScreen, Win+PrintScreen, Win+Shift+S.
- **FR-006**: Blocked shortcuts MUST be silently consumed with no visible effect.
- **FR-007**: Developer tools MUST NOT open on any key press (including F12) during an active exam session.
- **FR-008**: All shortcut blocks and window constraints MUST be released, restoring normal behaviour, when the exam session ends via any of the three exit paths.
- **FR-009**: The app MUST render the exam window as a black/blank surface in any OS screenshot or screen-recording capture during an active exam session.
- **FR-010**: Screen capture protection MUST be removed when the exam session ends so that the app window is capturable normally on Login and Exam-Code pages.
- **FR-011**: The app MUST check whether the student's environment includes a virtual machine or remote desktop software at exam start and every 60 seconds during the exam.
- **FR-012**: If a virtual machine or remote desktop environment is detected, the app MUST append a `VIRTUAL_ENVIRONMENT` alert record to the session JSONL log and display a blocking modal to the student. If the violation still exists on the next 60-second check, the modal MUST re-appear and another alert record MUST be logged — dismissal is an acknowledgement only, not a resolution.
- **FR-013**: The app MUST check for running screen-capture applications at exam start and every 60 seconds during the exam.
- **FR-014**: If a screen-capture application is detected, the app MUST append a `SCREEN_CAPTURE_DETECTED` alert record to the session JSONL log and display a blocking modal to the student. If the process is still running on the next 60-second check, the modal MUST re-appear and another alert record MUST be logged — dismissal is an acknowledgement only, not a resolution.
- **FR-015**: Blocking modals for detected violations MUST suspend all exam interaction until the student explicitly dismisses them. On dismissal, exam interaction MUST resume immediately with no re-check triggered; the next scheduled periodic check handles re-detection.
- **FR-016**: All periodic detection timers MUST be cancelled when the exam session ends via any exit path.
- **FR-017**: Environment detection checks that fail due to backend unavailability MUST fail silently without interrupting the exam.

### Key Entities

- **Exam Session**: The in-memory record of an active exam, identified by `attemptId`. Determines whether all lockdown controls are active or inactive.
- **Environment Check Result**: The output of a VM/RDP/screen-capture detection check — contains boolean detection flags and human-readable reason strings for each threat category (VM, RDP, screen capture).
- **Lockdown Alert**: A record appended to the session log capturing the violation type (`VIRTUAL_ENVIRONMENT`, `SCREEN_CAPTURE_DETECTED`, or `FULLSCREEN_ESCAPE_ATTEMPT`), UTC timestamp, session ID, and reason string.
- **Blocking Modal**: A UI overlay that suspends exam interaction and displays a violation reason; dismissed exclusively by explicit student action.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every blocked shortcut produces no observable effect within 50 milliseconds of being pressed during an active exam session.
- **SC-002**: The app re-enters fullscreen within one second of any OS-forced fullscreen exit during an active exam session.
- **SC-003**: Environment detection (VM, RDP, screen capture) completes and either clears silently or raises a modal within 5 seconds of each check firing. Each individual subprocess call (WMIC, netstat, registry query, process listing) has a 3-second timeout; a timed-out call is treated as clean.
- **SC-004**: All lockdown constraints (shortcuts, fullscreen, content protection, timers) are fully released within one second of the exam session ending.
- **SC-005**: Session log alert records for detected violations are written within 2 seconds of detection, reliably across all three exam exit paths.
- **SC-006**: Zero shortcut blocks, fullscreen constraints, content protection flags, or detection timers remain active after any exam session is cleared.
- **SC-007**: The exam window renders as a blank surface in 100% of OS-level screenshot captures taken during an active exam session.

## Assumptions

- Windows is the only supported platform. macOS and Linux lockdown is out of scope for this spec.
- The exam session lifecycle (set/clear) is managed exclusively via the `examSession` module-scope variable in `frontend/main.js`; this spec introduces no new exit paths.
- The three exam exit paths are: successful submission (`bridge:submit-exam`), logout (`bridge:clear-session`), and back-to-home (`bridge:clear-submit-result`). All lockdown cleanup must be applied on each.
- The Python bridge server is running when the exam session starts. Environment check failures due to bridge unavailability are treated as non-violations and do not interrupt the exam.
- Student dismissal of a violation modal does not auto-terminate the exam. Enforcement decisions (e.g., disqualification) are made by the proctor after reviewing session logs.
- The 60-second detection cadence is fixed; no configuration interface is exposed to students or proctors.
- Screen-capture process detection operates by matching executable names only. Driver-level or kernel-level capture tools are out of scope.
- Each individual subprocess call within the environment check (WMIC, netstat, Windows Registry, process listing) has a 3-second timeout. A call that times out is treated as returning a clean (non-detection) result, consistent with the silent failure requirement.
- Fullscreen re-entry on OS-forced exit is a single best-effort call with no retry loop. A subsequent leave-full-screen event from the same cause will trigger another attempt implicitly.
- The existing JSONL session log format (one JSON record per line, best-effort writes, never raising on failure) is reused without schema changes for lockdown alert records.
- Lockdown controls are independent of AI proctoring services (eye gaze, face detection, etc.); this spec introduces no changes to those services.
- Content protection disabling on session end must not cause any visible flash or transition for the student (the result/login page loads after session clear).
