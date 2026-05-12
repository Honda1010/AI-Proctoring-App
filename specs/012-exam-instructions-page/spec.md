# Feature Specification: Pre-Exam Instructions Page

**Feature Branch**: `012-exam-instructions-page`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "012-exam-instructions-page — A mandatory Pre-Exam Instructions page shown after AI Readiness calibration, displaying 8 proctoring rules, requiring acknowledgment via checkbox, and gating exam entry behind a Start Exam button."

## Clarifications

### Session 2026-05-07

- Q: How does the ai-readiness page navigate to the instructions page — does the existing ai-readiness navigation target need changing, or is a different entry point used? → A: Update the ai-readiness "Continue to Exam" button to navigate to `exam-instructions` instead of `exam` (one existing file edit; no new IPC required).
- Q: Should the student's acknowledgment be logged to the session JSONL as auditable evidence? → A: No — the page is purely navigational and leaves no trace in the session log.
- Q: What happens if the student navigates back to the instructions page during an active exam? → A: Out of scope — back-navigation into the instructions page during an active exam is not supported; exam-page lockdown handles navigation prevention.
- Q: Is a new `loadPage` routing entry required in `main.js` for the `'exam-instructions'` page key? → A: Yes — page key `'exam-instructions'` maps to `frontend/pages/exam-instructions/index.html`; a new entry in `main.js` `loadPage` is required as part of this feature.
- Q: Should the acknowledgment footer be pinned to the bottom of the card or to the viewport? → A: Pinned to the bottom of the card — the rules list scrolls independently inside the card while the footer stays at the card's bottom edge (`position: sticky; bottom: 0` within a flex-column card layout).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — View Proctoring Rules and Acknowledge (Priority: P1)

A student has just completed AI Readiness calibration and is ready to begin their supervised exam. The app navigates them to the Pre-Exam Instructions page, which displays eight mandatory proctoring rules with a descriptive icon for each. After reading the rules, the student checks a confirmation checkbox to indicate understanding before the "Start Exam" button becomes active.

**Why this priority**: This is the core purpose of the page. Without the ability to present rules and capture acknowledgment, the feature delivers no value. All other stories depend on this one completing first.

**Independent Test**: Can be fully tested by loading the instructions page with a valid exam session in memory, verifying all 8 rules are visible with titles and descriptions, checking the acknowledgment checkbox, and confirming the "Start Exam" button transitions from disabled to enabled — no server calls or additional pages required.

**Acceptance Scenarios**:

1. **Given** a student arrives on the Pre-Exam Instructions page, **When** the page finishes loading, **Then** all 8 proctoring rules are visible, each showing an icon, a rule title, and a one-line description.
2. **Given** the page has loaded, **When** the student has not yet checked the acknowledgment checkbox, **Then** the "Start Exam" button is disabled and cannot be clicked.
3. **Given** the student checks the acknowledgment checkbox ("I have read and agree to all exam rules"), **When** the checkbox state changes to checked, **Then** the "Start Exam" button becomes enabled and is visually interactive.
4. **Given** the student checks and then unchecks the acknowledgment checkbox, **When** the checkbox state returns to unchecked, **Then** the "Start Exam" button returns to its disabled state.
5. **Given** the page is displayed, **When** the student scrolls through the rules list, **Then** the acknowledgment checkbox and "Start Exam" button remain visible and accessible (pinned footer area).

---

### User Story 2 — Navigate to Active Exam (Priority: P1)

After acknowledging the rules, the student clicks "Start Exam." The button enters a loading state to signal the transition is in progress. The app navigates the student to the active exam page.

**Why this priority**: This is the exit path of the page and directly determines whether the student reaches the exam. It is equally critical as acknowledgment — neither alone is sufficient.

**Independent Test**: Can be fully tested by checking the acknowledgment checkbox, clicking "Start Exam," and verifying (a) the button shows a loading/spinner state and is disabled, and (b) the app navigates to the exam page with the correct exam content loaded.

**Acceptance Scenarios**:

1. **Given** the acknowledgment checkbox is checked, **When** the student clicks "Start Exam", **Then** the button is immediately disabled, its label changes to "Starting…", and a spinner is shown.
2. **Given** the "Start Exam" button is in loading state, **When** the navigation completes, **Then** the student is on the active exam page with the exam title, timer, and questions visible.
3. **Given** the "Start Exam" button is in loading state, **When** navigation fails (examSession data is missing), **Then** the student is redirected to the login page rather than shown a blank or crashed page.

---

### User Story 3 — Session Guard: Prevent Unauthorized Access (Priority: P1)

A student navigates directly to the instructions page URL without having completed login, exam code entry, or AI readiness calibration. The page detects the missing session and immediately redirects to login, preventing the instructions page from ever rendering without a valid context.

**Why this priority**: Security invariant. Every page in the app that sits inside the exam flow must guard against direct URL access. Without this guard, the instructions page would render in an invalid state, potentially allowing bypassed exam entry.

**Independent Test**: Can be fully tested by loading the instructions page with no exam session present and confirming immediate redirection to the login page — no rules list or buttons should render at any point.

