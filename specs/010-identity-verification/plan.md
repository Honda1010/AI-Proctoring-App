# Implementation Plan: Identity Verification Page

**Branch**: `010-identity-verification` | **Date**: 2026-04-23 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/010-identity-verification/spec.md`

## Summary

Insert an Identity Verification page between the Exam Access (exam-code) page and the AI Readiness page. The page activates the webcam, lets the student capture a reference photo, then chains a server-side face-detection check and Modal enrollment call (`POST /analysis/face-detection-file` → `POST /analysis/enroll-file`) via the existing AI-router JSON-RPC channel. On success, `enrollmentSucceeded` is set in the Electron main-process scope and the student proceeds to AI Readiness. The exam page is gated on `enrollmentSucceeded`. Unenrollment (`POST /analysis/unenroll`) fires on all exam-exit paths (submit, logout, back-to-home).

## Technical Context

**Language/Version**: Node.js 20 LTS (Electron 33+) / Python 3.11  
**Primary Dependencies**: Electron 33, httpx 0.27+, @fontsource/manrope, @fontsource/inter  
**Storage**: Module-scope variable `enrollmentSucceeded: boolean` in `frontend/main.js` (same pattern as `examSession`); no disk writes  
**Testing**: Manual against real Modal endpoint; mock JSON-RPC `enrollReference` response for offline testing  
**Target Platform**: Desktop (Windows / macOS)  
**Project Type**: Desktop app (Electron)  
**Performance Goals**: Enrollment roundtrip (face-detection + enroll) ≤ 15 s on cold Modal start; quality-indicator canvas refresh ≤ 100 ms per tick  
**Constraints**: Camera frames never persisted to disk; HTTPS only for Modal calls; frame-rate cap (1 frame per 2 s per AI model applies to exam proctoring — enrollment is a one-off, exempt); captured JPEG ≤ 640×480 for bandwidth  
**Scale/Scope**: 1 new page, 4 modified files (main.js, preload.js, router.py, face_recognition.py + modal_client.py + config.json), 1 navigation redirect change (exam-code.js)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-First Development | ✅ PASS | spec.md + 5 clarifications complete; spec reviewed before any implementation |
| II. Architecture Boundary | ⚠️ ACCEPTED DEVIATION | Existing code already uses stdin/stdout JSON-RPC for the AI router (pre-existing accepted deviation). New `enrollReference` / `unenrollReference` JSON-RPC methods extend this same router channel. `main.js` NEVER calls Modal endpoints directly — all Modal HTTP calls stay inside `router.py` / `modal_client.py`. LMS calls continue via Flask on port 5050. |
| III. Design System Fidelity | ✅ PASS | Page uses `design-tokens.css` custom properties; glassmorphism on video (surface-container-lowest ≥70% opacity + backdrop-filter blur ≥16px); Manrope headings, Inter body; no hardcoded hex; no 1px borders |
| IV. Security by Default | ✅ PASS | Captured JPEG held in memory only; transmitted over HTTPS to Modal; cleared on session end; `enrollmentSucceeded` contains no biometric data; Modal session_id used (not student email/password) |
| V. Independent Testability | ✅ PASS | `enrollReference` mock JSON-RPC response defined; page testable by loading identity-verification/index.html directly with mock router |

**Architecture Deviation Justification (Principle II)**:  
The AI router's stdin/stdout JSON-RPC channel was established in spec 001 as a pragmatic choice for low-latency local AI service management. All AI service operations (startService, stopService, predict, queryStatus) already flow through this channel. Enrollment is an AI service operation and belongs with the same service object (`FaceRecognitionService`). Using the Flask HTTP bridge for enrollment would require duplicating `ModalClient` into `server.py`, fragmenting the AI service ownership. The deviation is minimal, bounded, and pre-approved by the existing architecture.

## Project Structure

### Documentation (this feature)

```text
specs/010-identity-verification/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   ├── ipc-enroll-reference.md
│   └── json-rpc-enroll.md
└── tasks.md             ← Phase 2 output (speckit.tasks)
```

### Source Code (repository root)

```text
# New files
frontend/pages/identity-verification/
├── index.html                       ← identity verification page markup
├── identity-verification.js         ← page controller (webcam, capture, IPC)
└── identity-verification.css        ← page-scoped styles (imports design tokens)

# Modified files
frontend/
├── main.js                          ← add enrollmentSucceeded var; bridge:enroll-reference,
│                                       bridge:get-enrollment-status handlers; unenroll on exit paths
├── preload.js                       ← whitelist bridge:enroll-reference, bridge:get-enrollment-status
└── pages/
    └── exam-code/
        └── exam-code.js             ← change success redirect: ai-readiness → identity-verification

python_bridge/
├── router.py                        ← add enrollReference / unenrollReference JSON-RPC handlers
├── face_recognition.py              ← add enroll() / unenroll() methods; remove WARMUP from start()
└── modal_client.py                  ← add enroll(), unenroll(), face_detect() HTTP methods

config.json                          ← add enroll_endpoint_url, unenroll_endpoint_url,
                                        face_detect_endpoint_url under services.face-recognition
```

**Structure Decision**: Electron/Python two-process desktop app. The new page follows the existing `frontend/pages/<name>/` pattern (three files: HTML, JS, CSS). Python changes are confined to `python_bridge/` service layer. No new packages required.

## Complexity Tracking

No constitution violations requiring justification beyond the pre-existing Architecture Boundary deviation documented above.

