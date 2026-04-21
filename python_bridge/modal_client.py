import httpx
import datetime
import base64
import binascii
from typing import Dict, Any, Tuple, List

class ModalClient:
    """Async client for calling Modal web endpoints."""

    def __init__(self, endpoint_url: str, token: str, timeout: float = 10.0):
        self.endpoint_url = endpoint_url
        self.token = token
        self.timeout = timeout

    async def predict(self, service_name: str, session_id: str, frame: str) -> Dict[str, Any]:
        """
        Sends a frame to the Modal endpoint and returns a DetectionEvent.
        Handles cold starts and timeouts.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._send_request(client, session_id, frame)
                
                if response.status_code == 200:
                    try:
                        raw_body = response.json()
                    except ValueError:
                        return self._create_error_event(
                            service_name,
                            session_id,
                            "BRIDGE_ERROR",
                            "Modal returned a non-JSON response.",
                        )

                    return self._normalize_event(service_name, session_id, raw_body)
                elif response.status_code == 503:
                    return self._create_error_event(
                        service_name, session_id, "SERVICE_UNAVAILABLE", 
                        "Modal container is warming up. Retrying..."
                    )
                else:
                    return self._create_error_event(
                        service_name, session_id, "BRIDGE_ERROR", 
                        f"Modal returned unexpected status: {response.status_code}"
                    )
        except httpx.TimeoutException:
            return self._create_error_event(
                service_name, session_id, "TIMEOUT", 
                "Request to Modal timed out (cold start threshold exceeded)."
            )
        except Exception as e:
            return self._create_error_event(
                service_name, session_id, "UNKNOWN_ERROR", str(e)
            )

    async def _send_request(
        self,
        client: httpx.AsyncClient,
        session_id: str,
        frame: str,
    ) -> httpx.Response:
        endpoint_lower = self.endpoint_url.lower()

        if "/analysis/detect_objects" in endpoint_lower:
            image_bytes, mime = self._decode_frame_to_image(frame)
            files = {"file": ("frame.jpg", image_bytes, mime)}
            return await client.post(self.endpoint_url, files=files)

        if "/analysis/verify-file" in endpoint_lower:
            image_bytes, mime = self._decode_frame_to_image(frame)
            data = {"session_id": session_id}
            files = {"frame": ("frame.jpg", image_bytes, mime)}
            return await client.post(self.endpoint_url, data=data, files=files)

        payload = {
            "token": self.token,
            "sessionId": session_id,
            "frame": frame,
        }
        return await client.post(self.endpoint_url, json=payload)

    def _normalize_event(self, service_name: str, session_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize endpoint-specific responses into DetectionEvent schema."""
        if not isinstance(body, dict):
            raise ValueError("Modal response must be a JSON object")

        endpoint_lower = self.endpoint_url.lower()

        if "/analysis/detect_objects" in endpoint_lower:
            return self._normalize_object_detection_response(service_name, session_id, body)

        if "/analysis/verify-file" in endpoint_lower:
            return self._normalize_face_verify_response(service_name, session_id, body)

        required_keys = {"service", "timestamp", "confidence", "sessionId", "payload"}
        if required_keys.issubset(body.keys()):
            return body

        # Best-effort fallback for legacy endpoints returning flat flag/evidence/probability.
        return {
            "service": service_name,
            "timestamp": self._iso_utc_now(),
            "confidence": self._coerce_probability(body.get("probability"), default=0.0),
            "sessionId": session_id,
            "payload": {
                "status": "ok",
                "raw": body,
            },
        }

    def _normalize_object_detection_response(
        self,
        service_name: str,
        session_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        detections = body.get("detections") if isinstance(body.get("detections"), list) else []

        objects: List[str] = []
        max_det_conf = 0.0
        for det in detections:
            if not isinstance(det, dict):
                continue
            label = det.get("label")
            if isinstance(label, str) and label.strip():
                objects.append(label.strip())
            det_conf = self._coerce_probability(det.get("confidence"), default=0.0)
            if det_conf > max_det_conf:
                max_det_conf = det_conf

        evidence = body.get("evidence") if isinstance(body.get("evidence"), str) else ""
        if not objects and evidence.lower().startswith("detected:"):
            inferred = evidence.split(":", 1)[1]
            objects = [item.strip() for item in inferred.split(",") if item.strip()]

        suspicious = bool(body.get("flag")) if "flag" in body else bool(objects)
        confidence = max(
            self._coerce_probability(body.get("probability"), default=0.0),
            max_det_conf,
        )

        return {
            "service": service_name,
            "timestamp": self._iso_utc_now(),
            "confidence": confidence,
            "sessionId": session_id,
            "payload": {
                "suspicious": suspicious,
                "objects": objects,
                "count": len(objects),
                "evidence": evidence,
                "detections": detections,
            },
        }

    def _normalize_face_verify_response(
        self,
        service_name: str,
        session_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = body.get("face_recognition") if isinstance(body.get("face_recognition"), dict) else body

        flag = bool(payload.get("flag"))
        num_faces = payload.get("num_faces", 1)
        if not isinstance(num_faces, int):
            num_faces = 1 if not flag else 0

        confidence = self._coerce_probability(payload.get("probability"), default=0.0)

        return {
            "service": service_name,
            "timestamp": self._iso_utc_now(),
            "confidence": confidence,
            "sessionId": session_id,
            "payload": {
                "is_matched": not flag,
                "faces_count": num_faces,
                "evidence": payload.get("evidence", ""),
                "result": payload.get("result", ""),
                "match_similarity": payload.get("match_similarity"),
                "liveness_score": payload.get("liveness_score"),
                "quality": payload.get("quality"),
                "active_challenge_required": bool(payload.get("active_challenge_required", False)),
                "raw": payload,
            },
        }

    def _coerce_probability(self, value: Any, default: float = 0.0) -> float:
        """Convert numeric and percent-like values to 0..1 float."""
        parsed = default
        if isinstance(value, bool):
            parsed = default
        elif isinstance(value, (int, float)):
            parsed = float(value)
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.endswith("%"):
                stripped = stripped[:-1].strip()
                try:
                    parsed = float(stripped) / 100.0
                except ValueError:
                    parsed = default
            else:
                try:
                    parsed = float(stripped)
                except ValueError:
                    parsed = default

        if parsed > 1.0 and parsed <= 100.0:
            parsed = parsed / 100.0

        if parsed < 0.0:
            return 0.0
        if parsed > 1.0:
            return 1.0
        return parsed

    def _iso_utc_now(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _decode_frame_to_image(self, frame: str) -> Tuple[bytes, str]:
        """Decode a base64 frame (or data URL) into image bytes for multipart upload."""
        if frame == "WARMUP":
            # 1x1 JPEG used for endpoint warmup on multipart-only routes.
            return (
                base64.b64decode(
                    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBUQEA8QFRUVFRUVFRUVFRUVFRUXFxUWFhUV"
                    "FRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGhAQGi0fHyUtLS0tLS0tLS0tLS0t"
                    "LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAAEAAQMBIgACEQEDEQH/xAAXAAEBAQEA"
                    "AAAAAAAAAAAAAAABAgME/8QAFhEBAQEAAAAAAAAAAAAAAAAAAAER/8QAFQEBAQAAAAAAAAAAAAAAAAAA"
                    "AgP/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCjAAH/2Q=="
                ),
                "image/jpeg",
            )

        frame_data = frame
        mime = "image/jpeg"

        if frame.startswith("data:") and ";base64," in frame:
            header, frame_data = frame.split(",", 1)
            mime = header[5:].split(";", 1)[0] or "image/jpeg"

        try:
            return base64.b64decode(frame_data, validate=True), mime
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Frame must be a valid base64 image payload") from exc

    def _create_error_event(self, service: str, session_id: str, code: str, message: str) -> Dict[str, Any]:
        """Creates a normalized error detection event."""
        return {
            "service": service,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "confidence": 0.0,
            "sessionId": session_id,
            "payload": {
                "status": "error",
                "code": code,
                "message": message
            }
        }
