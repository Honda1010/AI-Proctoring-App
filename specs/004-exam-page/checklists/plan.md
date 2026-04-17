# Implementation Plan Checklist: Exam Page

**Purpose**: Author self-review gate before running `/speckit.tasks` — validates that the spec, research, data-model, and contracts are complete, clear, and consistent enough to begin implementation task generation. Tests the quality of requirements written in English, not the implementation itself.
**Created**: 2026-04-16
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [research.md](../research.md) | [data-model.md](../data-model.md)
**Scope**: All 5 risk dimensions — Security & Auth, Timer & Auto-Submit, Data Integrity, UX & Error States, Webcam & Proctoring
**Depth**: Thorough (~38 items)
**Audience**: Author (pre-`/speckit.tasks` self-review)

---

## Requirement Completeness

- [x] CHK001 - Are requirements defined for the case where `examSession.title` or `examSession.duration` is missing or null when the page loads? **Resolved**: Malformed/missing fields treated identically to `{ ok: false }` — redirect to Login. [User decision 2026-04-17]
- [x] CHK002 - Is there an FR covering the "View Flags" button shown in `Designs/Exam_Page/code.html` navigator panel? **Resolved**: Excluded from spec 004. Navigator pills already show flagged state (FR-008 + FR-010); no dedicated button needed. [User decision 2026-04-17]
- [x] CHK003 - Are keyboard navigation requirements defined for interactive exam controls — e.g., can a student tab through choices and press Enter/Space to select, navigate questions with arrow keys? **Resolved**: Out of scope for spec 004; deferred to a future accessibility spec. [User decision 2026-04-17]
- [x] CHK004 - Is there an FR specifying that the timer is paused when a submission is in progress? **Resolved**: Covered by FR-020 edge case ("timer is already paused during submission") and tasks T020/T023 which call `clearInterval(timerInterval)` before the bridge call.
- [x] CHK005 - Are requirements defined for what happens to `answerMap` during an active submission round-trip? **Resolved**: `isSubmitting` guard in T023 sets `pointer-events: none` on all controls before payload is serialised; no concurrent write is possible.
- [x] CHK006 - Does the spec define requirements for the "LIVE FEED" badge on the webcam view? **Resolved**: US6 AS1 explicitly requires the badge; task T009 specifies the `<span class="live-badge">LIVE FEED</span>` element in the HTML.
- [x] CHK007 - Are all user-facing error message strings for non-UNAUTHORIZED failures explicitly specified in the spec? **Resolved**: Exact strings are defined in `contracts/bridge-exam-submit.md`; cross-reference is acceptable for implementation. Tasks T004/T005 quote the strings verbatim.

---

## Requirement Clarity

- [x] CHK008 - Is "full-page loading skeleton (spinner + dimmed placeholder)" in FR-001 specific enough to implement? **Resolved**: Delegated to `Designs/Exam_Page/code.html` prototype; task T010 defines the concrete spinner CSS (`.skeleton-overlay`, `.skeleton-spinner`, `@keyframes spin`).
- [x] CHK009 - Is "warning colour" in FR-015 defined as a concrete CSS token? **Resolved**: `var(--color-error)` per tasks T026 and research Decision-5. Cross-reference to design tokens is acceptable.
- [x] CHK010 - Is the exact letter labelling scheme in FR-003 bounded? **Resolved**: A–Z continues alphabetically with no upper bound. In practice choices are ≤6; label E would appear for a 5th choice.
- [x] CHK011 - Is "filled primary colour" for navigator pill states resolved to a specific token? **Resolved**: `var(--color-primary)` for answered/current, `var(--color-tertiary)` for flagged, per design tokens and tasks T016.
- [x] CHK012 - Is "inline error message" in FR-020 defined with a specific placement? **Resolved**: Floating banner fixed above the bottom navigator bar (`bottom: 80px`), per tasks T020 CSS.
- [x] CHK013 - Is "immediately after the ExamSession is loaded" (FR-014) consistent with FR-001 skeleton sequencing? **Resolved**: Correct sequence is FR-001 → IPC resolves → skeleton hidden → `startTimer()` called. Tasks T012 implement this order explicitly (`startTimer()` called after `examSession = session`).
- [x] CHK014 - Is the exact confirmation modal message string for the "zero answered" case precisely specified? **Resolved**: Exact string is "You haven't answered any questions yet." from the edge cases section. Tasks T021 use this verbatim.
- [x] CHK015 - Is "Camera unavailable" in FR-017 a complete UI requirement? **Resolved**: Delegated to design prototype for styling detail; tasks T030 specify the `.camera-unavailable` placeholder element with `position: absolute; inset: 0` covering the video area.

