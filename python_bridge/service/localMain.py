from __future__ import annotations

import base64
import logging
import threading
import time
from collections import deque
from datetime import datetime
from enum import Enum

import cv2
import numpy as np

try:
    from .Gaze import GazeDetector
except ImportError:  # pragma: no cover
    from Gaze import GazeDetector

logger = logging.getLogger(__name__)

# ── calibration ───────────────────────────────
SMOOTHING_BUFFER_SIZE = 3
ENVELOPE_WINDOW = 90

# ── away timers — horizontal ──────────────────
AWAY_SHORT_SECONDS_HORIZONTAL = 3.0
AWAY_LONG_SECONDS_HORIZONTAL = 5.0

# ── away timers — down (writing posture) ──────
AWAY_SHORT_SECONDS_DOWN_WRITE = 5.0
AWAY_LONG_SECONDS_DOWN_WRITE = 7.0

# ── away timers — down (lap / extreme) ────────
AWAY_SHORT_SECONDS_DOWN_LAP = 3.0
AWAY_LONG_SECONDS_DOWN_LAP = 5.0

# ── pitch thresholds ──────────────────────────
PITCH_LAP_THRESHOLD_WRITING = 24.0
PITCH_LAP_THRESHOLD_NORMAL  = 18.0

# ── long-term behavioral analysis ────────────
BEHAVIOR_WINDOW_SECONDS = 60.0
BEHAVIOR_MIN_EVENTS = 10
SUSTAINED_DOWN_MIN_SECONDS = 5.0
SUSTAINED_HORIZONTAL_MIN_SECONDS = 3.0
SUSTAINED_DOWN_SUSPICIOUS_RATIO = 0.30
SUSTAINED_HORIZONTAL_SUSPICIOUS_RATIO = 0.15
NO_FACE_SUSPICIOUS_RATIO = 0.15

# ── writing-pattern threshold ─────────────────
WRITING_PATTERN_AVG_EPISODE_MAX_SECONDS = 5.0

# ── tolerance cap ─────────────────────────────
TOLERANCE_Y_MAX = 0.08

# ── calibration failure ───────────────────────
CALIBRATION_TIMEOUT_SECONDS = 30.0
CALIBRATION_MIN_FACE_RATIO = 0.50


class SuspicionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class BehaviorEvent:
    __slots__ = ("timestamp", "state", "direction")

    def __init__(self, timestamp: float, state: str, direction: str):
        self.timestamp = timestamp
        self.state = state
        self.direction = direction


# ─────────────────────────────────────────────
# Session manager
# ─────────────────────────────────────────────
class SessionManager:
    def __init__(self):
        self.session: GazeSession | None = None
        """
        Safety lock in case the backend sends two batches at the same time
        to the same instance.
        """
        self.session_lock: threading.Lock = threading.Lock()

    def get_or_create(self, session_id: str) -> GazeSession:
        if self.session is None:
            self.session = GazeSession(session_id)
            logger.info(f"[SessionManager] Session created: {session_id}")
        return self.session

    def clear(self, session_id: str) -> None:
        self.session = None
        logger.info(f"[SessionManager] Session cleared: {session_id}")

    @property
    def lock(self) -> threading.Lock:
        return self.session_lock


manager = SessionManager()


def recalibrate_session(session_id: str) -> dict:
    """Reset calibration state for the given session so it can re-calibrate.

    Returns
    -------
    dict  with ``ok`` (bool) and ``message`` (str).
    """
    session = manager.session
    if session is None:
        return {"ok": False, "message": "No active session"}
    if session.session_id != session_id:
        return {"ok": False, "message": f"Session mismatch: expected {session.session_id}"}
    session.recalibrate()
    return {"ok": True, "message": "Calibration reset — collecting new baseline"}


