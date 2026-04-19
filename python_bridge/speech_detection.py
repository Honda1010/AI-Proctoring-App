from ai_base import AIService

class SpeechDetectionService(AIService):
    """Speech Detection service stub (runs locally)."""

    def __init__(self, session_id: str, config: dict):
        super().__init__("speech-detection", session_id, config)

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def predict(self, frame: str) -> dict:
        """Process audio for speech detection (stub)."""
        return self.get_mock_event()

    def get_mock_event(self) -> dict:
        """Returns a mock speech event."""
        return self.create_detection_event(0.75, {
            "is_speech_detected": True,
            "language": "en-US",
            "db_level": -24.5
        })
