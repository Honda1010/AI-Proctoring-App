# Data Model: Foundation — App Shell & Python Bridge

**Branch**: `001-foundation` | **Date**: 2026-04-15
**Source**: Entities extracted from `specs/001-foundation/spec.md`

---

## Entity 1: AppConfig

**What it represents**: The runtime configuration loaded from `config.json` at app startup.
Shared between Electron (reads it to know the bridge port) and the Python bridge (reads it
to know the LMS base URL). It is the single source of truth for all deployment-specific values.

### Fields

| Field | Type | Required | Default | Validation Rule |
|-------|------|----------|---------|-----------------|
| `baseUrl` | `string` | ✅ | — | Must start with `https://`. Trailing slash stripped. |
| `pythonPort` | `integer` | ❌ | `5050` | 1024–65535. Must not be in use at startup. |

### State Transitions

```
[File absent / malformed JSON]  →  CONFIG_ERROR
[http:// baseUrl]               →  CONFIG_ERROR (HTTPS enforced)
[Missing baseUrl field]         →  CONFIG_ERROR (field required)
[Valid]                         →  CONFIG_LOADED  →  (app continues startup)
```

### config.json Example

```json
{
  "baseUrl": "https://lms.university.edu/api",
  "pythonPort": 5050
}
```

---

## Entity 2: BridgeStatus

**What it represents**: The runtime health state of the Python Flask bridge as observed by
the Electron main process. Drives the loading / error screen displayed to the student.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `state` | `enum` | Current lifecycle state (see below) |
| `message` | `string?` | Human-readable reason for `failed` or `crashed` states |
| `port` | `integer` | The port the bridge is (or was) listening on |
| `pid` | `integer?` | OS process ID of the Python child process; `null` if not started |

### State Enum

| State | Meaning |
|-------|---------|
| `starting` | `spawn` called; bridge process is booting; health check not yet successful |
| `ready` | `GET /ping` returned 200 OK; bridge is operational |
| `failed` | Bridge never reached `ready` within 10-second timeout; polling exhausted |
| `crashed` | Bridge was `ready` but the child process unexpectedly exited with non-zero code |

### State Machine

```
[app launches]
      │
      ▼
  starting  ─── ping OK ──────────────────▶  ready  ─── process exits ──▶  crashed
      │                                                                         │
      └─── timeout (10s, 20 retries) ────▶  failed                             │
      │                                                                         │
      └─── port in use / python missing ─▶  failed                             │
                                                                                ▼
                                                                     [error screen shown]
```

---

## Entity 3: HealthResponse

**What it represents**: The JSON body returned by the Python bridge's `GET /ping` endpoint.
Used by Electron to confirm the bridge is operational and to display the bridge version in
diagnostic screens.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | `string` | ✅ | Always `"ok"` when the bridge is healthy |
| `version` | `string` | ✅ | Bridge version string (e.g., `"1.0.0"`) |
| `timestamp` | `string` | ✅ | ISO 8601 UTC timestamp of the response |

### Example Response

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-04-15T10:30:00Z"
}
```

---

## Entity 4: DesignToken

**What it represents**: A single CSS custom property entry in `frontend/assets/design-tokens.css`.
Represents a named, reusable design value extracted from the "Ethereal Authority" design system.
Not a runtime data entity — a CSS authoring contract.

### Categories and Full Token Inventory

#### 4.1 Color Tokens

| Token Name | Value | Usage |
|------------|-------|-------|
| `--color-primary` | `#006687` | Primary actions, gradient start |
| `--color-primary-container` | `#41B3E3` | Gradient end, secondary fills |
| `--color-on-primary` | `#FFFFFF` | Text on primary backgrounds |
| `--color-secondary-container` | `#A7C8FF` | Secondary button fill |
| `--color-on-secondary-container` | `#325383` | Text on secondary containers |
| `--color-tertiary` | `#8C5000` | Flagged/warning state indicators |
| `--color-surface` | `#F8F9FA` | Canvas base layer |
| `--color-surface-container-low` | `#F3F4F5` | Sectioning / sidebar layer |
| `--color-surface-container-lowest` | `#FFFFFF` | Content cards / highest layer |
| `--color-surface-bright` | `#F8F9FA` | Floating overlay base |
| `--color-on-surface` | `#191C1D` | High-contrast body text |
| `--color-on-surface-variant` | `#3E484E` | Secondary / supporting text |
| `--color-outline-variant` | `#BFC8CE` | Ghost borders (used at 20% opacity) |
| `--color-primary-fixed` | `#C2E8FF` | Focus glow spread (used at 30% opacity) |
| `--color-on-secondary-fixed-variant` | `#002D5B` | Shadow tint (navy) |

#### 4.2 Typography Tokens

| Token Name | Value | Usage |
|------------|-------|-------|
| `--font-display` | `'Manrope', sans-serif` | Display headings |
| `--font-body` | `'Inter', sans-serif` | Body text, labels |
| `--font-size-display-lg` | `3.5rem` | Landing / hero headings |
| `--font-size-headline-md` | `1.75rem` | Section anchors |
| `--font-size-body-lg` | `1rem` | Default body text |
| `--font-size-label-md` | `0.75rem` | Metadata labels, status chips |
| `--letter-spacing-display` | `-0.02em` | Display heading tracking |
| `--letter-spacing-label` | `0.05em` | Label tracking (ALL CAPS) |

#### 4.3 Spacing & Radius Tokens

| Token Name | Value | Usage |
|------------|-------|-------|
| `--radius-card` | `1.5rem` | Cards, proctoring event containers |
| `--radius-button` | `0.5rem` | Buttons, input fields |
| `--radius-chip` | `9999px` | Status chips, badges |
| `--spacing-md` | `0.75rem` | Spacing between compact items |

#### 4.4 Elevation & Shadow Tokens

| Token Name | Value | Usage |
|------------|-------|-------|
| `--shadow-ambient` | `0px 12px 32px rgba(0, 45, 91, 0.06)` | Floating elements |
| `--blur-glass` | `24px` | Glassmorphism backdrop-blur |
| `--opacity-glass` | `0.70` | Glassmorphism surface opacity |
| `--opacity-ghost-border` | `0.20` | Ghost border opacity |

#### 4.5 Gradient Token

| Token Name | Value | Usage |
|------------|-------|-------|
| `--gradient-primary` | `linear-gradient(135deg, #006687, #41B3E3)` | Primary buttons, hero states |

---

## Relationships

```
AppConfig ──read-by──▶ Electron main.js (port field)
AppConfig ──read-by──▶ Python bridge config.py (baseUrl field)

BridgeStatus ──owned-by──▶ Electron main process
BridgeStatus ──triggers──▶ page routing (loading → error or page)

HealthResponse ──returned-by──▶ GET /ping endpoint
HealthResponse ──consumed-by──▶ Electron polling loop (updates BridgeStatus)

DesignToken ──defined-in──▶ frontend/assets/design-tokens.css
DesignToken ──consumed-by──▶ frontend/assets/components.css (all components)
DesignToken ──consumed-by──▶ frontend/pages/*/page.css (per-page overrides)
```
