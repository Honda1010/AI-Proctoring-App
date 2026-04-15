# Contract: config.json Schema

**Contract Type**: Configuration file (JSON)
**Owner**: System administrator / deployment engineer
**Consumers**: Electron main process (reads `pythonPort`), Python bridge (reads `baseUrl`)
**Version**: 1.0.0
**Defined in**: `specs/001-foundation/contracts/config-schema.md`

---

## File Location

| Context | Path |
|---------|------|
| Development (unpackaged) | `<project-root>/config.json` |
| Packaged (electron-builder) | `<install-dir>/resources/config.json` |

---

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema",
  "type": "object",
  "required": ["baseUrl"],
  "additionalProperties": false,
  "properties": {
    "baseUrl": {
      "type": "string",
      "description": "Root URL of the LMS REST API. Must start with https://. No trailing slash.",
      "pattern": "^https://",
      "examples": ["https://lms.university.edu/api"]
    },
    "pythonPort": {
      "type": "integer",
      "description": "Port for the local Python Flask bridge. Default: 5050.",
      "minimum": 1024,
      "maximum": 65535,
      "default": 5050
    }
  }
}
```

---

## Valid Example

```json
{
  "baseUrl": "https://lms.university.edu/api",
  "pythonPort": 5050
}
```

---

## Validation Rules

| Rule | Enforced By | Error Displayed |
|------|-------------|-----------------|
| `baseUrl` field must be present | Python bridge on startup | "Configuration error: `baseUrl` is required in config.json" |
| `baseUrl` must start with `https://` | Python bridge on startup | "Configuration error: `baseUrl` must use HTTPS (https://)" |
| File must exist at expected path | Electron main process (before spawning bridge) | "Configuration file not found at: [path]. Please create config.json." |
| File must be valid JSON | Electron main process | "Configuration file is not valid JSON. Please check config.json for syntax errors." |
| `pythonPort` if present must be 1024–65535 | Electron main process | "Invalid pythonPort in config.json. Must be between 1024 and 65535." |

---

## Validation Flow

```
Electron starts
      │
      ▼
Read config.json
      │
      ├── File missing? ──────────────────────────────▶  CONFIG_ERROR: file not found
      │
      ├── Invalid JSON? ──────────────────────────────▶  CONFIG_ERROR: JSON parse error
      │
      ├── Missing baseUrl field? ─────────────────────▶  CONFIG_ERROR: field required
      │
      ├── pythonPort out of range? ───────────────────▶  CONFIG_ERROR: invalid port
      │
      └── All valid ──────────────────────────────────▶  Spawn Python bridge
                                                               │
                                                               ▼
                                                    Python reads config.json
                                                               │
                                                    baseUrl starts with http:// ?
                                                               │
                                                    Yes ──────▶  CONFIG_ERROR: HTTPS required
                                                    No  ──────▶  Bridge starts normally
```

---

## Notes for Implementers

- **Do not** include comments in `config.json` — the JSON specification does not support
  comments and Python's `json.load()` will fail.
- **Do not** add `apiKey`, `password`, or any credential fields to `config.json`.
  Credentials are never stored in this file.
- The `baseUrl` value should **not** have a trailing slash. The bridge appends paths directly:
  `baseUrl + '/Authuantication/login'`.
