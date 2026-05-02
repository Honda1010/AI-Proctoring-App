"""
Overall Risk Estimation — Post-Session Scoring Backend

Reads the JSONL session logs produced by the ProctoringOrchestrator and
computes either:
  (a) A single normalised risk score for the whole session  (default mode)
  (b) A per-question anomaly breakdown grouped by AI service  (--by-question)

Mode (a) — whole-session pipeline:
  1. Parse every DetectionEvent and AlertEvent in the session log.
  2. Map the 5 AI services → 4 high-level behaviour categories.
  3. Count raw anomaly occurrences per category.
  4. Normalise to (0, 1) via min-max normalisation.
  5. Compute Total Risk = Σ (weight_i × normalised_i)
  6. Write a structured JSON report.

Mode (b) — per-question pipeline:
  1. Parse every DetectionEvent in the session log.
  2. Pre-fill all N questions (1 … N) with zero counts for every AI service.
  3. For each suspicious event, read its `questionId` field and increment
     the matching service counter for that question.
     Events without a `questionId` go into an `unassigned` bucket.
  4. Write a structured JSON report keyed by `question_1` … `question_N`.

Usage:
  # Whole-session risk score
  python risk_estimator.py <session_log.jsonl> [--output <path.json>]
      [--student-id <id>] [--exam-id <id>]
      [--wf <float>] [--wh <float>] [--wc <float>] [--wb <float>]

  # Per-question breakdown
  python risk_estimator.py <session_log.jsonl> --by-question --total-questions <N>
      [--output <path.json>] [--student-id <id>] [--exam-id <id>]

If --output is omitted the report is written next to the input file as:
  <session_id>_risk_report.json          (whole-session)
  <session_id>_question_report.json      (per-question)
"""

import json
import os
import sys
import argparse
import datetime
from typing import Dict, Any, List, Optional


# ─── Behaviour categories and their mapping from AI services ────────────
CATEGORY_FACE   = "face_absence_mismatch"    # face-detection + face-recognition
CATEGORY_MOVE   = "suspicious_movement"      # eye-gaze
CATEGORY_CONV   = "conversation_noise"       # speech-detection
CATEGORY_OBJ    = "forbidden_objects"        # object-detection

ALL_CATEGORIES = [CATEGORY_FACE, CATEGORY_MOVE, CATEGORY_CONV, CATEGORY_OBJ]

# ─── Per-service keys used by the question-level report ─────────────────
# Ordered to match the target output structure.
SERVICE_KEYS = [
    "face_detection",
    "face_recognition",
    "eye_gaze",
    "speech_detection",
    "object_detection",
]

# Mapping from raw service names in the JSONL to the SERVICE_KEYS above.
_SERVICE_NAME_TO_KEY: Dict[str, str] = {
    "face-detection":   "face_detection",
    "face-recognition": "face_recognition",
    "eye-gaze":         "eye_gaze",
    "speech-detection": "speech_detection",
    "object-detection": "object_detection",
}


# ─── Event classification ──────────────────────────────────────────────

def _is_suspicious_event(event: Dict[str, Any]) -> Optional[str]:
    """Return the behaviour category if the event is suspicious, else None.

    The rules intentionally mirror ProctoringOrchestrator._update_risk_score
    so that the post-session report agrees with the real-time score.
    """
    service = event.get("service")
    payload = event.get("payload", {})

    # --- Face Detection: missing face ---
    if service == "face-detection":
        if not payload.get("face_detected", True):
            return CATEGORY_FACE

    # --- Face Recognition: impersonation / spoof ---
    elif service == "face-recognition":
        if payload.get("is_spoof"):
            return CATEGORY_FACE
        if not payload.get("is_matched", True) and payload.get("recognition_ran", False):
            return CATEGORY_FACE

    # --- Eye Gaze: looking away ---
    elif service == "eye-gaze":
        if payload.get("status") == "away":
            return CATEGORY_MOVE

    # --- Speech Detection: talking ---
    elif service == "speech-detection":
        if len(payload.get("new_violations", [])) > 0:
            return CATEGORY_CONV

    # --- Object Detection: prohibited object ---
    elif service == "object-detection":
        if payload.get("suspicious"):
            return CATEGORY_OBJ

    return None


def _is_alert_suspicious(event: Dict[str, Any]) -> Optional[str]:
    """Map orchestrator-generated AlertEvents to a category."""
    code = event.get("code", "")
    code_map = {
        "NO_FACE_DETECTED":         CATEGORY_FACE,
        "UNAUTHORIZED_PERSON":      CATEGORY_FACE,
        "SPOOF_DETECTED":           CATEGORY_FACE,
        "GAZE_OFF_SCREEN":          CATEGORY_MOVE,
        "SPEECH_DETECTED":          CATEGORY_CONV,
        "SPEECH_CHEATING_FLAGGED":  CATEGORY_CONV,
        "UNAUTHORIZED_OBJECT":      CATEGORY_OBJ,
    }
    return code_map.get(code)


