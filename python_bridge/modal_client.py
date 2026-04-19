import httpx
import json
import datetime
from typing import Dict, Any, Optional

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
        payload = {
            "token": self.token,
            "sessionId": session_id,
            "frame": frame
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.endpoint_url, json=payload)
                
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
