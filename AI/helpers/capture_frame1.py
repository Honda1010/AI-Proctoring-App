import argparse
import base64
import requests
import time
import cv2
import threading
from collections import deque

parser = argparse.ArgumentParser()
parser.add_argument("--batch",   type=int, default=30)
parser.add_argument("--session", type=str, default="test_user_001")
parser.add_argument("--fps",     type=int, default=10)
parser.add_argument("--url",     type=str, default="http://localhost:8000/analysis/gaze-frames")
args = parser.parse_args()

frame_queue = deque(maxlen=args.batch * 2)
queue_lock  = threading.Lock()
stop_flag   = threading.Event()

def capture_thread():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        stop_flag.set()
        return

    print(f"Capturing at {args.fps}fps in batches of {args.batch} frames.")
    print("Press Q to stop.\n")

    while not stop_flag.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (320, 240))
        cv2.imshow("Capturing - press Q to stop", frame)

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        b64    = base64.b64encode(buf).decode("utf-8")

        with queue_lock:
            frame_queue.append(b64)

        time.sleep(1 / args.fps)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            stop_flag.set()
            break

    cap.release()
    cv2.destroyAllWindows()

def send_thread():
    batch_count = 0

    while not stop_flag.is_set():

        with queue_lock:
            current_size = len(frame_queue)

        if current_size < args.batch:
            time.sleep(0.05)
            continue

        with queue_lock:
            batch = [frame_queue.popleft() for _ in range(args.batch)]

        batch_count += 1

        # --- timing starts here
        capture_time   = args.batch / args.fps
        send_start     = time.time()

        print(f"Batch {batch_count}:")
        print(f"  frames collected : {args.batch}")
        print(f"  capture duration : {capture_time:.2f}s")
        print(f"  queue size before send: {current_size - args.batch}")

        try:
            response = requests.post(
                args.url,
                json={"session_id": args.session, "frames": batch},
                timeout=30,
            )
            send_end        = time.time()
            send_duration   = send_end - send_start
            total_duration  = capture_time + send_duration

            data = response.json()

            print(f"  send + process   : {send_duration:.2f}s")
            print(f"  total time       : {total_duration:.2f}s")
            print(f"  frames in queue  : {len(frame_queue)}")
            print(f"  summary_flag     : {data['summary_flag']}")

            for v in data["verdicts"]:
                marker = "⚠️" if v["flag"] in ("AWAY_SHORT", "AWAY_LONG", "NO_FACE") else "✅"
                print(f"  {marker} {v['flag']}  prob={v['probability']}")

        except Exception as e:
            print(f"  ERROR: {e}")

        print()

t_capture = threading.Thread(target=capture_thread, daemon=True)
t_send    = threading.Thread(target=send_thread,    daemon=True)

t_capture.start()
t_send.start()

t_capture.join()
t_send.join()

try:
    requests.delete(f"http://localhost:8000/analysis/gaze-frames/{args.session}")
    print("Session cleared.")
except Exception:
    pass