def _suspicious_service_key(event: Dict[str, Any]) -> Optional[str]:
    """Return the SERVICE_KEY string if this DetectionEvent is suspicious.

    Used by the per-question analyser, which tracks counts at the individual
    AI-service level (not the 4-category level used by the session scorer).
    """
    service = event.get("service")
    key = _SERVICE_NAME_TO_KEY.get(service or "")
    if key is None:
        return None

    payload = event.get("payload", {})

    if service == "face-detection":
        return key if not payload.get("face_detected", True) else None

    if service == "face-recognition":
        if payload.get("is_spoof") or (
            not payload.get("is_matched", True) and payload.get("recognition_ran", False)
        ):
            return key
        return None

    if service == "eye-gaze":
        return key if payload.get("status") == "away" else None

    if service == "speech-detection":
        return key if len(payload.get("new_violations", [])) > 0 else None

    if service == "object-detection":
        return key if payload.get("suspicious") else None

    return None


# ─── Core logic ─────────────────────────────────────────────────────────

def count_anomalies(log_path: str) -> Dict[str, int]:
    """Read a JSONL session log and return raw anomaly counts per category."""
    counts: Dict[str, int] = {cat: 0 for cat in ALL_CATEGORIES}

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")

            # DetectionEvents (from AI services) have a "service" key but no "type"
            if "service" in event and event_type is None:
                cat = _is_suspicious_event(event)
                if cat:
                    counts[cat] += 1

            # AlertEvents generated by the orchestrator
            elif event_type == "alert":
                cat = _is_alert_suspicious(event)
                if cat:
                    counts[cat] += 1

    return counts


# ─── Per-question anomaly counting ──────────────────────────────────────

def _empty_service_counts() -> Dict[str, int]:
    """Return a fresh zero-initialised dict for all 5 AI services."""
    return {key: 0 for key in SERVICE_KEYS}


def count_anomalies_by_question(
    events: List[Dict[str, Any]],
    total_number_of_questions: int,
) -> Dict[str, Any]:
    """Group suspicious anomaly counts from raw event objects by question.

    Args:
        events: A list of DetectionEvent dicts (already parsed from JSONL).
            Each event may optionally carry a ``questionId`` field (int or str)
            that identifies which question was active when the event occurred.
            Events without ``questionId`` are tallied under ``"unassigned"``.
        total_number_of_questions: The total number of questions in the exam.
            All questions from 1 up to this value will appear in the output,
            even if no anomalies were recorded for them.

    Returns:
        A dict with the structure::

            {
                "total_questions": N,
                "questions": {
                    "question_1":  {"face_detection": 0, ...},
                    ...
                    "question_N":  {"face_detection": 0, ...},
                    # Only present when at least one event lacked a questionId:
                    "unassigned":  {"face_detection": 0, ...},
                }
            }
    """
    if total_number_of_questions < 1:
        raise ValueError(
            f"total_number_of_questions must be ≥ 1, got {total_number_of_questions}."
        )

    # Step 1 — Pre-fill every question with zeroes.
    questions: Dict[str, Dict[str, int]] = {
        f"question_{q}": _empty_service_counts()
        for q in range(1, total_number_of_questions + 1)
    }

    # Separate bucket for events that carry no questionId.
    unassigned: Dict[str, int] = _empty_service_counts()
    has_unassigned = False

    # Step 2 — Iterate events and increment the appropriate counter.
    for event in events:
        # Only DetectionEvents (those without a top-level "type" field) are
        # processed; riskScore / alert / lifecycle events are skipped.
        if event.get("type") is not None:
            continue
        if "service" not in event:
            continue

        service_key = _suspicious_service_key(event)
        if service_key is None:
            # Event is not suspicious — nothing to count.
            continue

        raw_qid = event.get("questionId")

        if raw_qid is None:
            # No question context attached — tally in the unassigned bucket.
            unassigned[service_key] += 1
            has_unassigned = True
        else:
            # Normalise: accept both int and string questionId values.
            try:
                q_num = int(raw_qid)
            except (TypeError, ValueError):
                unassigned[service_key] += 1
                has_unassigned = True
                continue

            q_key = f"question_{q_num}"
            if q_key in questions:
                questions[q_key][service_key] += 1
            else:
                # questionId is out of the declared range — still track it.
                questions.setdefault(q_key, _empty_service_counts())
                questions[q_key][service_key] += 1

    # Step 3 — Attach the unassigned bucket only if it received any counts.
    if has_unassigned:
        questions["unassigned"] = unassigned

    return {
        "total_questions": total_number_of_questions,
        "questions": questions,
    }


