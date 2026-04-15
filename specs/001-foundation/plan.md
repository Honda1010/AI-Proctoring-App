# Implementation Plan: Foundation — App Shell & Python Bridge

**Branch**: `001-foundation` | **Date**: 2026-04-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-foundation/spec.md`

## Summary

Establish the complete foundation for the Lumina AI Proctoring desktop app: an Electron 33+
desktop shell that spawns a Python 3.11 Flask bridge as a subprocess, communicates with it
via `GET /ping` health polling over `localhost:5050`, reads all deployment configuration from
an external `config.json` file, and provides shared design token CSS and bundled fonts that
all subsequent page specs consume. This spec is a hard prerequisite for all 3 page specs.

## Technical Context

**Language/Version**: Node.js 20 LTS + JavaScript (Electron 33+) / Python 3.11+
**Primary Dependencies**: Electron 33+, Flask 3.x, flask-cors 4.x, @fontsource/manrope, @fontsource/inter, keytar 7.x
**Storage**: `config.json` (JSON file at project root / resources/ when packaged); OS keychain via keytar (spec 002+)
**Testing**: Manual DevTools inspection for CSS tokens; `curl /ping` for bridge health; no automated test framework in this spec
**Target Platform**: Windows 10/11 desktop (electron-builder NSIS packaging)
**Project Type**: desktop-app
**Performance Goals**: Window visible <3s from launch; `GET /ping` response <1s; bridge startup timeout 10s
**Constraints**: All fonts bundled offline (no CDN); HTTPS enforced for `baseUrl`; `child_process.spawn` for bridge IPC; single-instance lock
**Scale/Scope**: Single concurrent user, 1 Electron window, 1 Python subprocess, 3 HTML pages (built across 4 specs)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Notes |
|-----------|------|--------|-------|
| I. Spec-First Development | spec.md complete and reviewed before any code | ✅ PASS | spec.md authored and checklist passed |
| II. Architecture Boundary | Plan keeps Electron = UI only; Python = all HTTP; IPC via localhost only | ✅ PASS | GET /ping is the only IPC call in this spec; no LMS calls yet |
| III. Design System Fidelity | design-tokens.css + components.css are primary deliverables; zero hardcoded values | ✅ PASS | Full token inventory in data-model.md; components.css uses ONLY custom properties |
| IV. Security by Default | No credential handling in this spec; HTTPS enforced for baseUrl; keytar declared as dep | ✅ PASS | config.json validation rejects http://; no passwords or tokens stored in this spec |
| V. Independent Testability | GET /ping + DevTools inspection enable standalone verification; mocks/ directory planned | ✅ PASS | US1 testable via curl; US2 testable via DevTools; US3 testable by editing config.json |

**POST-DESIGN RE-CHECK** (after Phase 1):

All 5 gates continue to pass. Design artifacts (data-model, contracts, quickstart) are consistent
with spec requirements. No violations introduced. Constitution compliance confirmed.

## Project Structure

### Documentation (this feature)

```text
specs/001-foundation/
├── plan.md              # This file (speckit.plan output)
├── research.md          # Phase 0 output — 5 research decisions resolved
├── data-model.md        # Phase 1 output — 4 entities: AppConfig, BridgeStatus, HealthResponse, DesignToken
├── quickstart.md        # Phase 1 output — local setup guide
├── contracts/
│   ├── ping.md          # GET /ping contract (Electron → Python bridge)
│   └── config-schema.md # config.json JSON schema contract
└── tasks.md             # Phase 2 output (speckit.tasks — NOT created by speckit.plan)
```

### Source Code (repository root)

```text
frontend/
├── main.js                     # Electron main process: window, child_process.spawn, IPC
├── preload.js                  # contextBridge: exposes safe IPC API to renderer
├── pages/
│   ├── loading/
│   │   └── loading.html        # Shown while bridge is starting (US1)
│   ├── error/
│   │   └── error.html          # Shown on bridge failure / config error (US1, US3)
│   ├── login/                  # (spec 002 — placeholder dir only)
│   ├── exam-code/              # (spec 003 — placeholder dir only)
│   └── exam/                   # (spec 004 — placeholder dir only)
└── assets/
    ├── design-tokens.css       # All CSS custom properties from Ethereal Authority (US2)
    └── components.css          # Reusable component styles using only design tokens (US2)

python_bridge/
├── server.py                   # Flask app: GET /ping, reads config.json, binds 127.0.0.1
├── config.py                   # Config loader: reads config.json, validates baseUrl (HTTPS)
└── requirements.txt            # flask>=3.0, flask-cors>=4.0

config.example.json             # Committed template (no real URLs)
config.json                     # Runtime config — gitignored
package.json                    # Electron + npm dependencies
.gitignore                      # Includes config.json, node_modules/, __pycache__/
```

**Structure Decision**: Two-root layout (Electron frontend + Python bridge) matches the
architecture boundary defined in Constitution Principle II. Source folders are `frontend/`
and `python_bridge/` rather than `backend/` to reflect the local-bridge nature of the Python
process. No shared `src/` directory — each process owns its code exclusively.

## Complexity Tracking

> No constitution violations. No complexity justification required.
