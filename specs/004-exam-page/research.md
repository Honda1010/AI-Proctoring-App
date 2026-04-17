# Research: Exam Page

**Branch**: `004-exam-page` | **Date**: 2026-04-16  
**Input**: Unknowns extracted from `spec.md` Technical Context + best-practice tasks

---

## Decision 1 — Token delivery for exam submission

**Question**: `POST /api/QuizAttempts/submit/{attemptId}` requires `Authorization: Bearer <token>`. The renderer never holds tokens (constitution.md — Security by Default). How does the JWT reach the bridge for the submit call?

**Decision**: Identical pattern to spec 003 (`POST /exam-access`). main.js reads the access token from `sessionMemory?.accessToken` or from keytar (`access-token` key), then includes it as `"token"` in the `POST /submit-exam` request body sent to the bridge. The bridge reads the value, attaches it as the `Authorization: Bearer` header to the outbound LMS call, then discards it — never logged, never stored by the bridge, never returned in any response.

**Rationale**: The token is already owned by main.js. This is the same pattern used for `bridge:start-exam` and `bridge:login`, making the entire authentication surface symmetric. Putting it in the request body (not a URL path or query param) prevents it appearing in any server or proxy access log.

**Alternatives considered**:
- Shared file / environment variable: Bridge holds token for whole app lifetime — wrong; token is per-session and may be absent.
- URL path parameter: Appears in HTTP server access logs.
- Separate IPC "get token" call from bridge to main: Adds complexity; IPC is renderer ↔ main only, not bridge ↔ main.

---

## Decision 2 — AnswerMap data structure and scope

**Question**: Where should the student's in-progress answer selections be stored, and in what data structure?

**Decision**: A plain JavaScript object `answerMap = {}` declared at the top of `exam.js` (renderer module scope). Keys are question IDs (numbers), values are choice IDs (numbers). Example: `{ 101: 205, 102: 210 }`. The object is populated on every choice selection and read when building the submit payload.

**Rationale**: A plain object with numeric keys provides O(1) reads/writes per question, is trivially JSON-serialisable for the submit payload, and requires zero framework dependencies. Module scope (declared once on page load, reset by page reload) is the correct lifetime — it must persist across question navigation but never survive a page reload or app restart. `const answerMap = {}` with mutation is idiomatic for this lifetime.

**Alternatives considered**:
- `localStorage`/`sessionStorage`: Prohibited by constitution; also unnecessary for in-session data.
- `Map` object: More ergonomic but adds a serialisation step (`Object.fromEntries`) before submission; plain object is simpler here since keys are already valid object keys.
- Module-scope in main.js: Would require a new IPC channel per answer update — unacceptable latency for rapid navigation.

---

## Decision 3 — FlagSet data structure

**Question**: How should flagged question IDs be tracked?

**Decision**: `const flagSet = new Set()` in `exam.js` renderer module scope. Toggling a flag calls `flagSet.add(questionId)` or `flagSet.delete(questionId)`. Reading a flag state uses `flagSet.has(questionId)`.

**Rationale**: `Set` provides O(1) add/delete/has, models the "set of flagged IDs" intent precisely, and is well-supported in Chrome (Electron). The flag state drives only the navigator pill display — no serialisation is ever needed (flags are never submitted).

**Alternatives considered**:
- Object `{ [id]: boolean }`: Slightly less ergonomic; `delete` is needed to truly remove, vs. `Set.delete()`. `Set` is cleaner for this use case.
- Array: O(n) membership check; wrong data structure for a set of unique IDs.

---

## Decision 4 — SubmitResult hand-off to spec 005 (result page)

**Question**: After `POST /submit-exam` succeeds, how does the full `SubmitResult` (score, percentage, per-question review) reach the result page, which is a separate HTML page loaded by Electron?

**Decision**: main.js stores the `SubmitResult` in a new module-scope variable `submitResult`. The result page (spec 005) retrieves it via a new IPC invoke channel `bridge:get-submit-result` immediately after its own `DOMContentLoaded`. If `submitResult` is null, spec 005 redirects to Login.

After a successful submission, `examSession` is set to `null` in main.js (the exam is over; prevent the Exam page from being re-entered without a new code).

**Rationale**: Mirrors the `examSession` hand-off pattern from spec 003. Avoids URL query strings (arbitrary length for large result arrays; appears in navigation history), avoids `localStorage` (prohibited), and avoids re-submitting to the LMS (would create a duplicate grade record).

**Alternatives considered**:
- URL query param: Not viable for objects with nested arrays (per-question review); would require JSON encoding in the URL.
- `bridge:get-result` re-call that fetches from LMS again: `GET /api/QuizAttempts/result/{attemptId}` exists but adds a network round-trip and requires main.js to keep `attemptId` alive post-submit. Module-scope hand-off is simpler.
- Re-use the same IPC channel as the submit: Conflates two distinct operations; the submit and read are separate lifecycles.

---

## Decision 5 — Countdown timer drift correction

**Question**: `setInterval(fn, 1000)` accumulates drift over time — on a 90-minute exam, naïve implementation can be 10–30 seconds off by the end. How is the timer kept accurate to ±1 second (SC-004)?

