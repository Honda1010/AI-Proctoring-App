# Data Model: AI Frontend

## 1. LiveDashboardState
Internal frontend state representing the active session monitoring.

| Field | Type | Description |
|-------|------|-------------|
| `services` | Object | Map of `service_name` to `{ status: string, lastEvent: ISOString }` |
| `riskScore` | Integer | Running score (0–100) |
| `alerts` | Array | Circular buffer of the last 20 `AlertEvent` objects |

## 2. SessionReportData
Structured data parsed from a `.jsonl` session log.

| Field | Type | Description |
|-------|------|-------------|
| `sessionId` | String | Unique ID of the session |
| `summary` | Object | Total alerts per category, peak risk score, duration |
| `timeline` | Array | Flattened list of `DetectionEvent`, `AlertEvent`, and `RiskScoreUpdate` |

## 3. IPC Channel Additions
New channels to support frontend-driven log loading.

### `bridge:get-session-log`
- **Direction**: Renderer → Main
- **Arg**: `{ sessionId: string }`
- **Return**: `{ ok: true, data: Array<string> }` (Array of JSON lines) or `{ ok: false, error: object }`

### `bridge:export-pdf`
- **Direction**: Renderer → Main
- **Arg**: `{ filename: string, htmlContent: string }`
- **Return**: `{ ok: true, path: string }` or `{ ok: false }`
