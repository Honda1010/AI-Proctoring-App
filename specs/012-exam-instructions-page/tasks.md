---
description: "Task list for 012-exam-instructions-page"
---

# Tasks: Pre-Exam Instructions Page

**Input**: `specs/012-exam-instructions-page/` — plan.md, spec.md, research.md, data-model.md, quickstart.md  
**Feature**: `012-exam-instructions-page`  
**Generated**: 2026-05-07

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Parallelisable (different files, no blocking dependencies)
- **[US#]**: User story this task belongs to
- All paths are relative to the repo root

---

## Phase 1: Setup

**Purpose**: Create the new page directory and stub files so all user-story tasks have targets to edit.

- [x] T001 Create `frontend/pages/exam-instructions/index.html` with DOCTYPE, `<head>` (charset, CSP meta, stylesheet links to `../../assets/design-tokens.css`, `../../assets/components.css`, `exam-instructions.css`, and `<title>Exam Instructions</title>`), and empty `<body>` with `<script src="exam-instructions.js"></script>`
- [x] T002 [P] Create `frontend/pages/exam-instructions/exam-instructions.css` as an empty file with a header comment
- [x] T003 [P] Create `frontend/pages/exam-instructions/exam-instructions.js` as an empty file with `'use strict';` and a `DOMContentLoaded` listener stub

**Checkpoint**: Three new files exist; `index.html` opens in Electron without console errors (blank page expected).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the full HTML layout shell — header, card skeleton, and CSS layout tokens. All user-story tasks depend on this structure existing.

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete.

- [x] T004 Add the page-level layout to `frontend/pages/exam-instructions/index.html`: `<header class="ei-header">` (Lumina wordmark + "Secure Environment" shield badge, matching the `iv-header` pattern in `frontend/pages/identity-verification/index.html`); `<main class="ei-root">` containing `<div class="ei-card">` with three child sections: `.ei-card-header` (h1 "Before You Begin" + subtitle paragraph), `<ol id="rulesList" class="ei-rules-list"></ol>` (empty, filled in T006), and `<footer class="ei-footer">` (empty, filled in T007)
- [x] T005 [P] Add CSS layout to `frontend/pages/exam-instructions/exam-instructions.css`: `.ei-root` (full-height flex container, `align-items: flex-start`, `justify-content: center`, `background: var(--color-surface-container-low)`); `.ei-card` (flex column, `max-width: 640px`, `max-height: calc(100vh - var(--header-height) - 4rem)`, `overflow: hidden`, `border-radius: var(--radius-xl)`, `background: var(--color-surface-container-lowest)`, `box-shadow: 0px 12px 32px rgba(0,45,91,0.06)`); `.ei-card-header` (padding `1.5rem 1.5rem 0`); `.ei-title` (Manrope, `font-size: 1.5rem`, `font-weight: 700`, `color: var(--color-on-surface)`); `.ei-subtitle` (Inter, `color: var(--color-on-surface-variant)`, `margin-top: 0.25rem`)

**Checkpoint**: App renders the page with a correctly sized, visually styled card (no rules content yet).

---

## Phase 3: User Story 1 — View Proctoring Rules and Acknowledge (P1) 🎯 MVP

**Goal**: All 8 proctoring rules are visible in a scrollable list. The acknowledgment checkbox controls the enabled/disabled state of the "Start Exam" button.

**Independent Test**: Load `frontend/pages/exam-instructions/index.html` with a valid exam session. Verify all 8 rules render with icon, title, and description. Check the checkbox → "Start Exam" enables. Uncheck → button disables again. Scroll the list → footer always visible.

### Implementation for User Story 1

- [x] T006 [US1] Add all 8 rule `<li>` items to `<ol id="rulesList">` in `frontend/pages/exam-instructions/index.html`. Each `<li class="ei-rule-item">` contains: `<span class="ei-rule-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">…</svg></span>` and `<div class="ei-rule-text"><span class="ei-rule-title">…</span><span class="ei-rule-body">…</span></div>`. Rule content (from spec FR-001): (1) Quiet Environment — volume-off SVG; (2) Full-Screen Mode — fullscreen-expand SVG; (3) No Unauthorized Devices — phone-off SVG; (4) Room Privacy — person-alone SVG; (5) No Leaving Seat — person-seat SVG; (6) Screen Focus — eye SVG; (7) No Virtual Machines — server/stack SVG; (8) No Unauthorized Keystrokes — keyboard SVG. All SVG paths must use `currentColor` stroke, no external references.
- [x] T007 [US1] Add the acknowledgment footer to `<footer class="ei-footer">` in `frontend/pages/exam-instructions/index.html`: `<label class="ei-agree-label"><input type="checkbox" id="agreeCheckbox" class="ei-checkbox" /><span>I have read and agree to all exam rules</span></label>` followed by `<button id="startBtn" class="btn-primary ei-start-btn" disabled><span id="btnText">Start Exam</span><span id="btnSpinner" class="spinner" hidden aria-hidden="true"></span></button>`
- [x] T008 [P] [US1] Add CSS for rule items and footer to `frontend/pages/exam-instructions/exam-instructions.css`: `.ei-rules-list` (`flex: 1; overflow-y: auto; padding: 1rem 1.5rem; margin: 0; list-style: none`); `.ei-rule-item` (flex row, `gap: 0.75rem`, `padding: 0.75rem 0`, `align-items: flex-start`); `.ei-rule-icon` (flex-shrink: 0, `color: var(--color-primary)`); `.ei-rule-title` (Inter medium, `font-size: 0.9375rem`, block, `color: var(--color-on-surface)`); `.ei-rule-body` (Inter, `font-size: 0.875rem`, block, `color: var(--color-on-surface-variant)`, `margin-top: 0.125rem`); `.ei-footer` (`position: sticky; bottom: 0; background: var(--color-surface-container-lowest); padding: 1rem 1.5rem 1.5rem; display: flex; flex-direction: column; gap: 0.75rem`); `.ei-agree-label` (flex row, `gap: 0.625rem`, `align-items: center`, `cursor: pointer`); `.ei-start-btn` (full width, `display: flex; justify-content: center; align-items: center; gap: 0.5rem`)
- [x] T009 [US1] In `frontend/pages/exam-instructions/exam-instructions.js`, inside the `DOMContentLoaded` handler, add checkbox wiring: `const agreeCheckbox = document.getElementById('agreeCheckbox'); const startBtn = document.getElementById('startBtn'); agreeCheckbox.addEventListener('change', () => { startBtn.disabled = !agreeCheckbox.checked; });`

**Checkpoint**: Rules list renders all 8 items. Checkbox toggles button enabled/disabled. Footer stays visible when scrolling on a small window height.

---

## Phase 4: User Story 2 — Navigate to Active Exam (P1)

**Goal**: Clicking "Start Exam" (when enabled) immediately enters a loading state and navigates to the active exam page.

**Independent Test**: Check the acknowledgment checkbox, click "Start Exam". Verify: button becomes disabled, text changes to "Starting…", spinner appears. Verify navigation to `../exam/index.html` occurs. (Exam page's own guard will handle any missing session at this point.)

### Implementation for User Story 2

- [x] T010 [US2] In `frontend/pages/exam-instructions/exam-instructions.js`, add elements for the loading state: `const btnText = document.getElementById('btnText'); const btnSpinner = document.getElementById('btnSpinner');`
- [x] T011 [US2] In `frontend/pages/exam-instructions/exam-instructions.js`, add the Start Exam click handler: `startBtn.addEventListener('click', () => { if (startBtn.disabled) return; startBtn.disabled = true; btnText.textContent = 'Starting…'; btnSpinner.hidden = false; btnSpinner.setAttribute('aria-hidden', 'false'); window.location.href = '../exam/index.html'; });`

**Checkpoint**: Complete the user journey: check checkbox → click "Start Exam" → spinner visible → exam page loads.

---

## Phase 5: User Story 3 — Session Guard: Prevent Unauthorized Access (P1)

**Goal**: Page redirects to login immediately on load if no valid exam session (with `attemptId`) is found — no page content ever renders for unauthenticated access.

**Independent Test**: Clear or invalidate the keychain exam session, then load the instructions page. Confirm immediate redirect to `../login/index.html` with no rules visible. Reload with a valid session and confirm the page renders normally.

### Implementation for User Story 3

- [x] T012 [US3] In `frontend/pages/exam-instructions/exam-instructions.js`, add the session guard at the **top** of the `DOMContentLoaded` callback (before element queries): `const sessionResult = await window.bridge.getExamSession(); if (!sessionResult?.ok || !sessionResult?.data?.attemptId) { window.location.replace('../login/index.html'); return; }`

**Checkpoint**: Manually clear the exam session from the OS keychain, open the instructions page — immediate redirect to login, no flicker of page content.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Wire the upstream navigation change so the full app flow works end-to-end, and validate visual fidelity.

- [x] T013 In `frontend/pages/ai-readiness/ai-readiness.js` line 33, change `window.location.href = '../exam/index.html';` to `window.location.href = '../exam-instructions/index.html';` — this is the only change needed in this file
- [x] T014 [P] Visual review: open the app, run through the full flow (login → exam-code → identity-verification → ai-readiness → exam-instructions → exam). Compare the instructions page against `Designs/Exam _Instructions_Page/screen.png` — confirm typography (Manrope headline, Inter body), surface colours, card shadow, icon colours, sticky footer, and button gradient all match the reference design (SC-003)
- [x] T015 [P] Accessibility pass on `frontend/pages/exam-instructions/index.html`: confirm the `<ol>` list is semantic, all SVG icons have `aria-hidden="true"`, checkbox `<label>` is correctly associated via wrapping, `startBtn` has meaningful disabled state text, spinner `aria-hidden` toggled correctly in T011

**Checkpoint**: Full end-to-end flow works. Exam instructions page is visually correct. All 3 user stories pass their independent tests.

---

## Dependencies

```
T001 → T002, T003 (T002 and T003 can run in parallel after T001)
T004 → T005 (T005 can run in parallel with T004 given separate files)
T001-T003 → T004, T005 (foundation requires files to exist)
T004 → T006, T007 (HTML sections must exist before content is added)
T006, T007 → T008 (CSS selectors reference classes added in T006, T007)
T007 → T009 (checkbox element must exist)
T009 → T010, T011 (element queries in T010 build on T009 element list)
T010 → T011 (btnText/btnSpinner declared before used in handler)
T001 → T012 (JS file must exist)
T004-T011 → T013, T014, T015 (polish after all stories complete)
T013 independent of T014, T015 (parallel)
```

**Story Completion Order**: US3 (T012) can be developed alongside US1 (T006–T009) and US2 (T010–T011) since they all operate in the same JS file, but T012 must be inserted **before** other DOMContentLoaded body statements in the final file.

---

## Parallel Execution Examples

**Group A** (after T001): T002 + T003 — separate files, no conflict  
**Group B** (after T004): T005 + T006 — CSS file vs HTML content, no conflict  
**Group C** (after T007): T008 + T009 — CSS file vs JS file, no conflict  
**Group D** (after all stories): T013 + T014 + T015 — separate files / read-only review  

---

## Implementation Strategy

**MVP Scope**: US1 (T006–T009) + US3 (T012) + setup phases (T001–T005). This gives a fully guarded page that displays all 8 rules and captures acknowledgment — the core value.

**Increment 2**: Add US2 (T010–T011) — Start Exam navigation and loading state.

**Increment 3**: Polish (T013–T015) — wire upstream navigation, visual review, accessibility.

**Total tasks**: 15  
**Parallelisable tasks**: T002, T003, T005, T008, T009 (after T007), T013, T014, T015  
**Critical path**: T001 → T004 → T006 → T007 → T010 → T011 → T013
