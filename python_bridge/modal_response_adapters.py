"""
Map Modal FastAPI JSON bodies into bridge DetectionEvent dicts.

The desktop bridge validates every predict() result against ai-service-contract.json.
Hosted Modal routes return module-specific shapes (e.g. {"face_recognition": {...}},
OWL-ViT evidence dict) rather than top-level DetectionEvents — normalize here.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

_BRIDGE_SERVICES = frozenset(
    {"eye-gaze", "object-detection", "face-recognition", "speech-detection"}
)


def is_bridge_detection_event(data: Any) -> bool:
    """True if *data* is already a normalized DetectionEvent (including Modal error events)."""
    if not isinstance(data, dict):
        return False
    if data.get("service") not in _BRIDGE_SERVICES:
        return False
    if not isinstance(data.get("payload"), dict):
        return False
    for key in ("timestamp", "confidence", "sessionId"):
        if key not in data:
            return False
    return True


def _parse_percent_or_fraction(val: Any) -> float:
    """Parse API fields that may be 0.85, 85, or \"85%\" into [0, 1]."""
    if val is None:
        return 0.0
    if isinstance(val, bool):
        return 1.0 if val else 0.0
    if isinstance(val, (int, float)):
        x = float(val)
        if x > 1.0:
            return max(0.0, min(1.0, x / 100.0))
        return max(0.0, min(1.0, x))
    if isinstance(val, str):
        s = val.strip()
        if s.endswith("%"):
            s = s[:-1].strip()
        try:
            x = float(s)
        except ValueError:
            return 0.0
        if x > 1.0:
            return max(0.0, min(1.0, x / 100.0))
        return max(0.0, min(1.0, x))
    return 0.0


def _infer_face_is_matched(inner: Dict[str, Any]) -> bool:
    """
    Map Modal `face_recognition` object to bridge `is_matched` (True = authorised / OK).

    The FaceRecognition pipeline in AI/Models/Face_Recognition_Service/face_recognition.py
    sets `flag`: True means suspicious (spoof, mismatch, no face, etc.), False means match.
    Cosine similarity is compared to `similarity_threshold` (default 0.5) inside `verify()`;
    that threshold is not repeated in the JSON — you see the outcome as `flag` / `result` /
    `evidence`.

    Some deployments strip `flag`; never default missing `flag` to True (that marks everyone
    as not matched). Use `result` or `evidence` when `flag` is absent.
    """
    if "flag" in inner and inner["flag"] is not None:
        return not bool(inner["flag"])

    result = inner.get("result")
    if isinstance(result, str):
        r = result.strip()
        if r == "No Cheating":
            return True
        if r == "Cheating Detected":
            return False

    ev = (inner.get("evidence") or "").lower()
    if "authorised person verified" in ev or "authorized person verified" in ev:
        return True
    if "no enrollment" in ev:
        return False
    if "no face detected" in ev:
        return False
    if "face does not match" in ev or "does not match reference" in ev:
        return False
    if "multiple faces" in ev:
        return False
    if "spoof detected" in ev:
        return False

    try:
        faces = int(inner.get("num_faces", 0) or 0)
    except (TypeError, ValueError):
        faces = 0
    if faces < 1:
        return False

    prob = _parse_percent_or_fraction(inner.get("probability"))
    return prob > 0.5


def adapt_face_modal_json(
    body: Dict[str, Any],
    create_detection_event: Callable[[float, Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    inner = body.get("face_recognition")
    if not isinstance(inner, dict):
        raise ValueError("Modal face response missing face_recognition object")

    is_matched = _infer_face_is_matched(inner)
    conf = _parse_percent_or_fraction(inner.get("probability"))
    if conf <= 0.0 and is_matched:
        conf = _parse_percent_or_fraction(inner.get("match_similarity"))
    if conf <= 0.0:
        conf = 0.01 if is_matched else 0.0
    conf = max(0.0, min(1.0, conf))

    try:
        faces = int(inner.get("num_faces", 0) or 0)
    except (TypeError, ValueError):
        faces = 0

    payload: Dict[str, Any] = {
        "is_matched": is_matched,
        "faces_count": faces,
    }
    return create_detection_event(conf, payload)


def adapt_object_modal_json(
    body: Dict[str, Any],
    create_detection_event: Callable[[float, Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    """OWL-ViT /analysis/detect_objects shape: id, timestamp, probability, evidence."""
    if not isinstance(body.get("evidence"), str):
        raise ValueError("Modal object response missing evidence string")

    prob = _parse_percent_or_fraction(body.get("probability"))
    evidence = body["evidence"].strip()
    objects: list[str] = []
    if "Detected:" in evidence:
        rest = evidence.split("Detected:", 1)[1].strip()
        if rest and "no restricted" not in evidence.lower():
            objects = [x.strip() for x in rest.split(",") if x.strip()]

    suspicious = len(objects) > 0
    payload: Dict[str, Any] = {
        "objects": objects,
        "count": len(objects),
        "suspicious": suspicious,
    }
    return create_detection_event(prob, payload)
