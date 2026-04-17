# Tasks: Result Page

**Feature**: `005-result-page` | **Branch**: `005-result-page` | **Date**: 2026-04-17
**Input**: [plan.md](plan.md), [spec.md](spec.md), [data-model.md](data-model.md), [contracts/bridge-result.md](contracts/bridge-result.md), [research.md](research.md)

**Tests**: Not generated — no TDD requirement in spec.md.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Parallelizable — targets a different file or independent section; no dependency on an incomplete task
- **[Story]**: Which user story this task belongs to (US1 / US2 / US3)
- No story label on Setup / Foundation / Polish tasks
- Exact file paths are included in every task description

---

## Phase 1: Setup

No new top-level directories are required. All source changes are edits or additions within existing directories. Proceed directly to Foundation.

---

## Phase 2: Foundation (Blocking Prerequisites)

**Purpose**: Cross-spec bug fix + Python bridge extension + two new IPC channels + renderer file scaffolding. Every user story phase depends on this phase being complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T001 Remove the `examSession = null;` line from the `bridge:submit-exam` success path in `frontend/main.js` — preserves `examSession.attemptId` for the US1 recovery path (research.md Decision 2; spec §Assumptions)
- [x] T002 [P] Add `map_lms_result_error(status, body)` error-mapper function to `python_bridge/exam.py` — maps LMS HTTP error codes to typed error objects; mirror the structure of the existing `map_lms_submit_error()` function in the same file
- [x] T003 Add `POST /result` route to the `exam_bp` Blueprint in `python_bridge/exam.py` — reads `{ attemptId, token }` from the JSON request body; calls `GET /api/QuizAttempts/result/{attemptId}` with `Authorization: Bearer <token>`; returns the LMS body on HTTP 200 or calls `map_lms_result_error()` on any other status (depends T002)
- [x] T004 Add `bridge:get-result` `ipcMain.handle` handler in `frontend/main.js` — reads `examSession?.attemptId` from module scope; if `attemptId` is absent returns `{ ok: false, redirect: 'login' }`; reads `accessToken` from `sessionMemory?.accessToken` or keytar; POSTs `{ attemptId, token }` to `http://127.0.0.1:${bridgePort}/result`; on HTTP 200 sets module-scope `submitResult = body` and returns `{ ok: true, data: body }`; on error returns `{ ok: false, error: body }` (contracts/bridge-result.md §Channel 2)
- [x] T005 Add `bridge:clear-submit-result` `ipcMain.handle` handler in `frontend/main.js` — sets `submitResult = null` and `examSession = null`, then calls `mainWindow.loadFile(path.join(__dirname, 'pages/exam-code/index.html'))` to navigate the window to the Exam Access page (contracts/bridge-result.md §Channel 3)
- [x] T006 Add `'bridge:get-result'` and `'bridge:clear-submit-result'` to the `ALLOWED_INVOKE_CHANNELS` array in `frontend/preload.js` and expose `getResult: () => ipcRenderer.invoke('bridge:get-result')` and `clearSubmitResult: () => ipcRenderer.invoke('bridge:clear-submit-result')` on the `window.bridge` contextBridge object alongside the existing methods (depends T004, T005)
- [x] T007 [P] Replace the `<!-- Placeholder -->` body content in `frontend/pages/result/index.html` with full semantic HTML — keep existing `<head>` intact; add `<link rel="stylesheet" href="result.css" />`; inside `<body>` add `<main class="result-container">`; inside main: a `<section class="score-summary">` with child elements for exam title (`<h1 id="exam-title">`), exam code (`<p id="exam-code">`), score (`<p id="score">`), percentage (`<p id="percentage">`), and pass/fail chip (`<span id="pass-fail" class="pass-chip">`); a `<section class="breakdown" id="breakdown-section" hidden>` containing `<ul id="breakdown-list">`; a `<button id="back-btn">Back to Home</button>`; close with `<script src="result.js"></script>` before `</body>`
- [x] T008 [P] Create `frontend/pages/result/result.css` — define styles for `.result-container`, `.score-summary`, `#score`, `#percentage`, `.pass-chip`, `.pass-chip.pass`, `.pass-chip.fail`, `.breakdown`, `.breakdown-item`, `.breakdown-item.correct`, `.breakdown-item.incorrect`, and `#back-btn`; `.breakdown` MUST use `overflow-y: auto` so 50+ items scroll without breaking layout (FR-007); use only existing CSS custom property tokens from `design-tokens.css` — pass state: `var(--color-primary)` text + `var(--color-primary-container)` background; fail state: `var(--color-error)` text + `var(--color-primary-fixed)` background; body text: `var(--font-body)`; zero hardcoded hex or font-family strings (SC-005; note: `--color-success` and `--color-destructive` do NOT exist in the token set — use the tokens listed here)
- [x] T009 Create `frontend/pages/result/result.js` — `const PASS_THRESHOLD = 50;`; on `DOMContentLoaded`: (1) disable `#back-btn` immediately; (2) call `window.bridge.getSubmitResult()`; (3) if result is `{ ok: false }` fall through to `window.bridge.getResult()` — if that also returns `{ ok: false, redirect: 'login' }` or `{ ok: false, error }` call `window.location.replace('../login/index.html')` and return; (4) on success store the result in module-level `let resultData` and re-enable `#back-btn`; render functions (`renderScore`, `renderBreakdown`) are scaffolded as empty stubs here and filled in T011 and T013 respectively (depends T006; HTML DOM IDs from T007 and CSS classes from T008 must exist before implementing render functions; FR-004 loading-state — remediation C1)
- [x] T010 Verify the `<meta http-equiv="Content-Security-Policy">` in `frontend/pages/result/index.html` permits `result.css` under `style-src 'self'` and `result.js` under `script-src 'self'` — update CSP only if those directives are absent or too restrictive (depends T007)

