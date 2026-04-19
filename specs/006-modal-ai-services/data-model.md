# Data Model: Modal AI Services

## 1. DetectionEvent (Schema 1.0)
Normalized detection event emitted by Modal and mapped by the bridge client.

| Field | Type | Description |
|-------|------|-------------|
| `service` | string | `face-recognition` or `object-detection` |
| `timestamp` | string | ISO 8601 UTC |
| `confidence` | float | 0.0 to 1.0 |
| `sessionId` | string | Current exam session ID |
| `payload` | object | Service-specific data |

## 2. Modal Configuration (config.json)
| Key | Type | Description |
|-----|------|-------------|
| `modal.token_id` | string | Modal API Token ID |
| `modal.token_secret` | string | Modal API Token Secret |
| `modal.user_id` | string | Modal User ID (e.g., `u-xxxx`) |
| `services.object-detection.endpoint_url` | string | URL for the Modal web endpoint |
| `services.face-recognition.endpoint_url` | string | URL for the Modal web endpoint |

## 3. Error Payload
If Modal is unavailable (cold start / crash):
- `status`: "error"
- `code`: "SERVICE_UNAVAILABLE"
- `message`: "Modal container is warming up or unreachable."
