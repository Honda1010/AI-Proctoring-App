from ai_base import AIService
from modal_client import ModalClient
from modal_response_adapters import adapt_face_modal_json, is_bridge_detection_event

class FaceRecognitionService(AIService):
    """Face Recognition service (hosted on Modal)."""

    def __init__(self, session_id: str, config: dict):
        super().__init__("face-recognition", session_id, config)
        service_config = config.get("services", {}).get("face-recognition", {})
        self.endpoint_url = service_config.get("endpoint_url")
        self.enroll_endpoint_url = service_config.get("enroll_endpoint_url", "")
        self.unenroll_endpoint_url = service_config.get("unenroll_endpoint_url", "")
        self.face_detect_endpoint_url = service_config.get("face_detect_endpoint_url", "")
        modal_config = config.get("modal", {})
        self.token = modal_config.get("token_id", "test-token") # In real app, might be combined
        self.client = None

    async def start(self):
        if not self.endpoint_url:
            raise ValueError("Face Recognition endpoint_url not configured")
        self.client = ModalClient(
            self.endpoint_url,
            self.token,
            enroll_url=self.enroll_endpoint_url,
            unenroll_url=self.unenroll_endpoint_url,
            face_detect_url=self.face_detect_endpoint_url,
        )
        self.is_running = True
        # WARMUP removed — Modal is warmed by the enrollment call (spec 010)

    async def stop(self):
        self.is_running = False
        self.client = None

    async def enroll(self, frame: str) -> dict:
        """
        Enroll a reference image for this session.
        Chains: face_detect (gate check) → enroll (store embedding).
        Returns: {ok: True} on success or {ok: False, error: {code, message}} on failure.
        """
        if not self.is_running or self.client is None:
            return {"ok": False, "error": {"code": "SERVICE_NOT_RUNNING",
                    "message": "Face recognition service is not running."}}

        # Gate: confirm a face is present before enrolling
        detect_result = await self.client.face_detect(self.session_id, frame)
        face_found = (
            detect_result.get("face_detected") or
            detect_result.get("ok") is True or
            (detect_result.get("num_faces", 0) > 0)
        )
        if not face_found:
            # Check for explicit error first
            if detect_result.get("ok") is False:
                return {"ok": False, "error": detect_result.get("error",
                        {"code": "NO_FACE_DETECTED", "message": "No face detected in the image."})}
            return {"ok": False, "error": {"code": "NO_FACE_DETECTED",
                    "message": "No face detected — please adjust your position."}}

        # Enroll the reference image
        enroll_result = await self.client.enroll(self.session_id, frame)
        if enroll_result.get("ok") is False:
            return {"ok": False, "error": enroll_result.get("error",
                    {"code": "ENROLLMENT_FAILED", "message": "Enrollment failed."})}

        return {"ok": True}

    async def unenroll(self) -> None:
        """
        Remove the stored embedding for this session (fire-and-forget).
        Errors are swallowed.
        """
        if self.client is not None:
            try:
                await self.client.unenroll(self.session_id)
            except Exception:
                pass  # fire-and-forget

    async def predict(self, frame: str) -> dict:
        """Process a frame using Modal cloud inference."""
        if not self.is_running:
            return self._create_error_event("SERVICE_NOT_RUNNING", "Service is not running")
        raw = await self.client.predict(self.service_name, self.session_id, frame)
        if is_bridge_detection_event(raw):
            return raw
        try:
            return adapt_face_modal_json(raw, self.create_detection_event)
        except (TypeError, ValueError, KeyError):
            return self._create_error_event(
                "BRIDGE_ERROR",
                "Unexpected Modal face response shape",
            )

    def get_mock_event(self) -> dict:
        """Returns a mock face recognition event."""
        return self.create_detection_event(0.99, {
            "is_matched": True,
            "student_id": "a3f1c2d4-0000-0000-0000-000000000000",
            "faces_count": 1
        })

    def _create_error_event(self, code: str, message: str) -> dict:
        import datetime
        return {
            "service": self.service_name,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "confidence": 0.0,
            "sessionId": self.session_id,
            "payload": {
                "status": "error",
                "code": code,
                "message": message
            }
        }