def build_question_report(
    log_path: str,
    total_number_of_questions: int,
    student_id: str,
    exam_id: str,
) -> Dict[str, Any]:
    """Load a JSONL session log and return a complete per-question JSON report.

    The report includes report metadata followed by the question-by-question
    breakdown produced by :func:`count_anomalies_by_question`.

    Args:
        log_path: Absolute path to the session JSONL file.
        total_number_of_questions: Total number of questions in the exam.
        student_id: Student identifier to embed in the report metadata.
        exam_id: Exam identifier to embed in the report metadata.

    Returns:
        A fully populated report dict ready for ``json.dump``.
    """
    events: List[Dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    breakdown = count_anomalies_by_question(events, total_number_of_questions)

    return {
        "report_metadata": {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_log": os.path.basename(log_path),
            "student_id": student_id,
            "exam_id": exam_id,
            "mode": "per_question",
        },
        **breakdown,
    }


def normalise_min_max(counts: Dict[str, int]) -> Dict[str, float]:
    """Min-max normalise raw counts to the (0, 1) range.

    When all counts are identical (including all-zero), normalisation returns
    0.0 for every category — there is no relative difference to highlight.
    """
    values = list(counts.values())
    min_v = min(values)
    max_v = max(values)
    spread = max_v - min_v

    if spread == 0:
        return {cat: 0.0 for cat in counts}

    return {cat: (counts[cat] - min_v) / spread for cat in counts}


def compute_risk_score(
    normalised: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    """Weighted-sum risk formula: Total = Σ (w_i × n_i)."""
    return sum(weights[cat] * normalised[cat] for cat in ALL_CATEGORIES)


def build_report(
    log_path: str,
    student_id: str,
    exam_id: str,
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """Build the full risk-estimation report dict."""
    raw_counts = count_anomalies(log_path)
    normalised = normalise_min_max(raw_counts)
    total_risk = compute_risk_score(normalised, weights)

    return {
        "report_metadata": {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_log": os.path.basename(log_path),
            "student_id": student_id,
            "exam_id": exam_id,
        },
        "raw_counts": raw_counts,
        "normalised_counts": {cat: round(v, 6) for cat, v in normalised.items()},
        "weights": weights,
        "total_risk_score": round(total_risk, 6),
    }


# ─── CLI ────────────────────────────────────────────────────────────────

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Overall Risk Estimation — compute a normalised risk score from a session JSONL log.",
    )
    parser.add_argument(
        "log_file",
        help="Path to the session JSONL log file (e.g. sessions/1009.jsonl).",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output JSON report path. Defaults to <session_id>_risk_report.json next to the log.",
    )
    parser.add_argument("--student-id", default=None, help="Student ID to embed in the report.")
    parser.add_argument("--exam-id", default=None, help="Exam / Question ID to embed in the report.")

    # ── Whole-session weights (default 1.0 each) ─────────────────────────
    parser.add_argument("--wf", type=float, default=1.0, help="Weight for face absence/mismatch (default 1.0).")
    parser.add_argument("--wh", type=float, default=1.0, help="Weight for suspicious movement (default 1.0).")
    parser.add_argument("--wc", type=float, default=1.0, help="Weight for conversation/noise (default 1.0).")
    parser.add_argument("--wb", type=float, default=1.0, help="Weight for forbidden objects (default 1.0).")

    # ── Per-question mode ─────────────────────────────────────────────────
    parser.add_argument(
        "--by-question",
        action="store_true",
        help="Generate a per-question anomaly breakdown instead of a whole-session risk score.",
    )
    parser.add_argument(
        "--total-questions",
        type=int,
        default=None,
        metavar="N",
        help="Total number of questions in the exam. Required when --by-question is set.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    log_path = os.path.abspath(args.log_file)
    if not os.path.isfile(log_path):
        print(f"Error: log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    # Derive student / exam IDs from the filename when not specified
    session_id = os.path.splitext(os.path.basename(log_path))[0]
    student_id = args.student_id or session_id
    exam_id    = args.exam_id    or session_id

    # ── Branch: per-question mode ─────────────────────────────────────────
    if args.by_question:
        if args.total_questions is None:
            print(
                "Error: --total-questions N is required when --by-question is set.",
                file=sys.stderr,
            )
            sys.exit(1)
        if args.total_questions < 1:
            print(
                "Error: --total-questions must be a positive integer.",
                file=sys.stderr,
            )
            sys.exit(1)

        report = build_question_report(
            log_path, args.total_questions, student_id, exam_id
        )

        if args.output:
            out_path = os.path.abspath(args.output)
        else:
            out_dir  = os.path.dirname(log_path)
            out_path = os.path.join(out_dir, f"{session_id}_question_report.json")

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"Question report written to: {out_path}")
        print(json.dumps(report, indent=2))
        return

    # ── Default: whole-session risk score ─────────────────────────────────
    weights = {
        CATEGORY_FACE: args.wf,
        CATEGORY_MOVE: args.wh,
        CATEGORY_CONV: args.wc,
        CATEGORY_OBJ:  args.wb,
    }

    report = build_report(log_path, student_id, exam_id, weights)

    if args.output:
        out_path = os.path.abspath(args.output)
    else:
        out_dir  = os.path.dirname(log_path)
        out_path = os.path.join(out_dir, f"{session_id}_risk_report.json")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Risk report written to: {out_path}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