**Checkpoint**: Foundation complete — bridge `/result` route live, two new IPC channels registered in main.js + preload.js, HTML shell in place, result.css created, result.js entry point runs and redirects on missing data. All user stories can now be implemented.

---

## Phase 3: User Story 1 — View Exam Score and Grade (P1) 🎯 MVP

**Goal**: Populate the score summary card — exam title, exam code, score/total, percentage, and pass/fail chip — from the in-memory `submitResult` (or recovered result).

**Independent Test**: In main.js, temporarily seed `submitResult` with the data from `specs/005-result-page/mocks/result-success.json`; navigate to `frontend/pages/result/index.html`; verify exam title, code, "7 / 10", "70.0%", and a "Passed" chip are all visible. Repeat with `result-failed.json` (score 3, 30%) and verify "Failed" chip.

- [x] T011 [US1] Implement `renderScore(data)` in `frontend/pages/result/result.js` — set `document.getElementById('exam-title').textContent = data.quizTitle`; set `document.getElementById('exam-code').textContent = data.quizCode`; set `document.getElementById('score').textContent = \`${data.score} / ${data.totalQuestions}\``; set `document.getElementById('percentage').textContent = \`${data.percentage.toFixed(1)}%\``; set `document.getElementById('pass-fail').textContent` to `'Passed'` or `'Failed'` and toggle CSS class `pass` / `fail` based on `data.percentage >= PASS_THRESHOLD` (depends T009)
- [x] T012 [US1] Wire `renderScore(resultData)` call into the `DOMContentLoaded` handler in `frontend/pages/result/result.js` immediately after `resultData` is assigned and before `renderBreakdown` (depends T011)

**Checkpoint**: User Story 1 fully functional — score summary renders correctly for both pass and fail scenarios.

---

## Phase 4: User Story 2 — Review Per-Question Breakdown (P2)

**Goal**: Always-visible per-question breakdown list showing question text, student answer, correct answer, and a correct/incorrect indicator. Hidden when `questions` array is empty or absent (FR-008).

**Independent Test**: Load result page with `mocks/result-success.json` (10 questions, mix of correct/incorrect); verify all 10 rows render with correct content and `correct`/`incorrect` CSS class. Load with a mock where `questions: []`; verify `.breakdown` section stays hidden.

- [x] T013 [US2] Implement `renderBreakdown(questions)` in `frontend/pages/result/result.js` — if `!questions || questions.length === 0` return immediately leaving `#breakdown-section` hidden (FR-008); otherwise remove the `hidden` attribute from `document.getElementById('breakdown-section')`; for each entry in `questions` create a `<li class="breakdown-item ${q.isCorrect ? 'correct' : 'incorrect'}">` with child `<span>` elements for `questionText`, `studentChoice`, `correctChoice`, and a status indicator (`'Correct'` or `'Incorrect'`); append all `<li>` elements to `#breakdown-list` (depends T009)
- [x] T014 [US2] Wire `renderBreakdown(resultData.questions)` call into the `DOMContentLoaded` handler in `frontend/pages/result/result.js` after `renderScore(resultData)` (depends T013)

