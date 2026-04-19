import cv2
import threading
import time
import asyncio
import datetime
from typing import Dict, Any, Callable, Optional
from ai_base import AIService

class LocalEyeGazeService(AIService):
    """
    Local Eye Gaze Detection service using OpenCV and a background thread.
    """

    def __init__(self, session_id: str, config: dict, event_callback: Callable[[dict], None]):
        super().__init__("eye-gaze", session_id, config)
        self.event_callback = event_callback
        
        # Load service specific config
        s_cfg = config.get("services", {}).get("eye-gaze", {})
        self.fps = s_cfg.get("fps", 5)
        self.camera_index = s_cfg.get("camera_index", 0)
        self.model_path = s_cfg.get("model_path")
        self.threshold = s_cfg.get("threshold", 0.5)

        self._thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._last_status = None

    async def start(self):
        """Start the background capture and inference thread."""
        if self.is_running:
            return

        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            # Emit hardware error via callback (wrapped in an async task if needed)
            self._emit_hardware_error("Unable to open webcam.")
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    async def stop(self):
        """Stop the background thread and release hardware."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
            self._cap = None

    async def predict(self, frame: str) -> dict:
        """
        The local service runs its own capture loop, so manual predict calls 
        from the router (which passes a frame) are ignored or return current state.
        """
        return self.create_detection_event(1.0, {"status": self._last_status or "initializing"})

    def get_mock_event(self) -> dict:
        """Returns a mock gaze event."""
        return self.create_detection_event(0.95, {
            "gaze_x": 0.5,
            "gaze_y": 0.5,
            "status": "on-screen"
        })

    def _run_loop(self):
        """Background thread loop."""
        interval = 1.0 / self.fps
        
        # In a real implementation, we would load the model here
        # model = load_model(self.model_path)

        while self.is_running:
            start_time = time.time()
            
            ret, frame = self._cap.read()
            if not ret:
                self._emit_hardware_error("Lost connection to webcam.")
                break

            # --- Placeholder for Real Gaze Inference ---
            # result = model.predict(frame)
            # For Phase 7, we simulate a gaze detection:
            status = "on-screen"
            confidence = 0.98
            # --------------------------------------------

            # Emit only on state change to reduce noise
            if status != self._last_status:
                event = self.create_detection_event(confidence, {
                    "gaze_x": 0.5,
                    "gaze_y": 0.5,
                    "status": status
                })
                self.event_callback(event)
                self._last_status = status

            # Throttle to FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)

    def _emit_hardware_error(self, message: str):
        error_event = {
            "method": "serviceError",
            "params": {
                "service": self.service_name,
                "code": "HARDWARE_FAILURE",
                "message": message
            }
        }
        self.event_callback(error_event)
        self.is_running = False
