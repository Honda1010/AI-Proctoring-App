Enroll File
Endpoint: POST /analysis/enroll-file

Description: The multipart/form-data variant of the enrollment process, used for testing or administrative uploads to register an authorized user's face.

Functionality: It accepts a session_id and one or more image files. The system processes these to compute an averaged ArcFace embedding, which is cached in-memory as the "ground truth" for identity verification during the exam.

Requirements: session_id (string) and references (one or more image files).

Unenroll
Endpoint: POST /analysis/unenroll

Description: A session management utility used to clear session-specific biometric data.

Functionality: Removes the cached reference face embedding for the provided session_id. This should be called after an exam ends to free memory and ensure data privacy.

Requirements: session_id (string) provided via form-data.

Verify File
Endpoint: POST /analysis/verify-file

Description: A testing-focused multipart variant of the live verification endpoint used to confirm the identity of the person taking the exam.

Functionality: Compares a live frame against the enrolled embedding. It simultaneously runs Face Anti-Spoofing (FAS) to ensure the subject is a real person and not a digital or physical spoof (like a photo or tablet).

Requirements: Must be called after enrollment. Requires session_id (string) and frame (image file).

Detect Objects (OWL-ViT)
Endpoint: POST /analysis/detect_objects

Description: High-accuracy prohibited object detection utilizing the OWL-ViT (Vision Transformer) model.

Functionality: Analyzes an image to identify proctoring violations (e.g., phones or books). It returns labels, confidence scores, and bounding boxes for any detected objects that may compromise exam integrity.

Requirements: Image file (multipart/form-data).

Face Detection File
Endpoint: POST /analysis/face-detection-file

Description: A diagnostic endpoint used to verify the system's ability to locate a face within a specific session context.

Functionality: This runs the detection phase of the pipeline. It ensures that the current environment (lighting, positioning, and image quality) allows the AI to successfully isolate a face before proceeding to more intensive recognition or anti-spoofing checks.

Requirements: session_id (string) and frame (image file).