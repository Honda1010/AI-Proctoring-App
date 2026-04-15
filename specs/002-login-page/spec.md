# Feature Specification: Login Page

**Feature Branch**: `002-login-page`
**Created**: 2026-04-15
**Status**: Draft
**Input**: User description: "002-login-page"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Student Sees the Login Form (Priority: P1)

A student launches Lumina AI after the bridge has started successfully. The login page
renders immediately, displaying the "Welcome Back" card with the Ethereal Authority design:
shield icon, email and password input fields, a "Remember this device" checkbox, and the
primary LOGIN button. The design precisely matches the approved screen design.

**Why this priority**: Without the login form rendering correctly, no other login behaviour
is reachable. This is the minimum visible deliverable of the spec.

**Independent Test**: Open `frontend/pages/login/index.html` directly in Electron (or a
browser). Verify that the card, inputs, button, progress pills, footer, and nav bar are all
visible and match the screen design in `Designs/Login_Page/screen.png`. No network call
required.

**Acceptance Scenarios**:

1. **Given** the app has loaded the login page, **When** the page renders, **Then** the card
   displays a shield icon, the headline "Welcome Back", the subtitle "The Digital Sanctuary
   of Integrity", an EMAIL ADDRESS input, a PASSWORD input, a "Forgot password?" link, a
   "Remember this device" checkbox, and a full-width "LOGIN →" primary button.
2. **Given** the login page is visible, **When** the student examines the footer area,
   **Then** three bottom progress pills are visible with the first one active, a floating
   info button appears in the bottom-right corner, and the footer shows copyright, Privacy
   Policy, Terms of Service, and System Check links.
3. **Given** the login page is visible, **When** the student examines the navigation bar,
   **Then** the "Lumina" wordmark appears on the left and a "Login" label with help (?) and
   info (ⓘ) icon buttons appears on the right.
4. **Given** all design tokens are loaded from `frontend/assets/design-tokens.css`, **When**
   the page is inspected, **Then** no hardcoded hex colour values exist in login page CSS
   files and the background gradient is defined entirely via CSS custom properties.

---

### User Story 2 — Student Submits Credentials and Logs In (Priority: P1)

A student enters their institutional email and password and clicks LOGIN. The form validates
the input client-side, then the request is forwarded through the Python bridge to the LMS
login endpoint. On success, the JWT access token and refresh token are stored securely, and
the app navigates to the exam-code page.

**Why this priority**: Authentication is the core purpose of this page. Without a working
submit flow the app cannot progress past login.

**Independent Test**: Use mock credentials routed to a stub Python bridge endpoint returning
the sample 200 OK response from the API docs. Verify the app navigates to the exam-code
page stub and that the IPC layer stores tokens correctly. No live LMS required.

**Acceptance Scenarios**:

1. **Given** the login form is visible, **When** the student submits a valid email and
   non-empty password, **Then** the LOGIN button shows a loading state (spinner, disabled),
   the bridge is called via IPC with the credentials, and on a 200 OK response the app
   navigates to the exam-code page.
2. **Given** the student checks "Remember this device" and logs in successfully, **When** the
   app is closed and relaunched, **Then** the saved session is detected and the login page
   is bypassed, navigating the student directly to the exam-code page.
3. **Given** the student does NOT check "Remember this device" and logs in, **When** the app
   is closed and relaunched, **Then** no stored session is found and the login page is
   shown again.
4. **Given** the student submits a blank email or password, **When** the form validates
   client-side, **Then** an inline error message appears without making any network call and
   the form does not submit.
5. **Given** the student enters an email without a valid format (e.g., no "@"), **When** the
   form validates, **Then** an inline error "Please enter a valid email address" appears
   without submitting.

---

### User Story 3 — Student Sees a Specific Error for Each Failure Case (Priority: P2)

When the LMS rejects the login attempt, the student sees a clear, human-readable error
message describing their specific situation. Each error scenario has a distinct message.
No raw API strings, tokens, or email addresses appear in the error display.

**Why this priority**: Error clarity is essential for a high-stakes exam context where
students cannot easily seek help. This story is lower priority than the happy path but must
be complete before the feature is shippable.