**Checkpoint**: User Stories 1 and 2 both functional — full result display with per-question review.

---

## Phase 5: User Story 3 — Exit to Home After Reviewing (P3)

**Goal**: "Back to Home" button clears `submitResult` and `examSession` in main.js and navigates the Electron window to the Exam Access page.

**Independent Test**: View the Result page; click "Back to Home"; verify the window navigates to `frontend/pages/exam-code/index.html`. Navigate back to the result page (e.g., via `loadFile` in devtools); verify the page immediately redirects to Login (confirming both variables are null).

- [x] T015 [US3] Add `document.getElementById('back-btn').addEventListener('click', () => window.bridge.clearSubmitResult())` inside the `DOMContentLoaded` handler in `frontend/pages/result/result.js` — navigation is handled entirely by main.js inside `bridge:clear-submit-result`; no renderer-side `window.location` call is needed (depends T009)

**Checkpoint**: Full exam workflow complete — student can exit to home, stale attempt data cleared, ready for next exam or logout.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T016 [P] Audit `frontend/pages/result/result.css` — confirm every colour, spacing, and typography value references a CSS custom property token; grep for any literal hex (`#`), `rgb(`, `hsl(`, hardcoded `px` font-sizes not from tokens, or hardcoded font-family strings and replace with the appropriate token (SC-005, FR-006)
- [x] T017 [P] Audit `frontend/pages/result/index.html` — confirm `<head>` links both `../../assets/components.css` (shared tokens) and `result.css` (page-specific styles), and that `result.js` is referenced as `<script src="result.js"></script>` immediately before `</body>`

---

## Dependencies

```
T002 ──────────────► T003    (exam.py — mapper before route)
T004 ──┐
T005 ──┴──────────► T006    (preload.js needs both channel names)
T007 ──┐
T008 ──┼──────────► T009    (result.js needs HTML DOM IDs + CSS class names)
T006 ──┘
T007 ──────────────► T010   (CSP check on finalized HTML)
T009 ──► T011 ──► T012      (US1: render function then wire)
T009 ──► T013 ──► T014      (US2: render function then wire)
T009 ──► T015               (US3: event listener in DOMContentLoaded)
T008 ──► T016               (CSS audit after result.css created)
T010 ──► T017               (polish after HTML finalized)
```

---

## Parallel Execution Examples

### Foundation phase

```
Track A (main.js):   T001 → T004 → T005    (sequential: all edit main.js)
Track B (exam.py):   T002 → T003           (independent of Track A)
Track C (HTML/CSS):  T007  T008            (independent of A and B; run in parallel with each other)

Sync point:  T006 (waits for T004, T005)
             T009 (waits for T006, T007, T008)
             T010 (waits for T007)
```

### User story phases

```
Phase 3 (US1):  T011 → T012   (result.js only)
Phase 4 (US2):  T013 → T014   (result.js only, after Phase 3)
Phase 5 (US3):  T015          (result.js only, after Phase 4)
```

### Polish phase

```
T016  T017   (independent — different files / different concerns)
```

---

## Implementation Strategy

**MVP = Phase 2 + Phase 3** (T001–T012): Foundation + score summary = a functional Result page. Students see their score. Phases 4–5 add educational value and workflow completion.

| Phase | Tasks | Delivers |
|-------|-------|---------|
| Phase 2 | T001–T010 | Foundation — IPC, bridge, HTML/CSS/JS scaffold |
| Phase 3 | T011–T012 | **MVP** — score and pass/fail visible (US1) |
| Phase 4 | T013–T014 | Per-question review visible (US2) |
| Phase 5 | T015      | Back to Home + state cleared (US3) |
| Phase 6 | T016–T017 | Design system + link audit |
| Phase 7 | T018–T022 | Visual redesign — match `Designs/Result_page/` editorial layout |

---

## Phase 7: Visual Redesign — Match Designs/Result_page/

**Purpose**: Upgrade the functional Result page (T001–T017 complete) to match the editorial "Ethereal Authority" layout in `Designs/Result_page/screen.png`. Three frontend files change; no backend or IPC changes. All previous DOM IDs (`#exam-title`, `#score`, etc.) are renamed to new IDs that the updated `renderScore` and `renderBreakdown` functions will populate.

**Reference file**: `Designs/Result_page/code.html` (Tailwind prototype) — adapt to CSS custom property tokens; strip CDN links; keep the same visual output.

