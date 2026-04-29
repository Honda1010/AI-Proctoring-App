from ai_base import AIService
from modal_client import ModalClient
from modal_response_adapters import adapt_object_modal_json, is_bridge_detection_event

class ObjectDetectionService(AIService):
    """Object Detection service (hosted on Modal)."""

    def __init__(self, session_id: str, config: dict):
        super().__init__("object-detection", session_id, config)
        service_config = config.get("services", {}).get("object-detection", {})
        self.endpoint_url = service_config.get("endpoint_url")
        # Project-side confidence threshold for the suspicious flag.
        # Detections below this probability are logged but do not trigger alerts.
        self.probability_threshold: float = float(
            service_config.get("probability_threshold", 0.3)
        )
        self.timeout: float = float(service_config.get("timeout_seconds", 10.0))
        modal_config = config.get("modal", {})
        self.token = modal_config.get("token_id", "test-token")
        self.client = None

    async def start(self):
        if not self.endpoint_url:
            raise ValueError("Object Detection endpoint_url not configured")
        self.client = ModalClient(self.endpoint_url, self.token, timeout=self.timeout)
        self.is_running = True
        # Pre-warm Modal
        await self.client.predict(self.service_name, self.session_id, "WARMUP")

    async def stop(self):
        self.is_running = False
        self.client = None

    async def predict(self, frame: str) -> dict:
        """Process a frame using Modal cloud inference."""
        if not self.is_running:
            return self._create_error_event("SERVICE_NOT_RUNNING", "Service is not running")
        raw = await self.client.predict(self.service_name, self.session_id, frame)
        if is_bridge_detection_event(raw):
            return raw
        try:
            return adapt_object_modal_json(
                raw,
                self.create_detection_event,
                threshold=self.probability_threshold,
            )
        except (TypeError, ValueError, KeyError):
            return self._create_error_event(
                "BRIDGE_ERROR",
                "Unexpected Modal object-detection response shape",
            )

    def get_mock_event(self) -> dict:
        """Returns a mock object detection event."""
        return self.create_detection_event(0.88, {
            "objects": ["cell phone"],
            "count": 1,
            "suspicious": True
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