**Independent Test**: Manually inject mock 401 and 500 responses from the Python bridge
stub and verify each error message renders in the correct location on screen without
exposing credentials or raw error payloads.

**Acceptance Scenarios**:

1. **Given** the student submits wrong credentials, **When** the bridge returns a 401 with
   `"Invalid Email/password"`, **Then** the inline error "Invalid email or password" appears
   below the password field.
2. **Given** the student's account is locked out, **When** the bridge returns a 401 with
   `"locked out"` in the message, **Then** the inline error reads "Your account is
   temporarily locked. Please contact your administrator."
3. **Given** the student's email is not confirmed, **When** the bridge returns a 401 with
   `"is not confirmed"` in the message, **Then** the inline error reads "Please confirm your
   email address before logging in."
4. **Given** the student's account is administratively disabled, **When** the bridge returns
   a 500 with `"is disabled"` in the message, **Then** the inline error reads "Your account
   has been disabled. Please contact your administrator."
5. **Given** the bridge itself is unreachable or returns an unexpected error, **When** a
   network-level failure occurs, **Then** the inline error reads "Unable to reach the
   server. Please check your connection and try again."
6. **Given** any error is displayed, **When** the student inspects the DOM and console,
   **Then** no JWT tokens, raw passwords, raw API `errorMessage` strings, or student email
   addresses are visible in the page source or browser console.

---

### User Story 4 — Saved Session Is Restored on Relaunch (Priority: P2)

When "Remember this device" was checked on a previous successful login and the stored
refresh token has not expired, the app bypasses the login page on relaunch and navigates
directly to the exam-code page. When the saved session is expired or missing, the login
page is shown normally.

**Why this priority**: Session restore prevents unnecessary re-authentication. Secondary to
the core login flow.

**Independent Test**: Use the OS keychain (Windows Credential Manager) to inspect and
manually set stored token entries. Verify that a valid stored session causes `main.js` to
navigate past login. Verify that deleting keychain entries shows the login page normally.

**Acceptance Scenarios**:

1. **Given** a stored session with a refresh token not yet expired, **When** `main.js` loads
   the login page, **Then** the session check runs before the page is displayed and the
   window navigates directly to the exam-code page without rendering the login form.
2. **Given** a stored session whose `refreshTokenExpiration` is in the past, **When**
   `main.js` checks the session, **Then** the expired tokens are cleared from the keychain
   and the login page is shown normally.
3. **Given** no stored session exists (first launch or after logout), **When** `main.js`
   checks the session, **Then** the login page is loaded and displayed normally.

---

### Edge Cases

- Double-clicking the LOGIN button must not send two requests — the form is disabled after
  the first click until a response arrives.
- If the LMS base URL is unreachable (no internet / wrong domain in config.json), the
  bridge returns a `BRIDGE_ERROR` and the page shows "Unable to reach the server."
- If the Python bridge crashes between bridge-ready and the login call completing, the
  page shows the "server unreachable" message rather than a blank or hung state.
- If `profilePictureUrl` in the login response is `null`, the session must store correctly
  and downstream pages must receive a null-safe value.
- Pressing Enter inside either input field must trigger form submission.
- If the keychain entry is corrupt (unparseable JSON in the user-profile blob), the corrupt
  entry must be cleared and the login page shown without crashing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The login page MUST render identically to `Designs/Login_Page/screen.png`,
  using only Ethereal Authority design tokens — no hardcoded hex values in page CSS.
- **FR-002**: The login form MUST validate that the email field is non-empty and
  syntactically valid (contains "@" and a domain) before submitting.
- **FR-003**: The login form MUST validate that the password field is non-empty before
  submitting. Password complexity is NOT validated client-side.
- **FR-004**: The LOGIN button MUST enter a loading state (disabled, spinner visible) from
  the moment the form is submitted until the bridge responds or an error is shown.
- **FR-005**: The login request MUST be sent to the Python bridge via IPC — the renderer
  MUST NOT make any direct HTTP calls to the LMS API.
- **FR-006**: The Python bridge MUST proxy `POST /api/Authuantication/login` to the LMS,
  forwarding `email` and `password`, and return either a success payload or a typed error
  object `{code, message}` to the Electron main process.
