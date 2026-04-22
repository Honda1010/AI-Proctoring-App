import httpx
import datetime
import base64
import binascii
from typing import Dict, Any, Tuple

class ModalClient:
    """Async client for calling Modal web endpoints."""

    def __init__(self, endpoint_url: str, token: str, timeout: float = 30.0):
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
            data = {"session_id": "test_session_001"}
            #data = {"session_id": session_id}
            files = {"frame": ("frame.jpg", image_bytes, mime)}
            return await client.post(self.endpoint_url, data=data, files=files)

        payload = {
            "token": self.token,
            "sessionId": session_id,
            "frame": frame,
        }
        return await client.post(self.endpoint_url, json=payload)

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