**Design → Data field decisions**:
- Completion date → **OMIT** (not in data model)
- Download Report button → **OMIT** (no backend PDF support)
- Per-question topic tags → **OMIT** (not in `QuestionResult`)
- Per-question explanation quote → **OMIT** (not in `QuestionResult`)
- Pagination → **OMIT** — keep scrollable `<ul>` (data count is unbounded and unknown at render time)
- Category chip → populate with `data.quizCode`
- SVG progress ring → driven by `data.percentage`
- Filter tabs → client-side only (no new IPC)

**Independent Test**: `npm start` → log in → submit exam → Result page shows glassmorphic hero card with SVG ring, question cards with correct/incorrect variants, and filter tabs that update the visible list. "Back to Home" still navigates to exam-code page.

- [x] T018 Restructure `frontend/pages/result/index.html` — replace entire `<body>` content with: (1) `<header class="page-header">` containing Lumina AI logo SVG + `<nav>` with "Back to Home" anchor (id `back-btn`) and "Exam Results" active link; (2) `<main class="page-main">` containing a page-title `<div>` with eyebrow `<p class="eyebrow">ACADEMIC ASSESSMENT</p>` and `<h2 class="page-title">Exam Results</h2>`; (3) `<section class="hero-card" id="hero-card">` containing a left column with `<span id="exam-code-chip" class="category-chip"></span>`, `<h3 id="exam-title"></h3>`, `<p class="proctoring-status">AI Proctoring Status: Clean</p>` and a right column `.score-ring-wrap` with `<svg id="progress-ring" viewBox="0 0 192 192">` (two `<circle>` elements — track + progress — and a `<defs>` with `<linearGradient id="ring-gradient">`), plus a `<div class="ring-overlay">` containing `<p id="percentage-text"></p>` and `<p id="score-text"></p>`; below `.score-ring-wrap` add `<span id="pass-fail-chip" class="pass-fail-chip"></span>` (sibling of `.score-ring-wrap`, inside the right column div, below the SVG wrapper); (4) `<section class="breakdown-section">` with a flex header row containing `<h3 class="breakdown-title">Question Breakdown</h3>` and `<div class="filter-tabs">` with three `<button class="filter-tab" data-filter="all|correct|incorrect">` buttons each containing a count `<span>` (ids `count-all`, `count-correct`, `count-incorrect`); `<ul id="breakdown-list"></ul>` below; (5) `<footer class="page-footer">` with static Lumina AI branding text; close with `<script src="result.js"></script>` before `</body>`; keep existing CSP `<meta>` unchanged (style-src/script-src 'self' already covers result.css + result.js)

