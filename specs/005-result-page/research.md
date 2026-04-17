# Research: Result Page

**Branch**: `005-result-page` | **Date**: 2026-04-17  
**Input**: Unknowns extracted from `spec.md` Technical Context + best-practice tasks

---

## Decision 1 — Token delivery for `GET /api/QuizAttempts/result/{attemptId}`

**Question**: The recovery path (FR-004) calls `GET /api/QuizAttempts/result/{attemptId}` which requires `Authorization: Bearer <token>`. How does the JWT reach the Python bridge given the renderer never holds tokens?

**Decision**: Identical pattern to every prior spec (002, 003, 004). main.js reads the access token from `sessionMemory?.accessToken` or from keytar (`access-token` key), then passes it as `"token"` in the JSON body of the `POST /result` request it sends to the Python bridge. The bridge reads the value, attaches it as `Authorization: Bearer` on the outbound LMS `GET` call, then discards it — never logged, stored, or returned in any response.

Note: The bridge endpoint receives a `POST` from main.js (easier to pass a body) but calls `GET` on the LMS. This asymmetry is consistent with how `bridge:start-exam` and `bridge:submit-exam` work.

**Rationale**: Symmetric with all prior token delivery patterns. main.js already owns the token — it just includes it in the bridge request body. No new security surface is opened.

**Alternatives considered**:
- URL query param: Token appears in HTTP access logs. Rejected.
- Separate IPC "get token" from bridge: IPC is renderer ↔ main only; bridge cannot call main. Rejected.

---

## Decision 2 — ExamSession lifetime: do NOT null on submit

**Question**: Spec 004 implementation sets `examSession = null` in main.js immediately after a successful `bridge:submit-exam`. But spec 005 recovery path (FR-004) needs `examSession?.attemptId` when `submitResult` is absent. Under the current implementation these two requirements are contradictory.

**Decision**: Spec 005 supersedes spec 004's `examSession = null` on submit. The `bridge:submit-exam` handler in main.js MUST be modified to **not** null `examSession` at submission time. Instead, `examSession` is cleared only when the student clicks "Back to Home" (FR-005), via the new `bridge:clear-submit-result` handler. This preserves `attemptId` for the recovery path throughout the student's time on the Result page.

**Lifecycle after this change**:
```
Spec 003 bridge:start-exam success  → examSession = { attemptId, ... }
Spec 004 bridge:submit-exam success → submitResult = body  (examSession kept)
Result page load (normal)           → bridge:get-submit-result → submitResult present → render
Result page load (recovery)         → bridge:get-submit-result → null
                                    → bridge:get-result       → examSession.attemptId used
                                    → GET /result/{attemptId} → submitResult set → render
Back to Home clicked                → bridge:clear-submit-result → submitResult = null, examSession = null
App quit                            → all module vars lost
```

**Rationale**: The clarification session (2026-04-17 Q5) explicitly decided: "clear both `submitResult` and `examSession` on Back to Home" — implying examSession persists until then. The spec 005 assumption also states: "The `attemptId` used for recovery will be sourced from `examSession?.attemptId` in main.js (still populated during the exam even after submission completes)."

**Impact on spec 004**: One-line change in main.js `bridge:submit-exam` handler — remove `examSession = null;`.

**Alternatives considered**:
- Store `attemptId` separately in a new module-scope variable: adds redundant state. Rejected.
- Remove recovery path entirely: spec 005 clarification Q4 explicitly chose the recovery path. Rejected.

---

## Decision 3 — IPC channels for result page: count and naming

**Question**: Spec 005 needs three new IPC operations: get-submit-result (already exists), get-result (new, recovery), and clear-submit-result (new, on Back to Home). Should these be new channels or overloaded onto existing ones?

**Decision**: Two new channels are added:
- `bridge:get-result` — calls `GET /result` on the Python bridge, which calls `GET /api/QuizAttempts/result/{attemptId}` on the LMS. Returns `{ ok: true, data }` or `{ ok: false, error }`.
- `bridge:clear-submit-result` — clears both `submitResult` and `examSession` in main.js; navigates to the Exam Access page. Returns `{ ok: true }`. Navigation is handled in main.js, not the renderer, for consistency with `bridge:start-exam`'s UNAUTHORIZED redirect pattern.

The existing `bridge:get-submit-result` is unchanged.

**Rationale**: Separate channels maintain single-responsibility. `bridge:clear-submit-result` doing navigation in main.js follows the pattern set by spec 003 (redirect on UNAUTHORIZED in main.js, not renderer).

**Alternatives considered**:
- Single `bridge:get-or-fetch-result` channel that does both: mixes concerns, harder to test. Rejected.
- Renderer calls `window.location.href` for navigation: puts routing logic in the renderer, breaks the main-process-owns-navigation pattern. Rejected.

---

## Decision 4 — Pass/fail threshold implementation

**Question**: FR-002 says pass threshold is 50% (inclusive) client-side. Where and how is this constant defined?

**Decision**: `const PASS_THRESHOLD = 50;` declared at the top of `result.js`. Pass is determined by `result.percentage >= PASS_THRESHOLD`. The constant is module-scoped (not exported, not configurable at runtime) since it is a fixed business rule with no server input.

**Rationale**: Single constant, single location, trivially readable and changeable. No complexity needed.

**Alternatives considered**:
- Inline literal `>= 50` everywhere: magic number. Rejected.
- Read from `config.json` via IPC: adds IPC complexity for a requirement that is explicitly fixed. Rejected.

---

## Decision 5 — Question breakdown layout

**Question**: The breakdown must display up to 100 questions without layout breaking (FR-007, SC-002). What layout approach handles arbitrary-length lists without breaking the design?

**Decision**: The overall page uses a two-region layout — a fixed-size score summary card at the top and a scrollable breakdown section below. The breakdown section has `overflow-y: auto` and a `max-height` that fills the remaining viewport below the summary card. Each question row is a standard block-flow card. No virtualisation is needed for 100 items in Electron (Chromium handles it trivially).

**Rationale**: CSS `overflow-y: auto` with a viewport-relative `max-height` is the correct pattern for bounded-height scroll regions. 100 items × ~120px each = ~12 000px of content, well within Chromium's rendering budget. No JS-based virtualisation needed.

**Alternatives considered**:
- `position: sticky` header with full-page scroll: entire page scrolls, fixed header clips. More complex. Rejected in favour of single-region scroll.
- Virtual list / windowing: overkill for ≤100 items. Rejected.
