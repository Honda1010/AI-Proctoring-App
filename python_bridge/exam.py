"""
exam.py — Exam access blueprint for Lumina AI Python bridge.

Exposes one endpoint:
    POST /exam-access
        Body:    {"quizCode": str, "token": str}
        Success: ExamSession fields from the LMS (200 OK).
        Failure: BridgeExamError {"code": str, "message": str} (4xx / 5xx).

Security rules (constitution.md — Security by Default):
    - The access token is NEVER logged, printed, or included in any
      error response body or exception message.
    - Raw LMS error messages are NEVER forwarded to the caller.
      All error text is sanitised through map_lms_exam_error().
    - The BASE_URL used for LMS calls is read from the Flask app config,
      which is populated from the validated config.json (https:// enforced).
"""

import requests
from flask import Blueprint, jsonify, request, current_app
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

exam_bp = Blueprint("exam", __name__)


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------

def map_lms_exam_error(status_code: int):
    """
    Map an LMS HTTP status code to a typed, sanitised BridgeExamError tuple.

    The pre-defined safe display strings are returned — raw LMS error text
    is never forwarded.

    Args:
        status_code: HTTP status code from the LMS response.

    Returns:
        Tuple of (response_dict, http_status_code) for use with jsonify().
    """
    if status_code == 404:
        return (
            {
                "code": "EXAM_NOT_FOUND",
                "message": "Exam code not found. Please check the code and try again.",
            },
            404,
        )
    if status_code == 409:
        return (
            {
                "code": "ALREADY_ATTEMPTED",
                "message": "You have already attempted this exam.",
            },
            409,
        )
    if status_code == 401:
        return (
            {
                "code": "UNAUTHORIZED",
                "message": "Your session has expired. Please log in again.",
            },
            401,
        )
    return (
        {
            "code": "BRIDGE_ERROR",
            "message": "Unable to reach the server. Please check your connection and try again.",
        },
        503,
    )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@exam_bp.route("/exam-access", methods=["POST"])
def exam_access():
    """
    Start an exam attempt by validating the exam code against the LMS.

    Reads quizCode and token from the request body. The token is used
    exclusively as the Authorization header for the outbound LMS GET call —
    it is never logged, stored by this blueprint, or returned in any response.
    """
    data = request.get_json(silent=True) or {}
    quiz_code = (data.get("quizCode") or "").strip()
    token = data.get("token") or ""

    if not quiz_code or not token:
        return (
            jsonify(
                {
                    "code": "BRIDGE_ERROR",
                    "message": "Unable to reach the server. Please check your connection and try again.",
                }
            ),
            400,
        )

    base_url = current_app.config["BASE_URL"]
    lms_url = f"{base_url}/api/QuizAttempts/attempt/{quiz_code}"

    try:
        response = requests.get(
            lms_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
            verify=False,
        )
    except requests.exceptions.RequestException:
        return (
            jsonify(
                {
                    "code": "BRIDGE_ERROR",
                    "message": "Unable to reach the server. Please check your connection and try again.",
                }
            ),
            503,
        )

    if response.status_code == 200:
        return jsonify(response.json()), 200

    error_body, error_status = map_lms_exam_error(response.status_code)
    return jsonify(error_body), error_status
