# AI-Proctoring-App Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-05

## Active Technologies
- Node.js 20 LTS + JavaScript (Electron 33+) / Python 3.11+ + Electron 33+, Flask 3.x, flask-cors 4.x, @fontsource/manrope, @fontsource/inter, keytar 7.x (001-foundation)
- `config.json` (JSON file at project root / resources/ when packaged); OS keychain via keytar (spec 002+) (001-foundation)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (002-login-page)
- Node.js 20 LTS (Electron 33+) / Python 3.11+ + Electron 33, keytar 7.x, Flask 3.x, flask-cors 4.x, requests 2.32+, @fontsource/manrope, @fontsource/inter (002-login-page)
- OS keychain via keytar (JWT + refresh token + user profile); no database (002-login-page)
- OS keychain via keytar (existing session — read only in this spec); module-scope `examSession` variable (in-memory, not persisted) (002-login-page)
- OS keychain via keytar (existing session — read only in this spec); module-scope `examSession` (read only, written by spec 003); module-scope `submitResult` (written once on submit success, read by spec 005 via IPC) (004-exam-page)
- OS keychain via keytar (read-only in this spec); module-scope `submitResult` (read then cleared); module-scope `examSession` (read for `attemptId` in recovery path, then cleared on Back to Home) (005-result-page)
- Node.js 20 LTS (Electron 33+) / Python 3.11 + Electron 33, httpx 0.27+, @fontsource/manrope, @fontsource/inter (010-identity-verification)
- Module-scope variable `enrollmentSucceeded: boolean` in `frontend/main.js` (same pattern as `examSession`); no disk writes (010-identity-verification)
- JavaScript (Electron 33+ renderer + main) / Python 3.11+ + Electron 33+, MediaRecorder Web API, ffmpeg-python, requests 2.32+ (013-violation-clip-upload)
- Temp files in `os.tmpdir()` during clip composition (deleted in `try/finally`); Bunny CDN for permanent clip storage; no local disk persistence of clip data (013-violation-clip-upload)

- [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION] (001-foundation)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

[e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]: Follow standard conventions

## Recent Changes
- 013-violation-clip-upload: Added JavaScript (Electron 33+ renderer + main) / Python 3.11+ + Electron 33+, MediaRecorder Web API, ffmpeg-python, requests 2.32+
- 010-identity-verification: Added Node.js 20 LTS (Electron 33+) / Python 3.11 + Electron 33, httpx 0.27+, @fontsource/manrope, @fontsource/inter
- 005-result-page: Added Node.js 20 LTS (Electron 33+) / Python 3.11+ + Electron 33, keytar 7.x, Flask 3.x, flask-cors 4.x, requests 2.32+, @fontsource/manrope, @fontsource/inter


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
