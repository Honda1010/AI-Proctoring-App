# Research: Pre-Exam Instructions Page

**Phase**: 0 — Outline & Research  
**Feature**: `012-exam-instructions-page`  
**Date**: 2026-05-07

All unknowns were resolved by reading the existing codebase. No external research needed.

---

## Decision 1 — Page-to-page navigation mechanism

**Decision**: Use `window.location.href = '../exam-instructions/index.html'` (from ai-readiness)
and `window.location.href = '../exam/index.html'` (from the instructions page to exam).

**Rationale**: Every existing renderer page uses relative `window.location.href` for forward
navigation and `window.location.replace(...)` for session guard redirects. No central router
exists in `main.js` for renderer-to-renderer navigation — `mainWindow.loadFile(...)` calls in
main.js are only used in the startup sequence and by IPC handlers triggered from the main process
(e.g. after logout). The spec reference to "loadPage pattern" was conceptual; no new main.js
entry is needed.

**Alternatives considered**:
- `window.bridge.navigate(...)` IPC call: Not used anywhere in the codebase for page transitions.
  The bridge handles data operations, not page routing.
- `mainWindow.loadFile(...)` via IPC: Not used for renderer-initiated navigation; would add
  unnecessary round-trip complexity.

---

## Decision 2 — Session guard redirect target

**Decision**: Redirect to `'../login/index.html'` when `getExamSession()` returns no valid session.

**Rationale**: `exam.js` redirects to `'../login/index.html'` on session guard failure (line 78).
The instructions page sits just before exam.js in the flow and shares the same prerequisite
(a valid `examSession` with `attemptId`). Using the same target maintains consistency with the
deepest pages in the flow.

**Alternatives considered**:
- Redirect to `'../exam-code/index.html'`: Used by `identity-verification.js` and `ai-readiness.js`
  for their guards. Those pages are earlier in the flow and know the student has a login session
  but may not have an exam session. By the time the instructions page loads, if there's no
  `examSession`, something is fundamentally wrong — sending the user to login is more correct.

---

## Decision 3 — Loading state / spinner pattern

**Decision**: Mirror the `exam-code.js` loading pattern exactly:
- Two child elements inside the button: `<span id="btnText">` and `<span class="spinner" id="btnSpinner" hidden aria-hidden="true">`
- On click: `startBtn.disabled = true; btnText.textContent = 'Starting…'; btnSpinner.hidden = false;`
- No re-enable path (navigation supersedes it; if it fails the user is redirected to login)

**Rationale**: `exam-code.js` is the canonical loading-button implementation in the project
(see `setLoading()` function in `exam-code.js`). Same HTML structure, same CSS classes, same
JS pattern. SC-005 requires visual consistency with login and exam-code loading states.

---

## Decision 4 — Icon vocabulary for 8 rules

**Decision**: Use inline SVG paths sourced from the existing project SVG vocabulary, picking the
closest semantic match for each rule. All SVGs must work in a 24×24 viewBox with `currentColor`.

| Rule | Icon concept | SVG source reference |
|------|-------------|----------------------|
| Quiet Environment | volume-off / speaker muted | New — muted speaker path (standard Material icon shape) |
| Full-Screen Mode | fullscreen arrows | New — fullscreen-expand icon (4 corner arrows) |
| No Unauthorized Devices | phone with ban | New — mobile phone outline |
| Room Privacy | person alone / door | Person outline (already in identity-verification) |
| No Leaving Seat | seat / person seated | New — person-seat icon |
| Screen Focus | eye | Eye outline (already in identity-verification) |
| No Virtual Machines | server / VM | New — server/stack icon |
| No Unauthorized Keystrokes | keyboard | New — keyboard outline |

All icons are simple 2–3 path SVGs, styled with `currentColor` and `stroke`, matching the
established icon style throughout the project (no fill-heavy or complex icons).

**Alternatives considered**:
- External icon library (Heroicons, Material Symbols CDN): Blocked by CSP `script-src 'self'`
  and `font-src 'self' data:`. No external resources permitted.
- Image files (.svg, .png): Would require `img-src` in CSP and add asset management overhead.

---

## Decision 5 — Sticky footer CSS approach

**Decision**: The card is a CSS flex column with `overflow: hidden`. The rules list is
`overflow-y: auto; flex: 1`. The footer uses `position: sticky; bottom: 0` within the card's
flex context, backed by a `background-color: var(--color-surface-container-lowest)` so it
visually lifts off the list content when scrolled.

**Rationale**: Confirmed by Q5 clarification. `position: sticky` within a flex column is
well-supported in Electron 33 (Chromium 130+). It keeps the footer attached to the card
(not the viewport), consistent with the design system's "card-contained" layout philosophy.

**Alternatives considered**:
- `position: fixed`: Rejected (Q5 clarification — breaks card containment, z-index conflicts
  with potential future modals).
- JavaScript scroll listener + `bottom: 0` recalc: Unnecessary complexity when CSS sticky works.

---

## Summary of Resolved Unknowns

All items from the spec were fully resolved by codebase inspection. No external dependencies,
API integrations, or new infrastructure are required. The feature is a self-contained HTML/CSS/JS
page following established project conventions.
