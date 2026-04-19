# Implementation Plan: Proctoring Orchestration Layer

**Branch**: `008-proctoring-orchestration`
**Spec**: [spec.md](spec.md)

## Summary
Implement the proctoring logic that transforms raw AI signals into actionable alerts and a running risk score. This module acts as the "brain" of the bridge.

## Technical Context
- **Language**: Python 3.11
- **Storage**: Local filesystem (`sessions/` directory)
- **Integration**: The `AIRouter` will pass all validated `DetectionEvent`s to the `ProctoringOrchestrator`.
- **Validation**: `jsonschema` for alert rule configuration.

## Implementation Steps

### Phase 1: Core Orchestrator
1. Create `python_bridge/orchestrator.py`.
2. Implement the `ProctoringOrchestrator` class with an `on_detection_event(event)` entry point.
3. Implement thread-safe JSONL logging to `sessions/<session_id>.jsonl`.

### Phase 2: Rule Engine
1. Define the `Rule` base class and specific rule implementations:
   - `MissingFaceRule` (time-based)
   - `OffScreenGazeRule` (time-based)
   - `SuspiciousObjectRule` (immediate)
   - `SpeechDetectedRule` (immediate)
2. Implement state tracking (timers) for time-based rules.

### Phase 3: Risk Scorer
1. Implement the `RiskScorer` logic using weighted averages of triggered rules and active detections.
2. Add "decay" logic so the score slowly returns to zero during quiet periods.

### Phase 4: Router Integration
1. Instantiate the `ProctoringOrchestrator` inside `AIRouter`.
2. Update `AIRouter.thread_safe_emit` and `handle_predict` to pipe events through the orchestrator.
3. Add a callback mechanism so the orchestrator can emit `alert` and `riskScore` notifications back to the router's `stdout`.

## Verification
- Unit tests for each rule type using mock event streams.
- Unit tests for risk score math (clamping at 0 and 100).
- Integration test running the full bridge and verifying the generated `.jsonl` file.
