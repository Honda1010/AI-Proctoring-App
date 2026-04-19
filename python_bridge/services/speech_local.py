import pyaudio
import threading
import time
import asyncio
import datetime
import numpy as np
from typing import Dict, Any, Callable, Optional
from ai_base import AIService

class LocalSpeechDetectionService(AIService):
    """
    Local Speech Detection service using PyAudio and a background thread.
    """

    def __init__(self, session_id: str, config: dict, event_callback: Callable[[dict], None]):
        super().__init__("speech-detection", session_id, config)
        self.event_callback = event_callback
        
        # Load service specific config
        s_cfg = config.get("services", {}).get("speech-detection", {})
        self.chunk_size = s_cfg.get("chunk_size", 1024)
        self.sample_rate = s_cfg.get("sample_rate", 16000)
        self.threshold = s_cfg.get("threshold", 0.05)
        self.model_path = s_cfg.get("model_path")

        self._thread: Optional[threading.Thread] = None
        self._pa: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._is_speech_detected = False
        
        # Aggregation window (5 seconds as per clarification)
        self._agg_window = 5.0
        self._last_event_time = 0

    async def start(self):
        """Start the audio capture and detection thread."""
        if self.is_running:
            return

        try:
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
        except Exception as e:
            self._emit_hardware_error(f"Unable to access microphone: {str(e)}")
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    async def stop(self):
        """Stop the background thread and release hardware."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()

    async def predict(self, frame: str) -> dict:
        """Manual trigger - returns current state."""
        return self.create_detection_event(1.0, {"is_speech_detected": self._is_speech_detected})

    def get_mock_event(self) -> dict:
        """Returns a mock speech event."""
        return self.create_detection_event(0.75, {
            "is_speech_detected": True,
            "language": "en-US",
            "db_level": -24.5
        })

    def _run_loop(self):
        """Background audio processing loop."""
        
        # Energy aggregation buffers
        energy_buffer = []
        frames_per_window = int(self._agg_window * self.sample_rate / self.chunk_size)

        while self.is_running:
            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                samples = np.frombuffer(data, dtype=np.float32)
                
                # Simple energy-based detection
                energy = np.sqrt(np.mean(samples**2))
                energy_buffer.append(energy)
                
                if len(energy_buffer) >= frames_per_window:
                    avg_energy = np.mean(energy_buffer)
                    detected = avg_energy > self.threshold
                    
                    if detected != self._is_speech_detected:
                        event = self.create_detection_event(0.9, {
                            "is_speech_detected": detected,
                            "db_level": 20 * np.log10(avg_energy + 1e-6),
                            "language": "en-US"
                        })
                        self.event_callback(event)
                        self._is_speech_detected = detected
                    
                    energy_buffer = [] # Reset window

            except Exception as e:
                self._emit_hardware_error(f"Audio stream error: {str(e)}")
                break

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