---

## Requirement Consistency

- [x] CHK016 - FR-013 (manual submit) and FR-016 (auto-submit) both say they use "the same submission path." **Resolved**: FR-020 explicitly distinguishes the two error-recovery paths (timer-resume for manual, timer-frozen for auto). Tasks T023/T025 implement `isAutoSubmit` flag to differentiate. Consistent.
- [x] CHK017 - What is the expected display when a question is simultaneously "current" AND "flagged"? **Resolved**: Flagged takes priority over all states including current. This extends the "flagged > answered" rule already stated in the spec. Tasks T015/T016 implement this (flagged class applied last, overwriting current).
- [x] CHK018 - SC-003 says the submit payload is `{ "answers": [{questionId, choiceId}] }`. But main.js posts `{ attemptId, answers, token }` to bridge. **Resolved**: SC-003 measures the renderer-side answers array only. The bridge body with `attemptId` and `token` is an implementation layer detail. The two definitions are at different layers and not contradictory.
- [x] CHK019 - Is it specified that the UNAUTHORIZED redirect (FR-019) also triggers the FR-018 `beforeunload` webcam cleanup? **Resolved**: `beforeunload` fires on any page navigation including main.js-triggered redirects. Standard browser/Electron behaviour; no additional FR needed.
- [x] CHK020 - FR-021 says no logout control; the design prototype has a "Log Out" link. **Resolved**: FR-021 is explicit. Task T009 does not include a logout element; task T034 includes a design token audit that would catch any accidental additions.

---

## Security & Auth Requirements

- [x] CHK021 - Is it specified how main.js resolves the access token when both `sessionMemory?.accessToken` and keytar are absent? **Resolved**: Inherited from spec 002. Absent token means bridge call is made with `null` token → bridge returns 401 → UNAUTHORIZED path fires → redirect to Login. No additional FR needed.
- [x] CHK022 - Is it explicitly required that the JWT is never present in any IPC response body returned to the renderer — including non-UNAUTHORIZED error paths? **Resolved**: Architecture principle enforced in tasks T004/T005 ("token MUST NOT appear in any log statement, error response, or exception message"). Main.js catch block (T008) returns only a generic `BRIDGE_ERROR` object — no request data echoed.
- [x] CHK023 - Does FR-019 precisely define "clearing the session"? **Resolved**: Task T008 clears all three: `submitResult = null` is NOT cleared (only set on success; UNAUTHORIZED means no submit happened), `examSession = null`, `sessionMemory = null`, and `clearAllKeytarEntries()` — keytar cleared last. Scope is sufficient; `submitResult` is irrelevant on UNAUTHORIZED since submission never completed.
- [x] CHK024 - Is UNAUTHORIZED handling specified as fire-and-forget from the renderer's perspective? **Resolved**: Handler returns `undefined` (bare `return;`); renderer awaits `window.bridge.submitExam()` and receives `undefined`. Analysis finding I1 recommends a `if (!result) return;` guard in T023 so the renderer exits gracefully before the page unloads. Task T023 includes this guard.
- [x] CHK025 - Are requirements defined to ensure `attemptId` is validated as a positive integer before being used in the bridge URL path? **Resolved**: Task T005 Python route validates `attemptId` as a positive integer and returns 400 BRIDGE_ERROR if not — preventing path traversal or type injection into the URL.

---

## Timer & Auto-Submit Requirements