def process_frames_batch(
    session_id: str,
    frames_b64: list[str],
    fps: int = 30,
    is_writing: bool = False,
) -> list[dict]:
    """Process a batch of base64-encoded frames for gaze detection.

    Parameters
    ----------
    session_id  : Unique ID for the exam attempt.
    frames_b64  : List of base64-encoded JPEG/PNG frames.
    fps         : Frame rate used to assign per-frame timestamps.
    is_writing  : Pass ``True`` when the current question's
                  ``IsAllowableToLookDown`` flag is ``True`` so the session
                  switches to writing mode (looking down is not penalised).
    """
    frame_interval = 1.0 / fps
    session = manager.get_or_create(session_id)

    with manager.lock:
        # Sync question-type mode before processing the batch so that the
        # correct timers and pitch thresholds apply for every frame.
        session.set_question_type(is_writing=is_writing)

        start = time.time()
        results = []
        batch_start_time = time.time()

        for index, frame_b64 in enumerate(frames_b64):
            frame_timestamp = batch_start_time + (index * frame_interval)

            try:
                img_bytes = base64.b64decode(frame_b64)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            except Exception as exc:
                logger.warning(f"[process_frames_batch] Frame {index} decode error: {exc}")
                frame = None

            if frame is None:
                h, v, face = 0.0, 0.0, False
                pitch_deg = 0.0
            else:
                t0 = time.time()
                h, v, face = session.detector.get_gaze_ratio(frame)
                pitch_deg = getattr(session.detector, "last_pitch_deg", 0.0)
                t1 = time.time()
                print(
                    f"  Frame {index:02d} | "
                    f"mediapipe={t1 - t0:.3f}s | "
                    f"face={face} | h={h:.3f} v={v:.3f} pitch={pitch_deg:.1f}°"
                )

            verdict, v_diag = session.process_gaze_result(
                h, v, face, pitch_deg=pitch_deg, timestamp=frame_timestamp
            )
            # Embed diagnostics directly into the verdict so callers get
            # direction, avg_x/y, pitch data, and zone info without a
            # separate return value.
            verdict["gaze_diagnostics"] = {
                "direction":              session.last_direction,
                "gaze_h":                 round(h, 4),
                "gaze_v":                 round(v, 4),
                "avg_x":                  round(v_diag.get("avg_x", h), 4),
                "avg_y":                  round(v_diag.get("avg_y", v), 4),
                "pitch_deg":              round(pitch_deg, 2),
                "pitch_zone":             v_diag.get("pitch_zone", "LEVEL"),
                "looking_down":           v_diag.get("looking_down", False),
                "v_outside":              v_diag.get("v_outside", False),
                "baseline_pitch":         round(v_diag.get("baseline_pitch") or 0.0, 2),
                "active_pitch_threshold": round(v_diag.get("active_pitch_threshold") or 0.0, 2),
                "question_type":          session.question_type,
            }
            results.append(verdict)

        elapsed = time.time() - start
        print(
            f"[GazeSession] {len(frames_b64)} frames processed locally "
            f"in {elapsed:.2f}s  (~{elapsed / len(frames_b64) * 1000:.1f}ms/frame)"
        )

    return results


