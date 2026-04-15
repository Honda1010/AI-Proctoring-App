# AI-Proctoring-App Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-15

## Active Technologies
- Node.js 20 LTS + JavaScript (Electron 33+) / Python 3.11+ + Electron 33+, Flask 3.x, flask-cors 4.x, @fontsource/manrope, @fontsource/inter, keytar 7.x (001-foundation)
- `config.json` (JSON file at project root / resources/ when packaged); OS keychain via keytar (spec 002+) (001-foundation)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (002-login-page)
- Node.js 20 LTS (Electron 33+) / Python 3.11+ + Electron 33, keytar 7.x, Flask 3.x, flask-cors 4.x, requests 2.32+, @fontsource/manrope, @fontsource/inter (002-login-page)
- OS keychain via keytar (JWT + refresh token + user profile); no database (002-login-page)
- OS keychain via keytar (existing session — read only in this spec); module-scope `examSession` variable (in-memory, not persisted) (002-login-page)

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
- 002-login-page: Added Node.js 20 LTS (Electron 33+) / Python 3.11+ + Electron 33, keytar 7.x, Flask 3.x, flask-cors 4.x, requests 2.32+, @fontsource/manrope, @fontsource/inter
- 002-login-page: Added Node.js 20 LTS (Electron 33+) / Python 3.11+ + Electron 33, keytar 7.x, Flask 3.x, flask-cors 4.x, requests 2.32+, @fontsource/manrope, @fontsource/inter
- 002-login-page: Added [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