- **FR-007**: On a successful login response, the access token, refresh token, token expiry,
  refresh token expiration, and user profile data (id, email, firstName, lastName,
  profilePictureUrl) MUST be stored via keytar in the OS keychain.
- **FR-008**: Token storage via keytar is ONLY performed when "Remember this device" is
  checked. If unchecked, tokens are held in memory only and cleared when the app closes.
- **FR-009**: On successful login, the app MUST navigate to the exam-code page
  (`frontend/pages/exam-code/index.html`).
- **FR-010**: Each API error scenario MUST display a distinct, human-readable inline message
  mapped as follows:
  — `"Invalid Email/password"` → "Invalid email or password"
  — `"locked out"` in message → "Your account is temporarily locked. Please contact your administrator."
  — `"is not confirmed"` in message → "Please confirm your email address before logging in."
  — `"is disabled"` in message → "Your account has been disabled. Please contact your administrator."
  — all other/network errors → "Unable to reach the server. Please check your connection and try again."
- **FR-011**: Error messages MUST NOT contain raw API `errorMessage` strings, JWT tokens,
  passwords, or student email addresses.
- **FR-012**: On app launch, the main process MUST check the OS keychain for a stored
  session before loading the login page. If a valid, non-expired session exists, the app
  MUST navigate directly to the exam-code page without displaying the login form.
- **FR-013**: If the stored refresh token's `refreshTokenExpiration` is in the past, the
  keychain entries MUST be cleared and the login page MUST be shown.
- **FR-014**: The "Remember this device" checkbox MUST default to unchecked.
- **FR-015**: Pressing Enter in either input field MUST trigger form submission.
- **FR-016**: The "Forgot password?" link MUST open the system default browser to a
  configured URL. If no URL is configured, the link is visible but non-functional (disabled)
  rather than causing a crash.

### Key Entities

- **LoginRequest**: `email: string`, `password: string`
- **LoginResponse**: `id: string`, `email: string`, `firstName: string`,
  `lastName: string`, `profilePictureUrl: string | null`, `token: string`,
  `expinresIn: number`, `refreshToken: string`, `refreshTokenExpiration: string`
- **StoredSession**: keytar service `lumina-ai-proctoring`; keys: `access-token`,
  `refresh-token`, `token-expiry`, `refresh-expiry`, `user-profile` (JSON blob),
  `remember-flag`
- **BridgeLoginError**: `code: string` (one of `INVALID_CREDENTIALS`, `LOCKED_OUT`,
  `EMAIL_NOT_CONFIRMED`, `ACCOUNT_DISABLED`, `BRIDGE_ERROR`), `message: string`

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A student with valid credentials can complete the full login flow (page
  visible → form filled → button clicked → exam-code page visible) in under 10 seconds on
  a standard connection.
- **SC-002**: All five error scenarios each display a distinct, correct inline message
  within 3 seconds of the server responding.
- **SC-003**: A student who checked "Remember this device" on a prior login reaches the
  exam-code page on relaunch without manually entering credentials.
- **SC-004**: Zero credentials, tokens, or raw API error strings appear in the browser
  console or DOM source under any login outcome (success, failure, or crash).
- **SC-005**: The rendered login page achieves a visual match with `Designs/Login_Page/screen.png`
  at 1280×800, with all Ethereal Authority tokens applied and no hardcoded hex values in
  page CSS files.

---

## Assumptions

- The Python bridge (spec 001-foundation) is already running and healthy before the login
  page is shown. Bridge startup and health polling are handled by spec 001.
- The `baseUrl` in `config.json` points to a live or stub LMS that accepts
  `POST /api/Authuantication/login`.
- `keytar` is already installed (spec 001 T002).
- `@fontsource/manrope`, `@fontsource/inter`, `design-tokens.css`, and `components.css`
  are already in place from spec 001.
- `requests>=2.32` will be added to `python_bridge/requirements.txt` in this spec for the
  bridge to make outbound HTTP calls.
- The "Forgot password?" URL is not yet defined — the link is present but non-functional.
- Session restore (FR-012) checks only the refresh token expiry; it does not call the LMS
  to revalidate the access token.
- The floating info FAB and "System Access Policy" link navigate to `#` — their
  destinations are out of scope for this spec.


## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]