**Decision**: Record `startTime = Date.now()` and `totalSeconds` (parsed from `examSession.duration`) at timer start. Each interval tick computes `elapsed = Math.floor((Date.now() - startTime) / 1000)` and derives `remaining = totalSeconds - elapsed`. Display is based on `remaining`, not a decrementing counter. This approach is immune to interval jitter.

**Rationale**: Date-based drift correction is the standard approach for countdown timers in JavaScript. It compensates for both JS event loop jitter and Chromium timer throttling (which Electron may apply to backgrounded windows). The ±1 second requirement in SC-004 is satisfied because display granularity is 1 second and the correction resets on every tick.

**Alternatives considered**:
- Naive `let remaining = totalSeconds; setInterval(() => { remaining--; }, 1000)`: Accumulates drift; fails SC-004.
- `requestAnimationFrame`: Overkill for a 1-second display; wastes CPU; does not improve accuracy at 1s granularity.
- Server-side authoritative time: The LMS starts the timer server-side; we deliberately do NOT attempt to sync with it — that would require an extra LMS API call and would complicate offline/local testing. The client-side timer is for display only; the LMS enforces the true deadline.

---

## Decision 6 — Webcam stream management

**Question**: FR-017 requires `getUserMedia({video:true})` on page load and FR-018 requires all tracks stopped on navigation away. How is this implemented without IPC?

**Decision**: `exam.js` calls `navigator.mediaDevices.getUserMedia({ video: true, audio: false })` in `DOMContentLoaded`. On success, `stream.getTracks()` are iterated and assigned to `videoElement.srcObject = stream`. A module-scope `let activeStream = null` holds the reference. A `window.addEventListener('beforeunload', ...)` handler calls `activeStream?.getTracks().forEach(t => t.stop())`. On camera denial (`NotAllowedError`, `NotFoundError`, or any other failure), a "Camera unavailable" placeholder is shown; the exam continues normally.

**Rationale**: `getUserMedia` is a browser API available in the Electron renderer process without any IPC. The `beforeunload` event fires reliably before page navigation in Electron. Storing the stream reference module-scope ensures the cleanup handler can always access it.

**Alternatives considered**:
- IPC-based camera management (main process): Unnecessary; `getUserMedia` is a renderer API, not a Node.js API. Electron's renderer process has full access to it.
- Web Workers: Overkill for a single video feed with no processing.
- Stop tracks on the submit success callback only: Misses other exit paths (app close, redirect on 401). `beforeunload` covers all paths.

---

## Decision 7 — Confirmation modal implementation

**Question**: FR-012 requires a confirmation modal before manual submission. Should it use `window.confirm()` or a custom DOM modal?

**Decision**: Custom DOM modal using the Ethereal Authority glass-modal style (per DESIGN.md section 5 "Glass Modals"). The modal HTML is in `index.html` (hidden by default via `display:none`). `exam.js` shows/hides it by toggling a CSS class. The modal is NOT shown for auto-submit (timer expiry).

**Rationale**: `window.confirm()` renders a native OS dialog that cannot be styled, interrupts the JS event loop (blocking the timer), and is prohibited in Electron's content security policy by default in newer versions. A custom modal is consistent with the "Digital Sanctuary" design ethos and allows the unanswered question count to be dynamically inserted. It is also consistent with the approach implied by the design prototype (`Designs/Exam_Page/code.html`), which uses custom glassmorphic card-based UI for all overlays.

**Alternatives considered**:
- `window.confirm()`: Non-styleable; blocks event loop; may be prohibited by CSP; inconsistent with design system.
- Electron `dialog.showMessageBox()`: Runs in main process (requires IPC round-trip); native OS appearance; inconsistent with design system.
- Inline warning text below the submit button: Not prominent enough for a destructive, irreversible action.

---

## Decision 8 — Design token gaps for Exam page

**Question**: Does `Designs/Exam_Page/code.html` require any new CSS custom properties not already in `design-tokens.css`?

**Finding**: No new tokens are required. All visual elements map to existing tokens:
- Timer chip: `--color-surface-container-low`, `--color-primary`, `--radius-chip`
- Question badge: `--color-primary-fixed`, `--color-on-secondary-fixed-variant` (mapped as `on-primary-fixed-variant` in Tailwind prototype), `--radius-chip`
- Selected choice: `border: 2px solid var(--color-primary)`, letter circle `--color-primary` with white text
- Unselected choice: `--color-surface-container-lowest` background, `--color-outline-variant` ghost border, `--color-surface-container-high` circle
- Navigator pill states: answered = `--color-primary`, current = `--color-primary` + ring `rgba(0,102,135,0.2)`, flagged = `--color-tertiary` (#8C5000 per DESIGN.md "Flagged states"), unanswered = `--color-surface-container-high`
- Proctoring panel: `--color-surface-container-low` background, ghost border `--color-outline-variant` at 20% opacity
- Status row cards: `--color-surface-container-lowest`, `--radius-card` (xl)
- Submit button: gradient `--gradient-primary` mirrored with error tint (the design uses `from-error to-tertiary-container` in Tailwind; in plain CSS: `linear-gradient(135deg, var(--color-error), var(--color-tertiary))`). This is an **exception granted by spec 004** — the submit button uses the error→tertiary gradient to signal urgency, distinct from the primary action gradient. No new token needed; it uses two existing color tokens.
- Glass modal: `--color-surface-container-lowest` at 80% opacity, `backdrop-filter: blur(16px)`, ghost border at 15% opacity
