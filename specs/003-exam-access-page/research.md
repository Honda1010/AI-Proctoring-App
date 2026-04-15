# Research: Exam Access Page

**Branch**: `003-exam-access-page` | **Date**: 2026-04-15  
**Input**: Unknowns extracted from `spec.md` Technical Context + best-practice tasks

---

## Decision 1 — Token delivery from main.js to Python bridge

**Question**: The Python bridge must attach `Authorization: Bearer <token>` to the LMS call. How should the JWT reach the bridge, given that the renderer never holds tokens?

**Decision**: main.js reads the access token from its module-scope `sessionMemory` or directly from keytar, then includes it as a JSON field (`"token"`) in the `POST /exam-access` request body sent to the bridge. The bridge reads the value, attaches it as the Authorization header to the outbound LMS request, then discards it — it is never logged, never stored by the bridge, and never returned in any response.

**Rationale**: The token is already owned by main.js (set during `storeSession()`). Sending it through the existing IPC→bridge HTTP hop keeps the flow symmetric with the login path and avoids any new credential-storage mechanism. Passing it in the body (not a URL query parameter) prevents it appearing in any server or proxy access log.

**Alternatives considered**:
- Shared secret / file: Fragile and violates the "no files for credentials" rule.
- Environment variable injected at bridge startup: Bridge would hold the token for the whole app lifetime — wrong; the token changes per session.
- URL path/query parameter: Would appear in any HTTP server access log.

---

## Decision 2 — Bridge endpoint method for exam start

**Question**: The LMS endpoint is `GET /api/QuizAttempts/attempt/{quizCode}`. Should the corresponding bridge endpoint also be GET, or POST?

**Decision**: Use `POST /exam-access` on the bridge. The request body carries `{"quizCode": "...", "token": "..."}`. Internally, the bridge issues a `GET` to the LMS with the Authorization header.

**Rationale**: GET requests have no body (by HTTP convention), so the token can't be cleanly delivered in a GET body. Using POST on the bridge-internal HTTP API keeps credential delivery consistent with the login path. The renderer / main.js never sees the difference in LMS HTTP method.

**Alternatives considered**:
- GET with a custom header: Electron `net.fetch` supports it, but then the IPC layer must pass raw header strings — more surface area. POST body is simpler and already precedented.

---

## Decision 3 — ExamSession hand-off to the Exam page

**Question**: After `POST /exam-access` returns, how does the full `ExamSession` (attemptId, title, duration, questions) reach the Exam page, which is a completely separate HTML page loaded by Electron?

**Decision**: main.js stores the `ExamSession` in a module-scope variable `examSession`. The Exam page retrieves it via a new synchronous IPC invoke channel `bridge:get-exam-session` immediately after the page loads.

**Rationale**: This mirrors how `sessionMemory` is used for the login session. It avoids URL query strings (which could appear in navigation history or be arbitrarily long for large question arrays), avoids `localStorage`/`sessionStorage` (forbidden by constitution), and avoids re-fetching from the bridge (which would create a second attempt record via the LMS).

**Alternatives considered**:
- URL query param: Length-limited, appears in navigation history, would encode sensitive attempt data as plaintext.
- A new IPC event fired on navigation: Timing-dependent and fragile; the page may not have registered the listener.
- Re-call the bridge: Would create second attempt record (LMS is stateful — each call creates an attempt). Explicitly forbidden by API docs.

---

## Decision 4 — Client-side 15-second timeout

**Question**: How is the 15-second client-side timeout (FR-012) implemented in the renderer?

**Decision**: `exam-code.js` uses `Promise.race()` between the `window.bridge.startExam()` IPC call and a `new Promise(resolve => setTimeout(() => resolve({ok: false, timeout: true}), 15000))`. On timeout branch, the loading state is cleared and a network error message is shown.

**Rationale**: The bridge itself has a 15-second `requests.post` timeout, but that triggers a 503 from the bridge which is still a response. The client-side race handles the case where the IPC + bridge + LMS chain as a whole stalls for any reason (e.g., bridge process unresponsive). `Promise.race` is idiomatic and avoids AbortController boilerplate.

**Alternatives considered**:
- AbortController with `fetch`: Not applicable; uses IPC invoke, not fetch.
- No client-side timeout: Violates FR-012 and SC-001.

---

## Decision 5 — Hidden question/choice IDs

**Question**: The LMS API docs note that question and choice IDs are "intentionally hidden" in the `GET /api/QuizAttempts/attempt/{quizCode}` response. Answer submission (spec 004) requires these IDs. Are they available?

**Finding**: This is a known API limitation documented by the backend team. The resolution is out of scope for this spec (003). The plan and data model for 003 record the data shape as received. Spec 004 will track the backend dependency.

**Action recorded**: `data-model.md` notes that `id` fields on questions and choices are expected to be present in the live payload even if absent from public API docs. If not, this is a spec 004 blocker.

---

## Decision 6 — Design token gaps for Exam Access page

**Question**: Does the `Designs/Exam_Code_Page/screen.png` require any new CSS custom properties not already in `design-tokens.css`?

**Finding**: No new tokens are required. All visual elements in the design map to existing tokens: `--color-primary`, `--color-primary-fixed`, `--color-surface-container-low/lowest`, `--color-outline-variant`, `--gradient-primary`, `--radius-xl`, `--radius-button`/`--radius-default`, `--radius-chip`, `--shadow-ambient`. Status chips ("ENCRYPTED FEED", "AI MONITORING") use `--color-secondary-container` + `--color-on-secondary-container`.

---

## Decision 7 — Student name display and placeholder

**Question**: FR-009 requires the student's name to be displayed with a placeholder while the keychain read resolves. What HTML pattern achieves this without blocking the input?

**Decision**: The card renders a `<p>` element with ID `#student-name` initialised to a non-breaking space or skeleton class. `exam-code.js` calls `window.bridge.getSavedSession()` on `DOMContentLoaded`, then sets `textContent` to `firstName + ' ' + lastName` when resolved. The input and button are rendered and focusable immediately. If the session call fails (no session), main.js routes back to login before this page even loads — so `getSavedSession()` will always succeed here and the placeholder duration is < 100 ms in practice.

**Rationale**: `getSavedSession()` is a local keytar read — sub-millisecond on modern hardware. The placeholder is a defensive UX measure for slow keychains, not a structural loading state.