# ─────────────────────────────────────────────
# GazeSession
# ─────────────────────────────────────────────
class GazeSession:
    QUESTION_TYPE_NORMAL  = "normal"
    QUESTION_TYPE_WRITING = "writing"

    def __init__(self, session_id: str, question_type: str = "normal"):
        self.session_id = session_id
        self.detector = GazeDetector()

        self._question_type: str = question_type

        self.gaze_history_x: deque[float] = deque(maxlen=SMOOTHING_BUFFER_SIZE)
        self.envelope_x: deque[float] = deque(maxlen=ENVELOPE_WINDOW)
        self.baseline_center_x: float | None = None
        self.baseline_std_x: float | None = None

        self.gaze_history_y: deque[float] = deque(maxlen=SMOOTHING_BUFFER_SIZE)
        self.envelope_y: deque[float] = deque(maxlen=ENVELOPE_WINDOW)
        self.baseline_center_y: float | None = None
        self.baseline_std_y: float | None = None

        self.pitch_envelope: deque[float] = deque(maxlen=ENVELOPE_WINDOW)
        self.baseline_pitch: float | None = None

        self.initialized: bool = False
        self.calibration_failed: bool = False
        self.attention_state: str = "INITIALIZING"

        # ── calibration progress tracking ─────────────────────────────
        self._calibration_start_time: float | None = None
        self._calibration_total_frames: int = 0
        self._calibration_no_face_frames: int = 0

        self.away_start_time_horizontal: float | None = None
        self.away_start_time_vertical_write: float | None = None
        self.away_start_time_vertical_lap: float | None = None

        self.last_direction: str = "CENTER"
        self.behavior_history: deque[BehaviorEvent] = deque(maxlen=10000)

        self._continuous_down_start: float | None = None
        self._continuous_horizontal_start: float | None = None
        self._total_sustained_down_seconds: float = 0.0
        self._total_sustained_horizontal_seconds: float = 0.0
        self._total_no_face_seconds: float = 0.0
        self._session_start_time: float = time.time()
        self._last_process_time: float | None = None
        self.model_id: int = 0

        logger.info(
            f"[GazeSession] Initialized: {session_id} | question_type={self._question_type}"
        )

    # ── question-type API ─────────────────────────────────────────────
    @property
    def question_type(self) -> str:
        return self._question_type

    def set_question_type(self, is_writing: bool) -> None:
        """Switch MCQ mode when the backend sends a new question.

        Parameters
        ----------
        is_writing : bool
            False → normal MCQ  (looking down is flagged quickly).
            True  → writing MCQ (looking down to write is ignored).
        """
        qtype = self.QUESTION_TYPE_WRITING if is_writing else self.QUESTION_TYPE_NORMAL
        if qtype != self._question_type:
            logger.info(
                f"[GazeSession] question_type: {self._question_type!r} → {qtype!r}"
            )
            self._question_type = qtype
            self.away_start_time_vertical_write = None
            self.away_start_time_vertical_lap = None

    # ── recalibration ─────────────────────────────────────────────────
    def recalibrate(self) -> None:
        """Reset all calibration state so the session can re-collect baselines."""
        self.envelope_x.clear()
        self.envelope_y.clear()
        self.pitch_envelope.clear()
        self.gaze_history_x.clear()
        self.gaze_history_y.clear()

        self.baseline_center_x = None
        self.baseline_std_x = None
        self.baseline_center_y = None
        self.baseline_std_y = None
        self.baseline_pitch = None

        self.initialized = False
        self.calibration_failed = False
        self.attention_state = "INITIALIZING"

        self._calibration_start_time = None
        self._calibration_total_frames = 0
        self._calibration_no_face_frames = 0

        self.away_start_time_horizontal = None
        self.away_start_time_vertical_write = None
        self.away_start_time_vertical_lap = None

        logger.info(f"[GazeSession] Recalibration started for session {self.session_id}")

    # ── classify gaze ─────────────────────────────────────────────────
    def _classify_gaze(
        self, avg_x: float, avg_y: float, pitch_deg: float,
        pitch_lap_threshold: float = PITCH_LAP_THRESHOLD_WRITING,
    ) -> tuple[str, str, dict]:
        h_deviation = avg_x - self.baseline_center_x
        v_deviation = avg_y - self.baseline_center_y
        h_abs = abs(h_deviation)
        v_abs = abs(v_deviation)

        tolerance_x = max(0.07, self.baseline_std_x * 3.5)
        tolerance_y = min(TOLERANCE_Y_MAX, max(0.04, self.baseline_std_y * 2.0))

        h_outside = h_abs > tolerance_x
        looking_down = v_deviation > 0
        v_outside = v_abs > tolerance_y and looking_down

        if h_outside and v_outside:
            axis_outside = "BOTH"
        elif h_outside:
            axis_outside = "HORIZONTAL"
        elif v_outside:
            axis_outside = "VERTICAL"
        else:
            axis_outside = "NONE"

        if axis_outside == "NONE":
            direction = "CENTER"
        elif axis_outside == "HORIZONTAL":
            direction = "LEFT_RIGHT"
        elif axis_outside == "VERTICAL":
            direction = "DOWN_LAP" if pitch_deg > pitch_lap_threshold else "DOWN"
        else:
            h_norm = h_abs / tolerance_x
            v_norm = v_abs / tolerance_y
            if h_norm >= v_norm:
                direction = "LEFT_RIGHT"
            else:
                direction = "DOWN_LAP" if pitch_deg > pitch_lap_threshold else "DOWN"

        pitch_zone = (
            "LAP" if pitch_deg > pitch_lap_threshold
            else "WRITING" if pitch_deg < pitch_lap_threshold * 0.9
            else "LEVEL"
        )

        diag = {
            "v_deviation": v_deviation, "tolerance_y": tolerance_y,
            "looking_down": looking_down, "v_outside": v_outside,
            "h_deviation": h_deviation, "tolerance_x": tolerance_x,
            "pitch_zone": pitch_zone,
        }
        return direction, axis_outside, diag

    # ── main processing ───────────────────────────────────────────────
    def process_gaze_result(
        self,
        h_ratio: float,
        v_ratio: float,
        face_present: bool,
        pitch_deg: float = 0.0,
        timestamp: float | None = None,
    ) -> tuple[dict, dict]:
        _empty_diag: dict = {
            "raw_v": 0.0, "avg_y": 0.0, "v_deviation": 0.0,
            "tolerance_y": 0.0, "looking_down": False, "v_outside": False,
            "baseline_center_y": None, "baseline_std_y": None,
            "pitch_deg": 0.0, "pitch_zone": "LEVEL",
            "baseline_pitch": self.baseline_pitch,
            "active_pitch_threshold": None,
        }

        current_time = timestamp if timestamp is not None else time.time()
        dt = (current_time - self._last_process_time) if self._last_process_time else 1.0 / 30.0
        self._last_process_time = current_time

        # ── calibration-failed guard ──────────────────────────────────
        if self.calibration_failed:
            self.behavior_history.append(BehaviorEvent(current_time, "CALIBRATION_FAILED", "UNKNOWN"))
            suspicion = self._compute_behavioral_suspicion(current_time)
            fail_diag = {
                **_empty_diag,
                "calibration_failed": True,
                "calibration_face_ratio": (
                    (self._calibration_total_frames - self._calibration_no_face_frames)
                    / max(1, self._calibration_total_frames)
                ),
            }
            return self._build_event(
                "CALIBRATION_FAILED", 0.0, "CALIBRATION_FAILED", current_time, suspicion
            ), fail_diag

        # ── no face ───────────────────────────────────────────────────
        if not face_present:
            # Track no-face during calibration for timeout logic
            if not self.initialized:
                self._calibration_total_frames += 1
                self._calibration_no_face_frames += 1
                if self._calibration_start_time is None:
                    self._calibration_start_time = current_time
                # Check for calibration timeout
                elapsed_cal = current_time - self._calibration_start_time
                if elapsed_cal >= CALIBRATION_TIMEOUT_SECONDS:
                    face_ratio = (
                        (self._calibration_total_frames - self._calibration_no_face_frames)
                        / max(1, self._calibration_total_frames)
                    )
                    if face_ratio < CALIBRATION_MIN_FACE_RATIO:
                        self.calibration_failed = True
                        self.attention_state = "CALIBRATION_FAILED"
                        logger.warning(
                            f"[GazeSession] Calibration FAILED — "
                            f"face ratio {face_ratio:.1%} < {CALIBRATION_MIN_FACE_RATIO:.0%} "
                            f"after {elapsed_cal:.1f}s"
                        )
                        self.behavior_history.append(
                            BehaviorEvent(current_time, "CALIBRATION_FAILED", "UNKNOWN")
                        )
                        suspicion = self._compute_behavioral_suspicion(current_time)
                        return self._build_event(
                            "CALIBRATION_FAILED", 0.0, "CALIBRATION_FAILED",
                            current_time, suspicion,
                        ), {**_empty_diag, "calibration_failed": True, "calibration_face_ratio": face_ratio}

            if self._continuous_down_start is not None:
                dur = current_time - self._continuous_down_start
                if dur >= SUSTAINED_DOWN_MIN_SECONDS:
                    self._total_sustained_down_seconds += dur
            if self._continuous_horizontal_start is not None:
                dur = current_time - self._continuous_horizontal_start
                if dur >= SUSTAINED_HORIZONTAL_MIN_SECONDS:
                    self._total_sustained_horizontal_seconds += dur

            self.attention_state = "NO_FACE"
            self.away_start_time_horizontal = None
            self.away_start_time_vertical_write = None
            self.away_start_time_vertical_lap = None
            self._continuous_down_start = None
            self._continuous_horizontal_start = None
            self._total_no_face_seconds += dt

            self.behavior_history.append(BehaviorEvent(current_time, "NO_FACE", "UNKNOWN"))
            suspicion = self._compute_behavioral_suspicion(current_time)
            return self._build_event("NO_FACE", 1.0, "NO_FACE", current_time, suspicion), _empty_diag

        # ── calibrating ───────────────────────────────────────────────
        if not self.initialized:
            if self._calibration_start_time is None:
                self._calibration_start_time = current_time
            self._calibration_total_frames += 1

            self.envelope_x.append(h_ratio)
            self.envelope_y.append(v_ratio)
            if pitch_deg != 0.0:
                self.pitch_envelope.append(pitch_deg)
            if len(self.envelope_x) >= ENVELOPE_WINDOW and len(self.envelope_y) >= ENVELOPE_WINDOW:
                self.initialized = True
                self.calibration_failed = False
                logger.info(f"[GazeSession] Calibration complete — {ENVELOPE_WINDOW} frames")

            # Check for calibration timeout (face present but envelope not full)
            if not self.initialized:
                elapsed_cal = current_time - self._calibration_start_time
                if elapsed_cal >= CALIBRATION_TIMEOUT_SECONDS:
                    face_ratio = (
                        (self._calibration_total_frames - self._calibration_no_face_frames)
                        / max(1, self._calibration_total_frames)
                    )
                    if face_ratio < CALIBRATION_MIN_FACE_RATIO:
                        self.calibration_failed = True
                        self.attention_state = "CALIBRATION_FAILED"
                        logger.warning(
                            f"[GazeSession] Calibration FAILED — "
                            f"face ratio {face_ratio:.1%} < {CALIBRATION_MIN_FACE_RATIO:.0%} "
                            f"after {elapsed_cal:.1f}s"
                        )
                        self.behavior_history.append(
                            BehaviorEvent(current_time, "CALIBRATION_FAILED", "UNKNOWN")
                        )
                        suspicion = self._compute_behavioral_suspicion(current_time)
                        return self._build_event(
                            "CALIBRATION_FAILED", 0.0, "CALIBRATION_FAILED",
                            current_time, suspicion,
                        ), {**_empty_diag, "calibration_failed": True, "calibration_face_ratio": face_ratio}

            self.behavior_history.append(BehaviorEvent(current_time, "INITIALIZING", "CENTER"))
            suspicion = self._compute_behavioral_suspicion(current_time)
            cal_diag = {
                **_empty_diag,
                "raw_v": v_ratio, "avg_y": v_ratio, "pitch_deg": pitch_deg,
                "baseline_pitch": self.baseline_pitch, "active_pitch_threshold": None,
                "calibration_progress": len(self.envelope_x),
                "calibration_target": ENVELOPE_WINDOW,
            }
            return self._build_event("INITIALIZING", 0.0, "CALIBRATING", current_time, suspicion), cal_diag

        # ── baselines (set once after calibration) ────────────────────
        if self.baseline_center_x is None:
            self.baseline_center_x = float(np.median(self.envelope_x))
            self.baseline_std_x = float(np.std(self.envelope_x))
        if self.baseline_center_y is None:
            self.baseline_center_y = float(np.median(self.envelope_y))
            self.baseline_std_y = float(np.std(self.envelope_y))
        if self.baseline_pitch is None:
            if len(self.pitch_envelope) >= max(10, ENVELOPE_WINDOW // 3):
                self.baseline_pitch = float(np.max(self.pitch_envelope))
                logger.info(
                    f"[GazeSession] Pitch baseline — neutral={self.baseline_pitch:.1f}° | "
                    f"effective normal={self.baseline_pitch + PITCH_LAP_THRESHOLD_NORMAL:.1f}° | "
                    f"effective writing={self.baseline_pitch + PITCH_LAP_THRESHOLD_WRITING:.1f}°"
                )
            else:
                self.baseline_pitch = 0.0
                logger.warning("[GazeSession] Pitch baseline: insufficient samples, defaulting to 0°")

        # ── smooth ────────────────────────────────────────────────────
        self.gaze_history_x.append(h_ratio)
        self.gaze_history_y.append(v_ratio)
        avg_x = sum(self.gaze_history_x) / len(self.gaze_history_x)
        avg_y = sum(self.gaze_history_y) / len(self.gaze_history_y)

        # ── classify (pitch-aware) ────────────────────────────────────
        _pitch_offset = (
            PITCH_LAP_THRESHOLD_WRITING
            if self._question_type == self.QUESTION_TYPE_WRITING
            else PITCH_LAP_THRESHOLD_NORMAL
        )
        _neutral = self.baseline_pitch if self.baseline_pitch is not None else 0.0
        active_pitch_threshold = _neutral + _pitch_offset
        direction, axis_outside, _diag = self._classify_gaze(
            avg_x, avg_y, pitch_deg, pitch_lap_threshold=active_pitch_threshold
        )

        # ── question-type override ────────────────────────────────────
        if direction == "DOWN" and self._question_type == self.QUESTION_TYPE_WRITING:
            direction = "CENTER"
            axis_outside = "NONE"

        v_diag = {
            "raw_v": v_ratio, "avg_x": avg_x, "avg_y": avg_y,
            "v_deviation": _diag["v_deviation"], "tolerance_y": _diag["tolerance_y"],
            "looking_down": _diag["looking_down"], "v_outside": _diag["v_outside"],
            "baseline_center_y": self.baseline_center_y, "baseline_std_y": self.baseline_std_y,
            "pitch_deg": pitch_deg, "pitch_zone": _diag["pitch_zone"],
            "baseline_pitch": self.baseline_pitch,
            "active_pitch_threshold": active_pitch_threshold,
        }

        if direction != self.last_direction:
            logger.info(
                f"[GazeSession] Direction: {self.last_direction} → {direction} | "
                f"avg_x={avg_x:.3f} avg_y={avg_y:.3f} pitch={pitch_deg:.1f}°"
            )
            self.last_direction = direction

        self.behavior_history.append(BehaviorEvent(current_time, self.attention_state, direction))

        is_down = direction in ("DOWN", "DOWN_LAP")
        inside_safe_zone = axis_outside == "NONE"
        self._update_sustained_trackers(direction, current_time, inside_safe_zone, is_down)

        # ── away-timer logic ──────────────────────────────────────────
        if inside_safe_zone:
            self.attention_state = "ON_SCREEN"
            self.away_start_time_horizontal = None
            self.away_start_time_vertical_write = None
            self.away_start_time_vertical_lap = None
        else:
            if direction == "LEFT_RIGHT":
                if self.away_start_time_horizontal is None:
                    self.away_start_time_horizontal = current_time
                self.away_start_time_vertical_write = None
                self.away_start_time_vertical_lap = None
                elapsed = current_time - self.away_start_time_horizontal
                self.attention_state = (
                    "AWAY_LONG" if elapsed >= AWAY_LONG_SECONDS_HORIZONTAL
                    else "AWAY_SHORT" if elapsed >= AWAY_SHORT_SECONDS_HORIZONTAL
                    else "ON_SCREEN"
                )

            elif direction == "DOWN":
                if self.away_start_time_vertical_write is None:
                    self.away_start_time_vertical_write = current_time
                self.away_start_time_horizontal = None
                self.away_start_time_vertical_lap = None
                elapsed = current_time - self.away_start_time_vertical_write
                self.attention_state = (
                    "AWAY_LONG" if elapsed >= AWAY_LONG_SECONDS_DOWN_WRITE
                    else "AWAY_SHORT" if elapsed >= AWAY_SHORT_SECONDS_DOWN_WRITE
                    else "ON_SCREEN"
                )

            elif direction == "DOWN_LAP":
                if self.away_start_time_vertical_lap is None:
                    self.away_start_time_vertical_lap = current_time
                self.away_start_time_horizontal = None
                self.away_start_time_vertical_write = None
                elapsed = current_time - self.away_start_time_vertical_lap
                self.attention_state = (
                    "AWAY_LONG" if elapsed >= AWAY_LONG_SECONDS_DOWN_LAP
                    else "AWAY_SHORT" if elapsed >= AWAY_SHORT_SECONDS_DOWN_LAP
                    else "ON_SCREEN"
                )
            else:
                self.attention_state = "ON_SCREEN"

        probability = {"ON_SCREEN": 0.0, "AWAY_SHORT": 0.5}.get(self.attention_state, 1.0)
        suspicion = self._compute_behavioral_suspicion(current_time)

        return self._build_event(
            self.attention_state, probability, self.attention_state, current_time, suspicion
        ), v_diag

    # ── sustained-gaze trackers ───────────────────────────────────────
    def _update_sustained_trackers(
        self, direction: str, current_time: float, inside_safe_zone: bool, is_down: bool
    ) -> None:
        if inside_safe_zone:
            if self._continuous_down_start is not None:
                dur = current_time - self._continuous_down_start
                if dur >= SUSTAINED_DOWN_MIN_SECONDS:
                    self._total_sustained_down_seconds += dur
                self._continuous_down_start = None
            if self._continuous_horizontal_start is not None:
                dur = current_time - self._continuous_horizontal_start
                if dur >= SUSTAINED_HORIZONTAL_MIN_SECONDS:
                    self._total_sustained_horizontal_seconds += dur
                self._continuous_horizontal_start = None
        else:
            if is_down:
                if self._continuous_down_start is None:
                    self._continuous_down_start = current_time
                if self._continuous_horizontal_start is not None:
                    dur = current_time - self._continuous_horizontal_start
                    if dur >= SUSTAINED_HORIZONTAL_MIN_SECONDS:
                        self._total_sustained_horizontal_seconds += dur
                    self._continuous_horizontal_start = None
            elif direction == "LEFT_RIGHT":
                if self._continuous_horizontal_start is None:
                    self._continuous_horizontal_start = current_time
                if self._continuous_down_start is not None:
                    dur = current_time - self._continuous_down_start
                    if dur >= SUSTAINED_DOWN_MIN_SECONDS:
                        self._total_sustained_down_seconds += dur
                    self._continuous_down_start = None

    # ── behavioural suspicion ─────────────────────────────────────────
    def _compute_behavioral_suspicion(self, current_time: float) -> dict:
        window_start = current_time - BEHAVIOR_WINDOW_SECONDS
        recent: list[BehaviorEvent] = []
        for e in reversed(self.behavior_history):
            if e.timestamp >= window_start:
                recent.append(e)
            else:
                break
        recent.reverse()

        if len(recent) < BEHAVIOR_MIN_EVENTS:
            return {
                "level": SuspicionLevel.LOW, "score": 0.0,
                "down_ratio": 0.0, "down_lap_ratio": 0.0,
                "horizontal_ratio": 0.0, "no_face_ratio": 0.0,
                "transitions": 0, "detail": "insufficient data",
            }

        total = len(recent)
        down_write_count  = sum(1 for e in recent if e.direction == "DOWN")
        down_lap_count    = sum(1 for e in recent if e.direction == "DOWN_LAP")
        horizontal_count  = sum(1 for e in recent if e.direction == "LEFT_RIGHT")
        no_face_count     = sum(1 for e in recent if e.state == "NO_FACE")

        down_write_ratio  = down_write_count / total
        down_lap_ratio    = down_lap_count / total
        horizontal_ratio  = horizontal_count / total
        no_face_ratio     = no_face_count / total

        transitions = sum(
            1 for i in range(1, len(recent))
            if (recent[i - 1].state == "ON_SCREEN") != (recent[i].state == "ON_SCREEN")
        )

        raw_score = (
            horizontal_ratio * 0.40
            + down_lap_ratio * 0.35
            + down_write_ratio * 0.10
            + no_face_ratio * 0.15
        )

        down_total = down_write_count + down_lap_count
        detail = "gaze appears normal"

        if (down_total / total) > 0.10 and down_total > 0:
            down_episodes = sum(
                1 for i in range(len(recent))
                if recent[i].direction in ("DOWN", "DOWN_LAP")
                and (i == 0 or recent[i - 1].direction not in ("DOWN", "DOWN_LAP"))
            )
            if down_episodes > 0:
                avg_ep_sec = (down_total / down_episodes) / 30.0
                if avg_ep_sec < WRITING_PATTERN_AVG_EPISODE_MAX_SECONDS:
                    raw_score *= 0.70
                    detail = f"writing pattern — avg down episode {avg_ep_sec:.1f}s"
                else:
                    detail = f"sustained down gaze — avg down episode {avg_ep_sec:.1f}s"
            else:
                detail = "sustained down gaze detected"
        elif horizontal_ratio > 0.25:
            detail = "frequent horizontal gaze detected"
        elif no_face_ratio > NO_FACE_SUSPICIOUS_RATIO:
            detail = "frequent face absence detected"

        session_elapsed = max(1.0, current_time - self._session_start_time)

        ongoing_down = 0.0
        if self._continuous_down_start is not None:
            o = current_time - self._continuous_down_start
            if o >= SUSTAINED_DOWN_MIN_SECONDS:
                ongoing_down = o

        ongoing_horizontal = 0.0
        if self._continuous_horizontal_start is not None:
            o = current_time - self._continuous_horizontal_start
            if o >= SUSTAINED_HORIZONTAL_MIN_SECONDS:
                ongoing_horizontal = o

        if (self._total_sustained_horizontal_seconds + ongoing_horizontal) / session_elapsed > SUSTAINED_HORIZONTAL_SUSPICIOUS_RATIO:
            raw_score = min(1.0, raw_score + 0.20)
            detail += " | high sustained horizontal in session"

        if (self._total_sustained_down_seconds + ongoing_down) / session_elapsed > SUSTAINED_DOWN_SUSPICIOUS_RATIO:
            raw_score = min(1.0, raw_score + 0.10)
            detail += " | high sustained down in session"

        raw_score = float(np.clip(raw_score, 0.0, 1.0))
        level = (
            SuspicionLevel.HIGH   if raw_score >= 0.60
            else SuspicionLevel.MEDIUM if raw_score >= 0.30
            else SuspicionLevel.LOW
        )

        return {
            "level": level, "score": round(raw_score, 4),
            "down_ratio": round(down_write_ratio, 4),
            "down_lap_ratio": round(down_lap_ratio, 4),
            "horizontal_ratio": round(horizontal_ratio, 4),
            "no_face_ratio": round(no_face_ratio, 4),
            "transitions": transitions, "detail": detail,
        }

    # ── event builder ─────────────────────────────────────────────────
    def _build_event(
        self,
        state: str,
        probability: float,
        evidence: str,
        timestamp: float | None = None,
        suspicion: dict | None = None,
    ) -> dict:
        self.model_id += 1
        ts = (
            datetime.fromtimestamp(timestamp).isoformat()
            if timestamp else datetime.now().isoformat()
        )
        return {
            "id": self.model_id,
            "timestamp": ts,
            "flag": state,
            "probability": round(probability, 4),
            "evidence": evidence,
            "suspicion": suspicion or {
                "level": SuspicionLevel.LOW, "score": 0.0,
                "down_ratio": 0.0, "down_lap_ratio": 0.0,
                "horizontal_ratio": 0.0, "no_face_ratio": 0.0,
                "transitions": 0, "detail": "no data",
            },
        }