**Acceptance Scenarios**:

1. **Given** no exam session exists in the app state, **When** the instructions page initialises, **Then** the page immediately redirects to login without displaying any content.
2. **Given** an exam session exists but is missing a valid attempt ID, **When** the instructions page initialises, **Then** the page immediately redirects to login.
3. **Given** a valid exam session exists, **When** the instructions page initialises, **Then** the page renders normally and no redirect occurs.

---

### Edge Cases

- What if the student's exam session expires between loading the instructions page and clicking "Start Exam"? → The exam page's own session guard will catch this; no additional handling needed on the instructions page.
- What if the student resizes or zooms the window so the rules list overflows? → The rules list must be scrollable; the checkbox/button footer must always remain accessible.
- What if the page is loaded a second time (student navigated back)? → Checkbox state resets to unchecked on every page load; the student must re-acknowledge.
- What if the student navigates back to the instructions page from the active exam mid-session? → Out of scope. Back-navigation into this page during an active exam is not supported; exam-page lockdown (spec 014) is responsible for preventing navigation away from the exam.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The page MUST display exactly 8 proctoring rules, each with an icon, a title, and a one-sentence description, in the fixed order defined below.
- **FR-002**: Rule icons MUST be inline SVG sourced from the existing project icon vocabulary; no external CDN, image files, or icon fonts are permitted.
- **FR-003**: The "Start Exam" button MUST be disabled by default and MUST only become enabled when the acknowledgment checkbox is checked.
- **FR-004**: When "Start Exam" is clicked, the page MUST enter a loading state: button disabled, label replaced with "Starting…" and a spinner, matching the loading pattern on the login and exam-code pages.
- **FR-005**: When "Start Exam" is clicked, the page MUST navigate to the active exam page using the same `loadPage`/`navigate` pattern used by all other pages in the app.
- **FR-006**: On page initialisation, if no valid exam session (with a non-empty attempt ID) is found in app state, the page MUST immediately navigate to login without rendering any page content.
- **FR-007**: The acknowledgment checkbox and "Start Exam" button MUST remain visible at all times regardless of how far the student has scrolled in the rules list. The footer is sticky inside the card (`position: sticky; bottom: 0` within a flex-column card), not fixed to the viewport.
- **FR-008**: The page MUST conform to the "Ethereal Authority" design system: surface hierarchy, typography (Manrope display/headline, Inter body/label), spacing, corner radii, and colour tokens as defined in `Designs/Exam _Instructions_Page/DESIGN.md`.
- **FR-009**: No new IPC channels, backend API endpoints, or configuration keys are required for this page. A new `loadPage` routing entry for the `'exam-instructions'` key must be added to `main.js`, and the ai-readiness page navigation target must be updated from `'exam'` to `'exam-instructions'` — both are edits to existing files, not new infrastructure.

### The 8 Proctoring Rules (fixed content, FR-001)

| # | Title | Description |
|---|-------|-------------|
| 1 | Quiet Environment | Ensure a completely quiet, distraction-free location. |
| 2 | Full-Screen Mode | Do not exit full-screen mode at any time. |
| 3 | No Unauthorized Devices | Mobile phones, earphones, and smartwatches are strictly prohibited. |
| 4 | Room Privacy | You must be alone. No one else is permitted to enter the room. |
| 5 | No Leaving Seat | Complete all personal tasks beforehand; leaving your seat is forbidden. |
| 6 | Screen Focus | Keep your eyes on the screen. The AI system monitors head and eye movements. |
| 7 | No Virtual Machines | The exam must run on a native OS. VMs are strictly blocked. |
| 8 | No Unauthorized Keystrokes | Automated keystrokes and macros are forbidden. |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Students with a valid exam session can reach the "Start Exam" button and begin the exam without any additional steps or support interactions.
- **SC-002**: Students without a valid exam session are redirected to login within 1 second of page load — the instructions page content is never visible to them.
- **SC-003**: The page visually matches the reference design in `Designs/Exam _Instructions_Page/screen.png` with no style regressions on any other existing page.
- **SC-004**: All 8 rules are readable without horizontal scrolling at the app's default window size.
- **SC-005**: The "Start Exam" button loading state is visually consistent with the loading patterns on the login and exam-code pages (same spinner, same disabled appearance).

## Assumptions

- The exam session (including attempt ID, exam title, and questions) is fully loaded into app state before the AI readiness page navigates to this page.
- The ai-readiness "Continue to Exam" button will be updated to navigate to `exam-instructions` (not `exam`) as part of this feature; no new IPC channel is required — it is a single call-site change in the existing ai-readiness JS file.
- The student's window size is at minimum the same default Electron window size used by all other pages; no mobile viewport handling is required.
- The Electron Content Security Policy (`default-src 'self'; style-src 'self'; script-src 'self'; font-src 'self' data:`) applies to this page exactly as it does to every other page — no CSP changes are needed.
- Checkbox state is ephemeral (not persisted); every page load starts with the checkbox unchecked.
- The page is the last gate before the active exam — no additional interstitial pages are inserted between it and the exam page.
