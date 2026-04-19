# Data Model: Proctoring Orchestration

## 1. AlertEvent
Emitted by the Orchestrator when a rule is triggered.

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Constant: `"alert"` |
| `code` | string | Rule code (e.g., `OFF_SCREEN_GAZE`) |
| `severity` | string | `"low"`, `"medium"`, `"high"` |
| `message` | string | Human-readable explanation |
| `timestamp` | string | ISO 8601 UTC |
| `sessionId` | string | Current session ID |
| `evidence` | object | Snip of the `DetectionEvent` that triggered it |

## 2. RiskScoreUpdate
Emitted periodically or on significant changes.

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Constant: `"riskScore"` |
| `score` | integer | 0 to 100 |
| `trend` | string | `"rising"`, `"stable"`, `"falling"` |
| `timestamp` | string | ISO 8601 UTC |

## 3. Configuration (config.json)
Alert rules and scoring weights.

```json
{
  "orchestration": {
    "rules": {
      "eye-gaze": {
        "away_threshold_seconds": 3,
        "weight": 20
      },
      "face-recognition": {
        "missing_threshold_seconds": 5,
        "weight": 50
      },
      "speech-detection": {
        "weight": 30
      }
    },
    "risk_score_decay": 0.95
  }
}
```

## 4. Session Log (JSONL)
Format for `sessions/<session_id>.jsonl`.
- Each line is a standalone JSON object.
- Includes `DetectionEvent`, `AlertEvent`, and `RiskScoreUpdate`.
