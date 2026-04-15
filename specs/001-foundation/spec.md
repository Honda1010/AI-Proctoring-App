# Feature Specification: Foundation — App Shell & Python Bridge

**Feature Branch**: `001-foundation`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "Foundation setup — Electron desktop shell, Python Flask bridge, shared design tokens, fonts, and component styles for the Lumina AI Proctoring desktop app."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — App Launches and Bridge Comes Online (Priority: P1)

A student double-clicks the app executable. The window opens and the app confirms the AI
proctoring backend bridge is ready before showing any page content. If the bridge fails to start,
the student sees a clear error message rather than a blank or crashing window.

**Why this priority**: Nothing else in the app works without the Electron shell and the Python
bridge. This is the hard prerequisite for every other spec.

**Independent Test**: Can be fully tested by launching the app and observing that (a) the Electron
window opens, (b) the bridge health endpoint responds, and (c) a "bridge ready" state is
confirmed — all without any LMS credentials or exam data.

**Acceptance Scenarios**:

1. **Given** the app is installed and Python 3.11+ is available on the system PATH,
   **When** the student launches the app,
   **Then** an Electron window opens within 3 seconds and a bridge-ready state is confirmed before any page is displayed.

2. **Given** the app has started successfully,
   **When** Electron queries the bridge health check,
   **Then** the bridge returns a healthy response within 1 second.

3. **Given** Python is not available or the bridge fails to start within 10 seconds,
   **When** Electron detects the timeout,
   **Then** the window displays a clear, user-readable error screen (not a crash or blank window) explaining the problem and how to resolve it.

4. **Given** port 5050 is already in use by another process,
   **When** the bridge tries to start,
   **Then** the app surfaces a visible error identifying the port conflict, and does not silently hang.

---

### User Story 2 — Design Tokens Power All Pages (Priority: P2)

A developer working on any page (Login, Exam Code, Exam) can import a single shared CSS file and
immediately have access to all colors, typography sizes, spacing, and shadow values defined in the
"Ethereal Authority" design system — without repeating or hardcoding any values.

**Why this priority**: All 3 subsequent specs (Login, Exam Code, Exam Page) depend on the shared
design token file. Wrong or missing tokens would cause cascading visual defects across all pages.

**Independent Test**: Can be fully tested by creating a minimal HTML file that imports
`design-tokens.css` and `components.css`, then verifying that CSS custom properties resolve to the
correct values from DESIGN.md using browser DevTools — no LMS or Python connection required.

**Acceptance Scenarios**:

1. **Given** the design token CSS file is included in any page,
   **When** a developer inspects a styled element,
   **Then** the computed color values match the hex codes defined in DESIGN.md exactly (e.g., `primary` = `#006687`, `on-surface` = `#191c1d`).

2. **Given** the shared component CSS file is included,
   **When** a primary button element is rendered,
   **Then** it displays with the gradient fill defined in the design system (`#006687` to `#41B3E3` at 135°), rounded corners (`0.5rem`), and no border.

3. **Given** the shared component CSS file is included,
   **When** an input field is rendered,
   **Then** it shows the ghost border at 20% opacity on the `outline-variant` token and transitions to a full-opacity `primary` glow on focus.

4. **Given** any page includes the shared fonts,
   **When** a headline element is rendered,
   **Then** it uses the Manrope typeface. When a body paragraph is rendered, it uses the Inter typeface.

---

### User Story 3 — Runtime Configuration Is External (Priority: P3)

A system administrator or deployment engineer can change the LMS base URL by editing a single
configuration file — without modifying any source code or rebuilding the application.

**Why this priority**: Different deployments (university A vs university B) point to different LMS
instances. Hard-coded URLs are a security and maintainability violation per the constitution.

**Independent Test**: Can be fully tested by editing `config.json` with a mock base URL, relaunching
the app, and confirming the bridge uses that URL for outbound requests (inspectable in bridge logs).

**Acceptance Scenarios**:

1. **Given** a valid `config.json` file exists at the project root with a `baseUrl` property,
   **When** the Python bridge starts,
   **Then** all outbound LMS API calls use the URL from `config.json`, not any hardcoded value.

2. **Given** `config.json` contains a `baseUrl` starting with `http://` (non-TLS),
   **When** the Python bridge starts,
   **Then** the bridge refuses to start and the Electron window displays a visible configuration error warning the user that a secure connection is required.

