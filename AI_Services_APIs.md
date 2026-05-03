# Modal API Documentation

All endpoints are hosted on Modal and expect a `POST` request. Most endpoints use `multipart/form-data` for image uploads.

---

## Endpoints

### 1. Object Detection

| Field | Value |
|-------|-------|
| **Endpoint** | `/analysis/object-frame` |
| **Method** | `POST` |
| **Content-Type** | `multipart/form-data` |

**Parameters:**

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `file` | ✅ | binary | The image frame to analyze for prohibited objects (e.g., cell phones) |

**Response:**
```json
{
  "probability": 0.85,
  "evidence": "Detected: cell phone"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `probability` | float | Confidence score (`0.0` to `1.0`) |
| `evidence` | string | Description of detected objects. If prefixed with `"Detected:"`, the bridge extracts the objects |

---

### 2. Face Detection (Presence Check)

| Field | Value |
|-------|-------|
| **Endpoint** | `/analysis/face-detection-file` |
| **Method** | `POST` |
| **Content-Type** | `multipart/form-data` |

**Parameters:**

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `session_id` | ✅ | string | Unique ID for the proctoring session |
| `frame` | ✅ | binary | The image frame to check for a face |

**Response:**
```json
{
  "session_id": "test_session_001",
  "timestamp": "2026-04-25T02:12:39.498784",
  "num_faces": 1,
  "evidence": "One face detected"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | The session ID associated with this request |
| `timestamp` | string | ISO 8601 timestamp of when the detection occurred |
| `num_faces` | int | Number of faces detected in the frame |
| `evidence` | string | Human-readable description of the detection result |

---

### 3. Face Verification (Recognition)

| Field | Value |
|-------|-------|
| **Endpoint** | `/analysis/verify-file` |
| **Method** | `POST` |
| **Content-Type** | `multipart/form-data` |

**Parameters:**

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `session_id` | ✅ | string | Used to retrieve the previously enrolled reference face |
| `frame` | ✅ | binary | The image frame to verify against the reference |

**Response:**
```json
{
  "face_recognition": {
    "flag": false,
    "result": "No Cheating",
    "evidence": "Authorised person verified",
    "probability": 0.98,
    "num_faces": 1
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `flag` | boolean | `true` indicates suspicious activity (mismatch, spoof, or no face) |
| `result` | string | Human-readable status (e.g., `"No Cheating"`) |
| `evidence` | string | Explanation of the result |
| `probability` | float | Confidence score (`0.0` to `1.0`) |
| `num_faces` | int | Number of faces detected in the frame |

---

### 4. Face Enrollment

| Field | Value |
|-------|-------|
| **Endpoint** | `/analysis/enroll-file` |
| **Method** | `POST` |
| **Content-Type** | `multipart/form-data` |

**Parameters:**

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `session_id` | ✅ | string | The ID to associate this reference face with |
| `references` | ✅ | binary | The reference image to store |

**Response:**
```json
{
  "success": true,
  "session_id": "test_session_001",
  "num_images": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if enrollment completed successfully |
| `session_id` | string | The session ID the reference face was enrolled under |
| `num_images` | int | Number of reference images stored for this session |

---

### 5. Unenrollment

| Field | Value |
|-------|-------|
| **Endpoint** | `/analysis/unenroll` |
| **Method** | `POST` |
| **Content-Type** | `application/x-www-form-urlencoded` |

**Parameters:**

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `session_id` | ✅ | string | The ID of the session to clear |

**Response:**
```json
{
  "success": true,
  "session_id": "test_session_001"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if the session was successfully cleared |
| `session_id` | string | The session ID that was unenrolled |

---

## Shared Error Structure

If a request fails on the Modal side, the bridge returns:

```json
{
  "ok": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable reason"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Always `false` on error |
| `error.code` | string | Machine-readable error code |
| `error.message` | string | Human-readable explanation |