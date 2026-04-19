import json
import os
import datetime
import asyncio
from typing import Dict, Any, List, Optional, Callable

class ProctoringOrchestrator:
    """
    Fuses AI signals into high-level alerts and a running risk score.
    Persists all events to a Session Log (JSONL).
    """

    def __init__(self, config: Dict[str, Any], emit_callback: Callable[[Dict[str, Any]], None]):
        self.config = config.get("orchestration", {})
        self.rules_config = self.config.get("rules", {})
        self.risk_score_decay = self.config.get("risk_score_decay", 0.9997)
        self.emit_callback = emit_callback
        
        self.current_session_id: Optional[str] = None
        self.log_file = None
        
        # State tracking
        self.risk_score = 0.0
        self.active_violations: Dict[str, bool] = {
            "eye-gaze": False,
            "face-recognition": False,
            "speech-detection": False,
            "object-detection": False
        }
        
        # Timers for time-based rules
        self.missing_face_start: Optional[float] = None
        self.off_screen_gaze_start: Optional[float] = None
        
        # Lock for thread-safe logging if needed, though we use asyncio
        self._log_lock = asyncio.Lock()

    def set_session(self, session_id: str):
        """Initialize logging for a new session."""
        if self.current_session_id == session_id:
            return
            
        self.current_session_id = session_id
        self.risk_score = 0.0
        
        # Ensure sessions directory exists
        os.makedirs("sessions", exist_ok=True)
        log_path = os.path.join("sessions", f"{session_id}.jsonl")
        
        # Open in append mode
        self.log_file_path = log_path

    async def on_detection_event(self, event: Dict[str, Any]):
        """Entry point for incoming AI detections."""
        if not self.current_session_id:
            self.set_session(event.get("sessionId", "default-session"))

        # 1. Log the raw detection
        await self._log_event(event)

        # 2. Process rules
        await self._process_rules(event)

        # 3. Update risk score (additive weighted sum)
        await self._update_risk_score(event)

    async def _process_rules(self, event: Dict[str, Any]):
        service = event.get("service")
        payload = event.get("payload", {})
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()

        # --- Rule: Object Detection (Immediate) ---
        if service == "object-detection":
            if payload.get("suspicious"):
                await self._emit_alert(
                    "UNAUTHORIZED_OBJECT", "high", 
                    f"Suspicious object detected: {', '.join(payload.get('objects', []))}", 
                    event
                )

        # --- Rule: Speech Detection (Immediate/State-based) ---
        if service == "speech-detection":
            if payload.get("is_speech_detected"):
                await self._emit_alert("SPEECH_DETECTED", "medium", "Speech presence detected in environment.", event)

        # --- Rule: Eye Gaze (Time-based) ---
        if service == "eye-gaze":
            status = payload.get("status")
            threshold = self.rules_config.get("eye-gaze", {}).get("away_threshold_seconds", 3)
            
            if status == "away":
                if self.off_screen_gaze_start is None:
                    self.off_screen_gaze_start = now
                elif now - self.off_screen_gaze_start > threshold:
                    await self._emit_alert("GAZE_OFF_SCREEN", "low", f"Gaze away from screen for > {threshold}s", event)
                    # Reset start so we don't spam alerts every frame
                    self.off_screen_gaze_start = now 
            else:
                self.off_screen_gaze_start = None

        # --- Rule: Face Recognition (Time-based) ---
        if service == "face-recognition":
            matched = payload.get("is_matched", False)
            threshold = self.rules_config.get("face-recognition", {}).get("missing_threshold_seconds", 5)
            
            if not matched:
                if self.missing_face_start is None:
                    self.missing_face_start = now
                elif now - self.missing_face_start > threshold:
                    await self._emit_alert("NO_FACE_DETECTED", "high", f"Student face missing for > {threshold}s", event)
                    self.missing_face_start = now
            else:
                self.missing_face_start = None

    async def _update_risk_score(self, event: Dict[str, Any]):
        """Additive weighted sum calculation."""
        service = event.get("service")
        payload = event.get("payload", {})
        
        weight = self.rules_config.get(service, {}).get("weight", 10)
        
        # Determine if this specific event is "suspicious"
        is_suspicious = False
        if service == "eye-gaze" and payload.get("status") == "away":
            is_suspicious = True
        elif service == "face-recognition" and not payload.get("is_matched"):
            is_suspicious = True
        elif service == "speech-detection" and payload.get("is_speech_detected"):
            is_suspicious = True
        elif service == "object-detection" and payload.get("suspicious"):
            is_suspicious = True

        if is_suspicious:
            # Increase risk score
            self.risk_score = min(100.0, self.risk_score + (weight * 0.1)) # Scaling factor
        else:
            # Decay risk score
            self.risk_score *= self.risk_score_decay
            
        # Emit score update if changed significantly (or every few events)
        # For now, emit every time for simplicity
        score_update = {
            "type": "riskScore",
            "score": int(round(self.risk_score)),
            "trend": "rising" if is_suspicious else "falling",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self.emit_callback(score_update)
        await self._log_event(score_update)

    async def _emit_alert(self, code: str, severity: str, message: str, evidence: Dict[str, Any]):
        alert = {
            "type": "alert",
            "code": code,
            "severity": severity,
            "message": message,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sessionId": self.current_session_id,
            "evidence": {
                "service": evidence.get("service"),
                "confidence": evidence.get("confidence")
            }
        }
        self.emit_callback(alert)
        await self._log_event(alert)

    async def _log_event(self, event: Dict[str, Any]):
        """Write event to JSONL file."""
        if not self.current_session_id:
            return
            
        async with self._log_lock:
            try:
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")
            except Exception as e:
                # Fallback to stderr if logging fails
                import sys
                print(f"Logging error: {str(e)}", file=sys.stderr)