3. **Given** `config.json` is missing or malformed (invalid JSON),
   **When** the Python bridge starts,
   **Then** the app displays a clear error explaining the missing/invalid configuration file and its expected location.

---

### Edge Cases

- What happens if the Python process crashes mid-session? The Electron main process should detect the exit, surface a recovery error, and offer a restart option.
- What happens if the app is launched a second time while already running? Only one Python bridge instance should be active; a second launch should switch focus to the existing window.
- What happens if `config.json` exists but the `baseUrl` field is absent? The app should emit a specific "missing baseUrl field" error, not a generic crash.
- What if the system clock is wrong and the JWT immediately appears expired? Token expiry should be re-validated against server time, not local time alone.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST start as a native desktop window using the Electron runtime.
- **FR-002**: The Electron main process MUST spawn the Python Flask bridge as a child process at startup, before rendering any page content.
- **FR-003**: The Python Flask bridge MUST listen on `localhost:5050` (configurable via `config.json` as `pythonPort`).
- **FR-004**: The Python Flask bridge MUST expose a `GET /ping` endpoint that returns a healthy response when the bridge is operational.
- **FR-005**: Electron MUST call `GET /ping` after spawning the bridge and MUST NOT display any page content until a healthy response is received or a 10-second timeout elapses.
- **FR-006**: On bridge startup failure or timeout, Electron MUST display a visible, human-readable error screen (not a crash) with the specific failure reason.
- **FR-007**: All LMS base URLs and configuration MUST be read at runtime from `config.json` at the project root. No base URL, port, or domain MUST be hardcoded in any source file.
- **FR-008**: The Python bridge MUST refuse to start if the configured `baseUrl` uses `http://` (non-TLS) and MUST communicate this refusal back to Electron.
- **FR-009**: A shared CSS file (`frontend/assets/design-tokens.css`) MUST define every color, typography, spacing, radius, and shadow token from the "Ethereal Authority" design specification as CSS custom properties.
- **FR-010**: A shared component CSS file (`frontend/assets/components.css`) MUST implement the reusable UI components (primary button, secondary button, tertiary button, input field, glass modal) using only the tokens from `design-tokens.css` — no hardcoded values.
- **FR-011**: The Manrope and Inter fonts MUST be bundled with the app (not fetched from a CDN) and declared in the shared CSS so they are available offline to all pages.
- **FR-012**: If the Python child process exits unexpectedly after a successful launch, Electron MUST detect the exit event and display a recovery error to the student.

### Key Entities

- **AppConfig**: Runtime configuration loaded from `config.json`. Key attributes: `baseUrl` (LMS API root, must be HTTPS), `pythonPort` (default 5050).
- **BridgeStatus**: The health state of the Python bridge as seen by Electron. States: `starting`, `ready`, `failed`, `crashed`.
- **DesignToken**: A named CSS custom property mapping to an exact value from the "Ethereal Authority" design system (color, font size, spacing, radius, or shadow).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The app window appears and all internal systems confirm readiness within 3 seconds of the student launching the app on a standard machine.
- **SC-002**: 100% of color, typography, spacing, and shadow values defined in DESIGN.md are present as CSS custom properties in `design-tokens.css` with no hardcoded values in component or page files.
- **SC-003**: Changing the LMS server address in the configuration file and relaunching the app causes all outbound LMS calls to use the new address — verified without modifying any source code.
- **SC-004**: Any failure during app startup (missing runtime, port conflict, bad configuration) is always surfaced as a readable on-screen error rather than a silent hang or unhandled crash — 100% of failure scenarios covered.
- **SC-005**: All 3 page HTML files (Login, Exam Code, Exam) can import `design-tokens.css` and `components.css` and render correctly without any additional CSS boilerplate.

## Assumptions

- Python 3.11 or later is installed on the student's machine and available on the system PATH. The app does not bundle its own Python interpreter.
- The app runs on Windows (primary target per project scope). macOS/Linux compatibility is not required for this spec.
- A single `config.json` at the project root is sufficient for all configuration. Multi-environment config management (dev/staging/prod) is out of scope for this spec.
- Electron's built-in `child_process.spawn` is sufficient for launching the Python bridge. A dedicated process manager is not required at this stage.
- The "Remember this device" credential persistence feature is out of scope for this foundation spec; it is handled in the Login spec (002).
