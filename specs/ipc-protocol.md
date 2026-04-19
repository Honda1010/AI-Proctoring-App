# AI Service Bridge IPC Protocol

The Electron frontend communicates with the Python bridge via **stdin/stdout** using **JSON-RPC 2.0**.

## Transport

- **Stdin**: Electron writes JSON-RPC 2.0 requests and notifications to the Python bridge's standard input.
- **Stdout**: The Python bridge writes JSON-RPC 2.0 responses and notifications to its standard output.
- **Stderr**: Log messages, debug info, and critical system errors are written to standard error.

Each JSON message must be a single line terminated by a newline character (`\n`).

## JSON-RPC 2.0 Basics

### Request
```json
{"jsonrpc": "2.0", "method": "startService", "params": {"service": "eye-gaze"}, "id": 1}
```

### Response (Success)
```json
{"jsonrpc": "2.0", "result": {"status": "started"}, "id": 1}
```

### Response (Error)
```json
{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}
```

### Notification (Event)
```json
{"jsonrpc": "2.0", "method": "detection", "params": { ... DetectionEvent ... }}
```

## Methods

### `startService(params)`
Starts a specific AI service.

- `params`:
  - `service`: One of `eye-gaze`, `object-detection`, `face-recognition`, `speech-detection`.
  - `config`: Optional configuration overrides for this service.
  - `sessionId`: The current exam session ID.

### `stopService(params)`
Stops a specific AI service.

- `params`:
  - `service`: One of `eye-gaze`, `object-detection`, `face-recognition`, `speech-detection`.

### `queryStatus(params)`
Queries the status of all services or a specific one.

- `params`:
  - `service`: Optional. If omitted, returns status for all.

## Notifications (Outbound from Python)

### `detection`
Emitted by the Python bridge when a detection occurs.

- `params`: A `DetectionEvent` conforming to `specs/ai-service-contract.json`.

### `serviceError`
Emitted when a service fails unexpectedly.

- `params`:
  - `service`: Name of the service.
  - `code`: Error code.
  - `message`: Human-readable error message.

## Service Lifecycle

1. Electron spawns `router.py`.
2. Electron sends `startService` for desired AI modules.
3. Python bridge loads models (locally or on Modal) and starts inference loop.
4. Python bridge emits `detection` notifications on stdout.
5. Electron sends `stopService` when exam ends or page is left.
6. Electron terminates `router.py` process.
