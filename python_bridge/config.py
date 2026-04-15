"""
config.py — Load and validate config.json for the Lumina AI Python bridge.

Usage:
    from config import load_config, AppConfig, ConfigError

Raises ConfigError with a typed code and human-readable message for every
failure case. All errors are also emitted to stderr as a single-line JSON
string so Electron can parse them from the subprocess stderr stream.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Raised when config.json is missing, malformed, or contains invalid values."""

    CODES = {
        "FILE_NOT_FOUND",
        "INVALID_JSON",
        "MISSING_BASE_URL",
        "INSECURE_PROTOCOL",
        "INVALID_PORT",
    }

    def __init__(self, code: str, message: str) -> None:
        if code not in self.CODES:
            raise ValueError(f"Unknown ConfigError code: {code!r}")
        self.code = code
        self.message = message
        super().__init__(message)

    def emit_stderr(self) -> None:
        """Write a single-line JSON error to stderr for Electron to parse."""
        payload = json.dumps({"error": self.code, "message": self.message})
        print(payload, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AppConfig:
    base_url: str
    python_port: int = field(default=5050)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> AppConfig:
    """
    Read and validate config.json at *config_path*.

    Returns an AppConfig on success.
    Raises ConfigError (and emits to stderr) on any failure.

    Validation rules (from contracts/config-schema.md):
      - File must exist and be readable.
      - File must contain valid JSON.
      - 'baseUrl' key must be present and non-empty.
      - 'baseUrl' must start with 'https://' (INSECURE_PROTOCOL otherwise).
      - 'pythonPort', when present, must be an integer in range [1024, 65535].
    """
    # Rule 1: File must exist
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except FileNotFoundError:
        err = ConfigError(
            "FILE_NOT_FOUND",
            f"config.json not found at path: {config_path}",
        )
        err.emit_stderr()
        raise err
    except OSError as exc:
        err = ConfigError(
            "FILE_NOT_FOUND",
            f"Could not read config.json: {exc}",
        )
        err.emit_stderr()
        raise err

    # Rule 2: Must be valid JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        err = ConfigError(
            "INVALID_JSON",
            f"config.json contains invalid JSON: {exc.msg} (line {exc.lineno})",
        )
        err.emit_stderr()
        raise err

    # Rule 3: 'baseUrl' must be present and non-empty
    base_url: Optional[str] = data.get("baseUrl")
    if not base_url or not isinstance(base_url, str) or not base_url.strip():
        err = ConfigError(
            "MISSING_BASE_URL",
            "config.json must contain a non-empty 'baseUrl' string.",
        )
        err.emit_stderr()
        raise err

    base_url = base_url.strip().rstrip("/")

    # Rule 4: baseUrl must use HTTPS
    if not base_url.startswith("https://"):
        err = ConfigError(
            "INSECURE_PROTOCOL",
            "baseUrl must use HTTPS (https://). HTTP URLs are not permitted.",
        )
        err.emit_stderr()
        raise err

    # Rule 5: pythonPort must be in valid range when provided
    python_port = data.get("pythonPort", 5050)
    if not isinstance(python_port, int) or isinstance(python_port, bool):
        err = ConfigError(
            "INVALID_PORT",
            f"pythonPort must be an integer, got {type(python_port).__name__!r}.",
        )
        err.emit_stderr()
        raise err

    if not (1024 <= python_port <= 65535):
        err = ConfigError(
            "INVALID_PORT",
            f"pythonPort must be between 1024 and 65535, got {python_port}.",
        )
        err.emit_stderr()
        raise err

    return AppConfig(base_url=base_url, python_port=python_port)
