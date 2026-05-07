# Implementation Plan: Pre-Exam Instructions Page

**Branch**: `013-violation-clip-upload` | **Date**: 2026-05-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/012-exam-instructions-page/spec.md`

## Summary

Add a mandatory Pre-Exam Instructions page that appears between the AI Readiness calibration
page and the active exam. The page displays 8 fixed proctoring rules with inline SVG icons,
requires the student to check an acknowledgment checkbox, and gates exam entry behind a
"Start Exam" button with a loading state. Pure frontend — 3 new files plus 1 line changed in
`ai-readiness.js`. No new IPC channels, API endpoints, or configuration keys.

## Technical Context

**Language/Version**: JavaScript (ES2022) in Electron 33 renderer process  
**Primary Dependencies**: Electron 33; existing `components.css` + `design-tokens.css` (no new packages)  
**Storage**: N/A — no persistence; checkbox state is ephemeral  
**Testing**: Manual — visual comparison against `Designs/Exam _Instructions_Page/screen.png`; session guard test  
**Target Platform**: Electron 33 desktop (Windows), same window as all other pages  
**Project Type**: Desktop app renderer page  
**Performance Goals**: Page load < 500 ms; session guard redirect < 1 s (SC-002)  
**Constraints**: CSP `default-src 'self'; style-src 'self'; script-src 'self'; font-src 'self' data:` — no CDN, no external fonts, no inline scripts; inline SVG only for icons  
**Scale/Scope**: 1 page (3 new files + 1 line edit in ai-readiness.js)

## Constitution Check

*No constitution file found at `.specify/memory/constitution.md` — gate check skipped.*

**Design system compliance (from DESIGN.md)**:
- Surface hierarchy: `surface-container-lowest` card on `surface-container-low` page background ✅
- Typography: Manrope for headline/display, Inter for body/label ✅
- No 1px borders between sections ("No-Line" rule) ✅
- Buttons: `btn-primary` gradient from `components.css` ✅
- Corner radii: `xl` (1.5rem) for cards, `DEFAULT` (0.5rem) for buttons ✅
- Ambient shadow: `0px 12px 32px rgba(0,45,91,0.06)` ✅

**Gate: PASS** — No violations. Single-page frontend feature. No new infrastructure.

## Project Structure

### Documentation (this feature)

```text
specs/012-exam-instructions-page/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
└── checklists/
    └── requirements.md
```

### Source Code

```text
frontend/
├── pages/
│   ├── exam-instructions/         ← NEW
│   │   ├── index.html
│   │   ├── exam-instructions.css
│   │   └── exam-instructions.js
│   └── ai-readiness/
│       └── ai-readiness.js        ← EDIT: 1 line (navigation target)
└── assets/
    ├── components.css             ← read-only (shared, reused)
    └── design-tokens.css          ← read-only (shared, reused)

Designs/
└── Exam _Instructions_Page/
    ├── DESIGN.md                  ← design reference (read-only)
    ├── screen.png                 ← visual reference (read-only)
    └── code.html                  ← structural reference (read-only, NOT a template)
```

**Structure Decision**: Single renderer page following the `frontend/pages/{page-name}/` convention
established by all existing pages (`login/`, `exam-code/`, `identity-verification/`, `ai-readiness/`).

## Complexity Tracking

No violations to justify.
