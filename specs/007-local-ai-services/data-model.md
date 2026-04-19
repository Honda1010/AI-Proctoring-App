# Data Model: Local AI Services

## 1. Local Configuration (config.json)
Additional configuration fields required for local hardware access and model parameters.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `services.eye-gaze.fps` | integer | 5 | Target frames per second for capture. |
| `services.eye-gaze.camera_index` | integer | 0 | System index for the webcam. |
| `services.speech-detection.chunk_size` | integer | 1024 | Samples per audio buffer. |
| `services.speech-detection.threshold` | float | 0.05 | Energy threshold for speech detection. |
| `services.speech-detection.sample_rate` | integer | 16000 | Audio sampling rate in Hz. |

## 2. DetectionEvent Payloads
Service-specific data nested in the `payload` field.

### Eye Gaze
- `gaze_x`: float (0.0 to 1.0) - Horizontal coordinate.
- `gaze_y`: float (0.0 to 1.0) - Vertical coordinate.
- `status`: string (`"on-screen"`, `"away"`, `"blink"`)

### Speech Detection
- `is_speech_detected`: boolean
- `db_level`: float - Relative volume in decibels.
- `language`: string (optional, e.g., `"en-US"`)

## 3. Local Service State
Internal state maintained within the threaded service classes.
- `is_running`: boolean - Thread lifecycle control.
- `camera_handle`: object - OpenCV VideoCapture instance.
- `audio_stream`: object - PyAudio stream instance.