- [x] CHK026 - Is the drift-corrected timer approach (Date.now()-anchored) required by an FR, or is it only in research.md? **Resolved**: SC-004 requires accuracy to ±1 second over 90 minutes, which demands drift correction. Tasks T027 specify `Date.now()` anchoring explicitly. A naive decrement would fail SC-004; this is sufficient constraint.
- [x] CHK027 - Is it specified what the timer renders when `examSession.duration` is malformed? **Resolved**: Treated identically to a missing/null session field — redirect to Login. [User decision 2026-04-17, same as CHK001]
- [x] CHK028 - SC-005 says auto-submit fires "within 1 second of the timer displaying `00:00:00`." Is the 1-second budget for trigger latency or full round-trip? **Resolved**: SC-005 measures trigger latency only (the `setInterval` tick to `submitExam()` call). The full LMS round-trip has no SLA in this spec. Context makes this unambiguous.
- [x] CHK029 - Is the auto-submit retry loop fully specified? **Resolved**: FR-020 + edge case: "timer remains frozen at 00:00:00; the student can retry manually until the submission succeeds or they close the app." Applies indefinitely. Tasks T025 implement the retry button calling `submitExam(autoSubmitted)`.
- [x] CHK030 - What happens if the user answers a question AFTER the timer reaches 00:00:00 but BEFORE auto-submit fires? **Resolved**: `isSubmitting = true` is set before the submit payload is serialised (task T023 guard at top of `submitExam()`). The `.exam-page-loading` CSS disables all choice interactions before the event loop could process a click. No race condition.

---

## Data Integrity Requirements

- [x] CHK031 - Is "unanswered" explicitly defined as "a question with no entry in `answerMap`"? **Resolved**: Yes — `answerMap` is a plain object; presence check is `question.id in answerMap`. A null/zero `choiceId` cannot exist because the only write path is `answerMap[id] = choice.id` from a real DOM element, and IDs come from the LMS session.
- [x] CHK032 - What happens when a student selects the same choice already recorded? **Resolved**: Idempotent — `answerMap[id] = sameId` overwrites with the same value; no visible change; no pill state change. FR-006 ("changing a selection replaces the previous choiceId") covers this; re-selecting the current choice is a degenerate case of changing.
- [x] CHK033 - What happens if a `QuestionItem` has `id` of `0`, `null`, or `undefined`? **Resolved**: Accepted risk. The LMS API guarantees valid positive integer IDs per the spec 003 contract (research Decision 5). If the LMS returns malformed data, the submit payload will be malformed — this is a spec 003/005 data contract issue, not spec 004's responsibility.
- [x] CHK034 - Does the spec require that `FlagSet` is cleared when the exam is submitted? **Resolved**: Moot. On submit success the page navigates to the result page and `exam.js` is garbage-collected. On submit failure, persisting the `flagSet` is the correct behaviour (student should keep seeing their flags while retrying).

---

## UX & Error State Requirements

- [x] CHK035 - Is it specified whether the confirmation modal can be dismissed by pressing Escape or clicking the backdrop? **Resolved**: Cancel/Confirm buttons only. No Escape key, no backdrop click. Exam integrity: accidental dismissal must be impossible. [User decision 2026-04-17]
- [x] CHK036 - Is the loading state during submission described precisely enough to implement? **Resolved**: Loading state disables: choice items, nav pills, flag buttons, jump input, Submit button, Prev/Next buttons — all via `.exam-page-loading` class on `<body>` (task T020). Timer chip is excluded (already paused via `clearInterval` before submission begins).
- [x] CHK037 - Are the exact AI status row labels and their default "Active"/"Inactive" values specified? **Resolved**: Delegated to `Designs/Exam_Page/code.html` prototype. Task T009 lists the 5 rows with their exact labels and states in the HTML structure description. No additional spec FR needed.

---

## Acceptance Criteria Quality

- [x] CHK038 - Can SC-001 ("first question visible within 2 seconds") be objectively verified? **Resolved**: Verifiable via DevTools Performance tab (main thread + IPC call timing) during quickstart.md Scenario 1. No automated measurement tool required for this spec; manual observation with DevTools is sufficient.
- [x] CHK039 - Can SC-006 ("camera indicator light off within 1 second") be deterministically verified? **Resolved**: Accepted limitation. The physical camera indicator light is observable during manual testing on the developer's machine. For CI or machines without a physical light, DevTools media track status (`stream.getTracks()[0].readyState === 'ended'`) can be checked in `beforeunload` callback.
- [x] CHK040 - Are US1–US6 acceptance scenarios specific enough to be deterministically pass/fail? **Resolved**: "(A, B, C, D)" in US1 AS1 is an example, not a fixed maximum. FR-003 is authoritative: "labelled with a sequential letter (A, B, C, … for up to the number of choices provided)" — label E appears for a 5th choice, F for a 6th, etc.