- [x] T019 [P] Replace entire contents of `frontend/pages/result/result.css` — write styles for: `.page-header` (position sticky, top 0, z-index 50, `background: rgba(248,249,250,0.8)`, backdrop-filter blur 12px, border-bottom 1px solid with `color-mix(in srgb, var(--color-outline-variant) 20%, transparent)`, box-shadow var(--shadow-ambient)); `.page-main` (max-width 960px, margin auto, padding 3rem 1.5rem); `.eyebrow` (font-family var(--font-body), font-size var(--font-size-label-md), letter-spacing 0.1em, text-transform uppercase, color var(--color-primary), font-weight 700, margin-bottom 0.5rem); `.page-title` (font-family var(--font-display), font-size var(--font-size-display-lg), font-weight 800, color var(--color-on-surface), letter-spacing -0.02em); `.hero-card` (display flex, flex-wrap wrap, gap 2rem, `background: rgba(255,255,255,0.7)`, backdrop-filter blur 24px, border: 1px solid with outline-variant 20% opacity, border-radius var(--radius-card), padding 2rem, box-shadow var(--shadow-ambient), margin-top 2.5rem); `.hero-left` (flex 1, display flex, flex-direction column, gap 1rem); `.category-chip` (display inline-block, padding 0.25rem 0.75rem, border-radius var(--radius-chip), background var(--color-secondary-container), color var(--color-on-secondary-container), font-size var(--font-size-label-md), font-weight 700, letter-spacing 0.05em, text-transform uppercase); `#exam-title` (font-family var(--font-display), font-size var(--font-size-headline-md), font-weight 700, color var(--color-on-surface)); `.proctoring-status` (font-family var(--font-body), font-size var(--font-size-body-lg), color var(--color-primary), font-weight 600); `.score-ring-wrap` (position relative, width 192px, height 192px, flex-shrink 0); `#progress-ring` (width 100%, height 100%, transform rotate(-90deg)); `.ring-overlay` (position absolute, inset 0, display flex, flex-direction column, align-items center, justify-content center); `#percentage-text` (font-family var(--font-display), font-size var(--font-size-display-lg), font-weight 900, color var(--color-on-surface), line-height 1); `#score-text` (font-family var(--font-body), font-size var(--font-size-body-lg), color var(--color-on-surface-variant)); `.pass-fail-chip` (display inline-block, padding 0.375rem 1.25rem, border-radius var(--radius-chip), font-family var(--font-body), font-size var(--font-size-label-md), font-weight 600, letter-spacing 0.05em, text-transform uppercase, margin-top 0.75rem); `.pass-fail-chip.pass` (color var(--color-primary), background var(--color-primary-container)); `.pass-fail-chip.fail` (color var(--color-error), background var(--color-primary-fixed)); `.breakdown-section` (margin-top 3rem); `.breakdown-header` (display flex, align-items center, justify-content space-between, margin-bottom 1.5rem); `.breakdown-title` (font-family var(--font-display), font-size var(--font-size-headline-md), font-weight 700, color var(--color-on-surface)); `.filter-tabs` (display flex, gap 0.5rem); `.filter-tab` (font-family var(--font-body), font-size var(--font-size-label-md), font-weight 700, background var(--color-surface-container-low), border: 1px solid with outline-variant 20% opacity, border-radius var(--radius-chip), padding 0.375rem 0.75rem, cursor pointer, color var(--color-on-surface-variant)); `.filter-tab.active` (background var(--color-primary), color var(--color-on-primary), border-color transparent); `#breakdown-list` (list-style none, display flex, flex-direction column, gap 1rem, max-height 70vh, overflow-y auto, padding-right 0.25rem); `.question-card` (background var(--color-surface-container-lowest), border-radius var(--radius-card), padding 1.5rem, transition box-shadow 0.15s); `.question-card:hover` (box-shadow var(--shadow-ambient)); `.question-card.correct` (border-left: 4px solid transparent, position relative) — use `background: linear-gradient(var(--color-surface-container-lowest), var(--color-surface-container-lowest)) padding-box, var(--gradient-primary) border-box` approach OR simply `border-left: 4px solid var(--color-primary)`; `.question-card.incorrect` (border-left: 4px solid var(--color-error)); `.q-header` (display flex, gap 1rem, align-items flex-start, margin-bottom 1rem); `.q-icon` (width 2rem, height 2rem, border-radius var(--radius-chip), display flex, align-items center, justify-content center, flex-shrink 0, font-size 1rem, font-weight 700); `.q-icon.correct` (background var(--gradient-primary), color var(--color-on-primary)); `.q-icon.incorrect` (background var(--color-error-container), color var(--color-on-error-container)); `.q-text` (font-family var(--font-display), font-size var(--font-size-body-lg), font-weight 700, color var(--color-on-surface)); `.answer-boxes` (display flex, flex-direction column, gap 0.75rem, margin-top 0.5rem); `.answer-box` (padding 0.75rem, border-radius var(--radius-button)); `.answer-box.your-answer` (background var(--color-surface-container-low), border: 1px solid with primary 10% opacity); `.answer-box.your-answer.incorrect` (background: color-mix(in srgb, var(--color-error-container) 20%, transparent), border-color: color-mix(in srgb, var(--color-error) 10%, transparent)); `.answer-box.correct-answer` (background: color-mix(in srgb, var(--color-primary) 5%, transparent)); `.answer-box-label` (font-family var(--font-body), font-size var(--font-size-label-md), letter-spacing 0.08em, text-transform uppercase, font-weight 700, margin-bottom 0.25rem); `.answer-box.your-answer .answer-box-label` (color var(--color-on-surface-variant)); `.answer-box.your-answer.incorrect .answer-box-label` (color var(--color-error)); `.answer-box.correct-answer .answer-box-label` (color var(--color-primary)); `.answer-box-value` (font-family var(--font-body), font-size var(--font-size-body-lg), color var(--color-on-surface)); `.page-footer` (margin-top 3rem, padding 2rem 1.5rem, border-top: 1px solid with outline-variant 10% opacity, background: color-mix(in srgb, var(--color-surface-container-low) 50%, transparent), display flex, flex-wrap wrap, justify-content space-between, align-items center, gap 1rem, font-family var(--font-body), font-size var(--font-size-label-md), color var(--color-on-surface-variant)); zero hardcoded hex, rgb(), hsl(), or bare font-family strings — all values via CSS custom properties (FR-006, SC-005)

