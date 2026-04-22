# python_bridge/services/speech_local.py

import datetime
import threading
import time
from typing import Dict, Any, List, Optional

import numpy as np
import sounddevice as sd
import torch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_base import AIService


# ──────────────────────────────────────────────
# Configuration — tweak these without touching logic
# ──────────────────────────────────────────────
SAMPLE_RATE = 16000
CHUNK = 512
SPEECH_PROB_THRESHOLD = 0.5
CHEATING_DURATION = 5.0   # seconds of speech = 1 strike
CHEATING_THRESHOLD = 5    # strikes before flagging as cheater
ALLOWED_PAUSE = 1.5       # silence gap that resets the speech timer
MIN_SPEECH_SEGMENT = 1.0  # minimum segment length to count as speech
VIOLATION_COOLDOWN = 1.0  # avoid duplicate alerts from jittery boundaries


class SpeechDetectionService(AIService):
    """
    Listens to the local microphone using Silero VAD.
    Violations accumulate internally and are flushed on every predict() poll.

    Threading model:
      - sounddevice fires _audio_callback() from its own C-level thread (writes state)
      - predict() is called from the async server thread (reads state)
      - threading.Lock guards all shared mutable state between the two
    """

    def __init__(self, session_id: str, config: Dict[str, Any]):
        super().__init__("speech-detection", session_id, config)

        speech_cfg = (config or {}).get("services", {}).get("speech-detection", {})
        self._energy_threshold = float(speech_cfg.get("threshold", 0.02))
        self._use_energy_fallback = False

        # ── Load Silero VAD once at init time (fallback to energy VAD if unavailable) ──
        print("[SpeechDetection] Loading Silero VAD model...")
        try:
            self._model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            self._model.eval()
            print("[SpeechDetection] Model ready.")
        except Exception as e:
            self._model = None
            self._use_energy_fallback = True
            print(f"[SpeechDetection] Silero unavailable ({e}). Using RMS fallback detector.")

        # ── Stream handle ──
        self._stream: Optional[sd.InputStream] = None

        # ── Shared state (guarded by _lock) ──
        # Written by sounddevice thread, read by async predict()
        self._lock = threading.Lock()
        self._violation_log: List[Dict[str, Any]] = []
        self._cheat_counter: int = 0
        self._is_cheater: bool = False

        # ── Speech timing state ──
        # Only touched inside _audio_callback, so no lock needed
        self._is_speaking: bool = False
        self._speech_start_time: float = 0.0
        self._last_speech_time: float = 0.0
        self._last_violation_time: float = 0.0

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────

    async def start(self):
        """Open the microphone stream and begin VAD in the background."""
        if self.is_running:
            print("[SpeechDetection] Already running.")
            return

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            blocksize=CHUNK,
            callback=self._audio_callback  # sounddevice calls this every ~32ms
        )
        self._stream.start()
        self.is_running = True
        print("[SpeechDetection] Microphone stream started.")

    async def stop(self):
        """Stop the microphone stream cleanly."""
        if not self.is_running:
            return

        self.is_running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print("[SpeechDetection] Microphone stream stopped.")

    # ──────────────────────────────────────────────
    # Poll endpoint — called by frontend every ~2 seconds
    # ──────────────────────────────────────────────

    async def predict(self, frame: str) -> Dict[str, Any]:
        """
        Flush and return all violations recorded since the last poll.
        `frame` is intentionally unused — audio is captured locally via sounddevice.
        """
        with self._lock:
            flushed = self._violation_log.copy()
            self._violation_log.clear()
            strikes = self._cheat_counter
            is_cheater = self._is_cheater

        return self.create_detection_event(
            confidence=1.0,
            payload={
                "new_violations": flushed,          # list of violation dicts since last poll
                "violation_count": len(flushed),
                "total_strikes": strikes,
                "is_cheater": is_cheater,
            }
        )

    # ──────────────────────────────────────────────
    # Audio callback — runs on sounddevice's internal C thread
    # ──────────────────────────────────────────────

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status: sd.CallbackFlags
    ):
        """Called every ~32ms. Must be fast and non-blocking."""
        if not self.is_running:
            return

        # 1. Prepare tensor
        audio = indata[:, 0]
        tensor = torch.from_numpy(audio.copy())

        # 2. VAD inference
        try:
            if self._use_energy_fallback:
                # Scale RMS energy to a pseudo-probability in [0, 1].
                rms = float(np.sqrt(np.mean(np.square(audio))))
                speech_prob = min(1.0, max(0.0, rms / max(self._energy_threshold * 2.0, 1e-6)))
            else:
                speech_prob = self._model(tensor, SAMPLE_RATE).item()
        except Exception as e:
            print(f"[SpeechDetection] VAD error: {e}")
            return

        current_time = time.time()

        # 3. State machine
        if speech_prob > SPEECH_PROB_THRESHOLD:
            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start_time = current_time
                print("\n[SpeechDetection] Speech started.")

            self._last_speech_time = current_time

        else:
            if self._is_speaking:
                if current_time - self._last_speech_time > ALLOWED_PAUSE:
                    segment_duration = max(0.0, self._last_speech_time - self._speech_start_time)
                    should_count_segment = (
                        segment_duration >= MIN_SPEECH_SEGMENT
                        and current_time - self._last_violation_time >= VIOLATION_COOLDOWN
                    )
                    if should_count_segment:
                        self._record_violation(segment_duration)
                        self._last_violation_time = current_time

                    print(
                        f"\n[SpeechDetection] Speech ended "
                        f"(segment={segment_duration:.2f}s). Total strikes: {self._cheat_counter}"
                    )
                    self._is_speaking = False

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    def _record_violation(self, duration: float):
        """Append a violation to the log. Called from sounddevice thread → use lock."""
        with self._lock:
            self._cheat_counter += 1
            self._is_cheater = self._cheat_counter >= CHEATING_THRESHOLD

            self._violation_log.append({
                "type": "speech_violation",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "duration_seconds": round(duration, 2),
                "strike_number": self._cheat_counter,
                "cheater_flagged": self._is_cheater,
            })

        flag = " CHEATER FLAGGED" if self._is_cheater else ""
        print(f"[SpeechDetection] Strike {self._cheat_counter}/{CHEATING_THRESHOLD}{flag}")