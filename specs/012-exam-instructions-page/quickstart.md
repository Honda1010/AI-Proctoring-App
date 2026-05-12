# Quickstart: Pre-Exam Instructions Page

**Feature**: `012-exam-instructions-page`  
**Date**: 2026-05-07

---

## What to build

A single renderer page (`frontend/pages/exam-instructions/`) that:
1. Guards itself against a missing exam session — redirects to login if absent.
2. Displays the 8 fixed proctoring rules with inline SVG icons.
3. Requires the student to tick an acknowledgment checkbox before "Start Exam" enables.
4. On "Start Exam" click: shows a loading state then navigates to `'../exam/index.html'`.

---

## Files to create / edit

| Action | File | Description |
|--------|------|-------------|
| CREATE | `frontend/pages/exam-instructions/index.html` | Page markup |
| CREATE | `frontend/pages/exam-instructions/exam-instructions.css` | Page-scoped styles |
| CREATE | `frontend/pages/exam-instructions/exam-instructions.js` | Page logic |
| EDIT   | `frontend/pages/ai-readiness/ai-readiness.js` | Line 33: change nav target |

**No other files change.**  
No new packages, no CSP modifications, no main.js entries, no IPC channel additions.

---

## ai-readiness.js edit

```js
// BEFORE (line 33):
window.location.href = '../exam/index.html';

// AFTER:
window.location.href = '../exam-instructions/index.html';
```

Only this one line changes. No surrounding logic is touched.

---

## index.html structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'self'; style-src 'self'; script-src 'self'; font-src 'self' data:" />
  <link rel="stylesheet" href="../../assets/design-tokens.css" />
  <link rel="stylesheet" href="../../assets/components.css" />
  <link rel="stylesheet" href="exam-instructions.css" />
  <title>Exam Instructions</title>
</head>
<body>

  <!-- Header (reuse iv-header pattern) -->
  <header class="ei-header">
    <span class="ei-logo"><!-- Lumina wordmark --></span>
    <span class="ei-badge"><!-- "Secure Environment" shield badge --></span>
  </header>

  <!-- Card -->
  <main class="ei-root">
    <div class="ei-card">

      <!-- Card header -->
      <div class="ei-card-header">
        <h1 class="ei-title">Before You Begin</h1>
        <p class="ei-subtitle">Please review the exam rules…</p>
      </div>

      <!-- Rules list (scrollable) -->
      <ol class="ei-rules-list" id="rulesList">
        <!-- 8 × <li class="ei-rule-item"> … </li> -->
      </ol>

      <!-- Sticky footer (acknowledgment + button) -->
      <footer class="ei-footer">
        <label class="ei-agree-label">
          <input type="checkbox" id="agreeCheckbox" class="ei-checkbox" />
          <span>I understand and agree to these exam rules</span>
        </label>
        <button id="startBtn" class="btn-primary ei-start-btn" disabled>
          <span id="btnText">Start Exam</span>
          <span id="btnSpinner" class="spinner" hidden aria-hidden="true"></span>
        </button>
      </footer>

    </div>
  </main>

  <script src="exam-instructions.js"></script>
</body>
</html>
```

---

## exam-instructions.js logic

```js
'use strict';