- [x] T020 [P] Add `renderProgress(pct)` function to `frontend/pages/result/result.js` — `const r = 88; const circumference = 2 * Math.PI * r;` (matches SVG circle `r="88"` from T018); set `document.getElementById('progress-ring').querySelector('.progress-circle').style.strokeDasharray = circumference`; set `stroke-dashoffset = circumference * (1 - pct / 100)`; populate `document.getElementById('percentage-text').textContent` with `\`${pct.toFixed(1)}%\`` and `document.getElementById('score-text')` via the calling `renderScore` function (depends T018)

- [x] T021 [P] Add `initFilterTabs(questions)` function to `frontend/pages/result/result.js` — set `document.getElementById('count-all').textContent = questions.length`; set `document.getElementById('count-correct').textContent = questions.filter(q => q.isCorrect).length`; set `document.getElementById('count-incorrect').textContent = questions.filter(q => !q.isCorrect).length`; query all `.filter-tab` buttons and attach `click` listeners — on click: remove `active` class from all tabs, add `active` class to clicked tab, read `data-filter` value, iterate over `#breakdown-list li` items and toggle `hidden` attribute based on item's `data-correct` attribute (`"true"` for correct, `"false"` for incorrect, show all when filter is `"all"`); activate the "All" tab by default (depends T018)

- [x] T022 Update `renderScore(data)`, `renderBreakdown(questions)`, and the `DOMContentLoaded` handler in `frontend/pages/result/result.js` — `renderScore`: replace old ID references (`#exam-title`, `#exam-code`, `#score`, `#percentage`, `#pass-fail`) with new IDs from T018: set `#exam-title` (same id), `#exam-code-chip` (was `#exam-code`), `#score-text` text via `\`${data.score} / ${data.totalQuestions} Score\``, call `renderProgress(data.percentage)` at the end of renderScore; also populate `#pass-fail-chip`: set textContent to `'Passed'` or `'Failed'` (threshold `data.percentage >= PASS_THRESHOLD`), add class `pass` or `fail`, remove the opposite class; `renderBreakdown`: replace existing `<li>` innerHTML template with new question card markup — `<div class="q-header"><div class="q-icon ${q.isCorrect ? 'correct' : 'incorrect'}">${q.isCorrect ? '✓' : '✗'}</div><p class="q-text">${escapeHtml(q.questionText)}</p></div><div class="answer-boxes"><div class="answer-box your-answer ${q.isCorrect ? '' : 'incorrect'}"><p class="answer-box-label">${q.isCorrect ? 'Your Selection' : 'Your Selection (Incorrect)'}</p><p class="answer-box-value">${escapeHtml(q.studentChoice)}</p></div><div class="answer-box correct-answer"><p class="answer-box-label">Correct Answer</p><p class="answer-box-value">${escapeHtml(q.correctChoice)}</p></div></div>` — set `data-correct` attribute on `<li>` to `String(q.isCorrect)`; set `li.className = \`question-card ${q.isCorrect ? 'correct' : 'incorrect'}\``; remove `#breakdown-section hidden` toggle (section is always visible per new design); in `DOMContentLoaded`: after `renderBreakdown`, call `initFilterTabs(resultData.questions ?? [])`; remove old `back-btn` click listener registration (back-btn is now the header "Back to Home" anchor — wire it here: `document.getElementById('back-btn').addEventListener('click', (e) => { e.preventDefault(); window.bridge.clearSubmitResult(); })`) (depends T020, T021)

---

## Phase 7 Dependency Graph

```
T018 ──┬──────────────► T020   (renderProgress needs SVG circle in DOM)
       ├──────────────► T021   (initFilterTabs needs filter buttons in DOM)
       └──────────────► T022   (renderScore/renderBreakdown need new IDs)
T020 ──► T022                  (renderScore calls renderProgress)
T021 ──► T022                  (DOMContentLoaded calls initFilterTabs)
T019     (independent — CSS only, no DOM dependency)
```

## Phase 7 Parallel Execution

```
Track A:  T018 → T022           (HTML structure then JS update)
Track B:  T019                  (CSS — fully independent of all other T7 tasks)
Track C:  T020, T021            (JS helpers — independent of each other, depend on T018)

Sync:     T022 waits for T018, T020, T021
```
