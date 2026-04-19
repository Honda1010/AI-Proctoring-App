import json
import sys
import os
import asyncio
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError

from config import load_config, ConfigError
from eye_gaze import EyeGazeService
from object_detection import ObjectDetectionService
from face_recognition import FaceRecognitionService
from speech_detection import SpeechDetectionService

# Phase 7: Local services
from services.eye_gaze_local import LocalEyeGazeService
from services.speech_local import LocalSpeechDetectionService

# Phase 8: Proctoring Orchestration
from orchestrator import ProctoringOrchestrator

class AIRouter:
    def __init__(self, config_path: str, schema_path: str):
        self.config_path = config_path
        self.schema_path = schema_path
        self.config = None
        self.schema = None
        self.orchestrator = None
        self.services = {}
        self.service_classes = {
            "eye-gaze": LocalEyeGazeService,
            "object-detection": ObjectDetectionService,
            "face-recognition": FaceRecognitionService,
            "speech-detection": LocalSpeechDetectionService
        }
        self.loop = None

    def load_configuration(self):
        try:
            self.config = load_config(self.config_path)
        except ConfigError as e:
            self.send_error(None, -32000, f"Config error: {e.message}")
            sys.exit(1)

    def load_schema(self):
        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                self.schema = json.load(f)
        except Exception as e:
            self.send_error(None, -32000, f"Schema load error: {str(e)}")
            sys.exit(1)

    async def run(self):
        self.load_configuration()
        self.load_schema()
        self.loop = asyncio.get_running_loop()
        
        # Initialize Orchestrator
        self.orchestrator = ProctoringOrchestrator(
            vars(self.config), 
            self.emit_notification_from_orchestrator
        )

        while True:
            line = await self.loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            try:
                request = json.loads(line)
                asyncio.create_task(self.handle_request(request))
            except json.JSONDecodeError:
                self.send_error(None, -32700, "Parse error")
            except Exception as e:
                self.send_error(None, -32603, f"Internal error: {str(e)}")

    def emit_notification_from_orchestrator(self, notification: Dict[str, Any]):
        """Callback for orchestrator to send alerts and risk scores to stdout."""
        # Risk scores and alerts are already formatted as parameters
        msg_type = notification.get("type", "notification")
        self.send_notification(msg_type, notification)

    def thread_safe_emit(self, event: Dict[str, Any]):
        """
        Callback passed to local services. 
        Background threads call this to emit events to the async loop.
        """
        if "method" in event and event["method"] == "serviceError":
            # Direct notification (error)
            self.loop.call_soon_threadsafe(
                self.send_notification, event["method"], event["params"]
            )
        else:
            # Detection event - pipe through orchestrator
            def process_and_send():
                try:
                    validate(instance=event, schema=self.schema)
                    # Router sends raw detection immediately
                    self.send_notification("detection", event)
                    # AND sends to orchestrator for fusion/logging
                    asyncio.create_task(self.orchestrator.on_detection_event(event))
                except ValidationError as e:
                    self.send_notification("serviceError", {
                        "service": event.get("service", "unknown"),
                        "code": "CONTRACT_VIOLATION",
                        "message": f"Background event failed contract validation: {e.message}"
                    })
            
            self.loop.call_soon_threadsafe(process_and_send)

    async def handle_request(self, request: Dict[str, Any]):
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "startService":
            await self.handle_start_service(request_id, params)
        elif method == "stopService":
            await self.handle_stop_service(request_id, params)
        elif method == "queryStatus":
            self.handle_query_status(request_id, params)
        elif method == "predict":
            await self.handle_predict(request_id, params)
        elif method == "mockDetection": # Helper for testing/wiring
            await self.handle_mock_detection(request_id, params)
        else:
            self.send_error(request_id, -32601, "Method not found")

    async def handle_predict(self, request_id: Any, params: Dict[str, Any]):
        service_name = params.get("service")
        frame = params.get("frame")
        
        if service_name not in self.services:
            self.send_error(request_id, -32602, f"Service not running: {service_name}")
            return
            
        if not frame:
            self.send_error(request_id, -32602, "Missing frame data")
            return

        try:
            service = self.services[service_name]
            # All services should now implement an async predict method
            event = await service.predict(frame)
            
            # Validate event against schema
            try:
                validate(instance=event, schema=self.schema)
                self.send_notification("detection", event)
                self.send_result(request_id, {"status": "success"})
                # Pipe to orchestrator
                await self.orchestrator.on_detection_event(event)
            except ValidationError as e:
                self.send_notification("serviceError", {
                    "service": service_name,
                    "code": "CONTRACT_VIOLATION",
                    "message": f"Detection event failed contract validation: {e.message}"
                })
                self.send_error(request_id, -32001, "Contract violation")
        except Exception as e:
            self.send_error(request_id, -32603, f"Internal error during prediction: {str(e)}")


    async def handle_start_service(self, request_id: Any, params: Dict[str, Any]):
        service_name = params.get("service")
        session_id = params.get("sessionId", "default-session")
        
        if service_name not in self.service_classes:
            self.send_error(request_id, -32602, f"Invalid service: {service_name}")
            return

        if service_name in self.services:
            self.send_result(request_id, {"status": "already_running", "service": service_name})
            return

        service_cls = self.service_classes[service_name]
        
        # Local services require the emitter callback
        if service_name in ["eye-gaze", "speech-detection"]:
            service = service_cls(session_id, vars(self.config), self.thread_safe_emit)
        else:
            service = service_cls(session_id, vars(self.config))
            
        await service.start()
        self.services[service_name] = service
        self.send_result(request_id, {"status": "started", "service": service_name})

    async def handle_stop_service(self, request_id: Any, params: Dict[str, Any]):
        service_name = params.get("service")
        if service_name in self.services:
            await self.services[service_name].stop()
            del self.services[service_name]
            self.send_result(request_id, {"status": "stopped", "service": service_name})
        else:
            self.send_error(request_id, -32602, f"Service not running: {service_name}")

    def handle_query_status(self, request_id: Any, params: Dict[str, Any]):
        service_name = params.get("service")
        if service_name:
            status = "running" if service_name in self.services else "stopped"
            self.send_result(request_id, {"service": service_name, "status": status})
        else:
            statuses = {name: ("running" if name in self.services else "stopped") for name in self.service_classes}
            self.send_result(request_id, statuses)

    async def handle_mock_detection(self, request_id: Any, params: Dict[str, Any]):
        service_name = params.get("service")
        if service_name in self.services:
            # We assume get_mock_event might be async in the future
            if asyncio.iscoroutinefunction(self.services[service_name].get_mock_event):
                event = await self.services[service_name].get_mock_event()
            else:
                event = self.services[service_name].get_mock_event()
                
            # Validate event against schema
            try:
                validate(instance=event, schema=self.schema)
                self.send_notification("detection", event)
                self.send_result(request_id, {"status": "mock_event_sent"})
            except ValidationError as e:
                self.send_notification("serviceError", {
                    "service": service_name,
                    "code": "CONTRACT_VIOLATION",
                    "message": f"Detection event failed contract validation: {e.message}"
                })
                self.send_error(request_id, -32001, "Contract violation")
        else:
            self.send_error(request_id, -32602, f"Service not running: {service_name}")

    def send_result(self, request_id: Any, result: Any):
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
        self.write_stdout(response)

    def send_error(self, request_id: Any, code: int, message: str):
        response = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": request_id
        }
        self.write_stdout(response)

    def send_notification(self, method: str, params: Any):
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self.write_stdout(notification)

    def write_stdout(self, data: Dict[str, Any]):
        sys.stdout.write(json.dumps(data) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    # Resolve paths
    base_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.environ.get("LUMINA_CONFIG_PATH", os.path.join(base_dir, "config.json"))
    schema_path = os.path.join(base_dir, "specs", "ai-service-contract.json")
    
    router = AIRouter(config_path, schema_path)
    asyncio.run(router.run())