document.addEventListener('DOMContentLoaded', async () => {
  // ── Session Guard ────────────────────────────────────────────────────────
  const sessionResult = await window.bridge.getExamSession();
  if (!sessionResult?.ok || !sessionResult?.session?.attemptId) {
    window.location.replace('../login/index.html');
    return;
  }

  // ── Elements ─────────────────────────────────────────────────────────────
  const agreeCheckbox = document.getElementById('agreeCheckbox');
  const startBtn      = document.getElementById('startBtn');
  const btnText       = document.getElementById('btnText');
  const btnSpinner    = document.getElementById('btnSpinner');

  // ── Checkbox — gate the button ───────────────────────────────────────────
  agreeCheckbox.addEventListener('change', () => {
    startBtn.disabled = !agreeCheckbox.checked;
  });

  // ── Start Exam ───────────────────────────────────────────────────────────
  startBtn.addEventListener('click', () => {
    if (startBtn.disabled) return;
    // Loading state
    startBtn.disabled      = true;
    btnText.textContent    = 'Starting…';
    btnSpinner.hidden      = false;
    btnSpinner.setAttribute('aria-hidden', 'false');
    // Navigate
    window.location.href = '../exam/index.html';
  });
});
```

---

## exam-instructions.css layout contract

```css
/* Page root — centres the card */
.ei-root {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  min-height: calc(100vh - var(--header-height));
  padding: 2rem 1rem 4rem;
  background: var(--color-surface-container-low);
}

/* Card — flex column, fixed max-width, bounded height for sticky footer */
.ei-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 640px;
  max-height: calc(100vh - var(--header-height) - 4rem);
  overflow: hidden;
  border-radius: var(--radius-xl);
  background: var(--color-surface-container-lowest);
  box-shadow: 0px 12px 32px rgba(0, 45, 91, 0.06);
}

/* Rules list — takes remaining space; scrollable */
.ei-rules-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.5rem;
  margin: 0;
  list-style: none;
}

/* Sticky footer — sticks to bottom of card */
.ei-footer {
  position: sticky;
  bottom: 0;
  background: var(--color-surface-container-lowest);
  padding: 1rem 1.5rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-top: none; /* Design system: no 1px divider lines */
}
```

The `--header-height` custom property is already set by `components.css`.

---

## Rule items markup pattern

Each `<li>` follows this structure:

```html
<li class="ei-rule-item">
  <span class="ei-rule-icon" aria-hidden="true">
    <svg viewBox="0 0 24 24" width="24" height="24" fill="none"
         stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <!-- rule-specific path(s) -->
    </svg>
  </span>
  <div class="ei-rule-text">
    <span class="ei-rule-title">Quiet Environment</span>
    <span class="ei-rule-body">Ensure you are in a quiet, distraction-free space…</span>
  </div>
</li>
```

The 8 rules (from the spec's FR-002 table) are:

| # | Title | Short description |
|---|-------|-------------------|
| 1 | Quiet Environment | Work in a quiet, distraction-free space. |
| 2 | Full-Screen Mode | The exam must run in full-screen mode at all times. |
| 3 | No Unauthorized Devices | Only the authorised computer may be used. |
| 4 | Room Privacy | No other persons should be present in the room. |
| 5 | No Leaving Seat | Remain in your seat for the exam duration. |
| 6 | Screen Focus | Keep your gaze on the screen at all times. |
| 7 | No Virtual Machines | Virtual machines are not permitted. |
| 8 | No Unauthorized Keystrokes | Do not type outside of the answer fields. |

---

## Manual testing checklist

- [ ] Navigate to `ai-readiness/index.html` and complete calibration → page navigates to `exam-instructions/index.html`
- [ ] Open `exam-instructions/index.html` directly without a keychain session → redirect to `login/index.html`
- [ ] "Start Exam" button is disabled on page load
- [ ] Checking the checkbox enables the button
- [ ] Unchecking the checkbox disables the button again
- [ ] Clicking "Start Exam" shows spinner + "Starting…" text and navigates to `exam/index.html`
- [ ] Rules list scrolls when window height is small (e.g., resize Electron window to 600px tall)
- [ ] Footer stays stuck to bottom of card while list scrolls
- [ ] All 8 rules render with icon + title + description
- [ ] Page renders correctly in both light and dark themes

---

## Design reference

`Designs/Exam _Instructions_Page/screen.png` — use as visual reference for layout, spacing,
and icon choice. The `Designs/Exam _Instructions_Page/code.html` uses Tailwind+CDN and is
**not** a template; extract structural intent only.
