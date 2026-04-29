import httpx
import datetime
import base64
import binascii
from typing import Dict, Any, Tuple

class ModalClient:
    """Async client for calling Modal web endpoints."""

    def __init__(self, endpoint_url: str, token: str, timeout: float = 30.0,
                 enroll_url: str = "", unenroll_url: str = "", face_detect_url: str = ""):
        self.endpoint_url = endpoint_url
        self.token = token
        self.timeout = timeout
        self._enroll_url = enroll_url or endpoint_url
        self._unenroll_url = unenroll_url or endpoint_url
        self._face_detect_url = face_detect_url or endpoint_url
    
    async def predict(self, service_name: str, session_id: str, frame: str) -> Dict[str, Any]:
        """
        Sends a frame to the Modal endpoint and returns a DetectionEvent.
        Handles cold starts and timeouts.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._send_request(client, service_name, session_id, frame)
                
                if response.status_code == 200:
                    return response.json()
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
        service_name: str,
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
            # data = {"session_id": "test_session_001"}
            data = {"session_id": session_id}
            files = {"frame": ("frame.jpg", image_bytes, mime)}
            return await client.post(self.endpoint_url, data=data, files=files)

        # No known endpoint pattern matched — fail loudly rather than sending a
        # malformed payload that no active Modal route accepts.
        raise ValueError(
            f"No matching request format for endpoint: {self.endpoint_url!r}. "
            "Verify that config endpoint_url contains a recognised Modal route "
            "(/analysis/verify-file or /analysis/detect_objects)."
        )

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

    async def face_detect(self, session_id: str, frame: str) -> Dict[str, Any]:
        """
        Check for a face in a single frame via /analysis/face-detection-file.
        Returns the raw Modal JSON response.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                image_bytes, mime = self._decode_frame_to_image(frame)
                data = {"session_id": session_id}
                files = {"frame": ("frame.jpg", image_bytes, mime)}
                response = await client.post(self._face_detect_url, data=data, files=files)
                if response.status_code == 200:
                    return response.json()
                # Extract the human-readable detail from 422 bodies (e.g. "No face detected").
                try:
                    detail = response.json().get("detail", "")
                except Exception:
                    detail = ""
                return {"ok": False, "error": {"code": "FACE_DETECT_ERROR",
                        "message": detail or f"Modal face-detect returned {response.status_code}"}}
        except httpx.TimeoutException:
            return {"ok": False, "error": {"code": "TIMEOUT", "message": "Face-detect request timed out."}}
        except Exception as e:
            return {"ok": False, "error": {"code": "UNKNOWN_ERROR", "message": str(e)}}

    async def enroll(self, session_id: str, frame: str) -> Dict[str, Any]:
        """
        Enroll a reference image via /analysis/enroll-file.
        'frame' is a base64 data URL or raw base64 JPEG.
        Returns the raw Modal JSON response.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                image_bytes, mime = self._decode_frame_to_image(frame)
                data = {"session_id": session_id}
                files = {"references": ("reference.jpg", image_bytes, mime)}
                response = await client.post(self._enroll_url, data=data, files=files)
                if response.status_code == 200:
                    return response.json()
                # Extract the human-readable detail from 422 bodies
                # (e.g. "No face detected in reference image 0", "Multiple faces in reference image 0").
                try:
                    detail = response.json().get("detail", "")
                except Exception:
                    detail = ""
                return {"ok": False, "error": {"code": "ENROLLMENT_FAILED",
                        "message": detail or f"Modal enroll returned {response.status_code}"}}
        except httpx.TimeoutException:
            return {"ok": False, "error": {"code": "TIMEOUT", "message": "Enrollment request timed out."}}
        except Exception as e:
            return {"ok": False, "error": {"code": "UNKNOWN_ERROR", "message": str(e)}}

    async def unenroll(self, session_id: str) -> None:
        """
        Remove the stored embedding via /analysis/unenroll (fire-and-forget).
        Errors are swallowed — callers must not await a meaningful result.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                data = {"session_id": session_id}
                await client.post(self._unenroll_url, data=data)
        except Exception:
            pass  # fire-and-forget — swallow all errors

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
