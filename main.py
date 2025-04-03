import cv2
import time
import os
from eye_movement import process_eye_movement
from head_pose import process_head_pose
from mobile_detection import process_mobile_detection
import threading
from concurrent.futures import ThreadPoolExecutor

# Threaded video capture class
class VideoStream:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        # Reduce internal buffer for lower latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        # Set resolution for speed
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.ret, self.frame = self.cap.read()
        self.stopped = False
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
            else:
                self.stop()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.cap.release()

# Initialize threaded video capture
vs = VideoStream(src=0)

# Create a log directory for screenshots
log_dir = "log"
os.makedirs(log_dir, exist_ok=True)

# Calibration for head pose
calibrated_angles = None
start_time = time.time()

# Timers for misalignment events (for taking snapshots)
head_misalignment_start_time = None
eye_misalignment_start_time = None
mobile_detection_start_time = None

# Initialize detection results
head_direction = "Looking at Screen"

# Metrics counters
mobile_detection_counter = 0
head_pose_counter = {"Looking Left": 0, "Looking Right": 0, "Looking Up": 0, "Looking Down": 0, "Tilted": 0}
eye_movement_counter = {"Looking Left": 0, "Looking Right": 0, "Looking Up": 0, "Looking Down": 0}

previous_head_direction = "Looking at Screen"
previous_gaze_direction = "Looking Center"

# Create a ThreadPoolExecutor for concurrent processing
executor = ThreadPoolExecutor(max_workers=3)

try:
    while True:
        frame = vs.read()
        if frame is None:
            continue

        # Duplicate frames for independent processing
        frame_eye = frame.copy()
        frame_head = frame.copy()
        frame_mobile = frame.copy()

        # Submit detection tasks concurrently
        future_eye = executor.submit(process_eye_movement, frame_eye)
        if time.time() - start_time <= 5:  # Calibration period for head pose
            future_head = executor.submit(process_head_pose, frame_head, None)
        else:
            future_head = executor.submit(process_head_pose, frame_head, calibrated_angles)
        future_mobile = executor.submit(process_mobile_detection, frame_mobile)

        # Retrieve results from tasks
        _, gaze_direction = future_eye.result()
        _, head_direction = future_head.result()
        _, mobile_detected = future_mobile.result()

        # During calibration, set the calibrated head pose values once
        # During calibration, update the calibration data only if valid.
        if calibrated_angles is None and time.time() - start_time > 5:
            _, cal_data = process_head_pose(frame.copy(), None)
            if cal_data is not None and isinstance(cal_data, tuple) and len(cal_data) == 3:
                calibrated_angles = cal_data

        # Update metrics counters
        if mobile_detected:
            mobile_detection_counter += 1

        if head_direction != "Looking at Screen" and previous_head_direction == "Looking at Screen":
            if head_direction in head_pose_counter:
                head_pose_counter[head_direction] += 1
        previous_head_direction = head_direction

        if gaze_direction != "Looking Center" and previous_gaze_direction == "Looking Center":
            if gaze_direction in eye_movement_counter:
                eye_movement_counter[gaze_direction] += 1
        previous_gaze_direction = gaze_direction

        # Use the mobile processed frame for display (has drawn boxes, etc.)
        display_frame = frame_mobile.copy()

        # Overlay detection results
        cv2.putText(display_frame, f"Gaze Direction: {gaze_direction}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if time.time() - start_time > 5:
            cv2.putText(display_frame, f"Head Direction: {head_direction}", (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(display_frame, "Calibrating... Keep your head straight", (50, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(display_frame, f"Mobile Detected: {mobile_detected}", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Overlay metrics counters
        cv2.putText(display_frame, f"Mobile Detections: {mobile_detection_counter}", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 200, 50), 2)

        cv2.putText(display_frame, "Head Pose Events:", (20, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 200, 50), 2)
        head_y = 180
        for direction, count in head_pose_counter.items():
            cv2.putText(display_frame, f"{direction}: {count}", (20, head_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 200, 50), 2)
            head_y += 30

        cv2.putText(display_frame, "Eye Movement Events:", (320, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 200, 50), 2)
        eye_y = 180
        for direction, count in eye_movement_counter.items():
            cv2.putText(display_frame, f"{direction}: {count}", (320, eye_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 200, 50), 2)
            eye_y += 30

        # Check for head misalignment and save screenshot if misaligned for 3+ seconds
        if head_direction != "Looking at Screen":
            if head_misalignment_start_time is None:
                head_misalignment_start_time = time.time()
            elif time.time() - head_misalignment_start_time >= 3:
                filename = os.path.join(log_dir, f"head_{head_direction}_{int(time.time())}.png")
                cv2.imwrite(filename, display_frame)
                print(f"Screenshot saved: {filename}")
                head_misalignment_start_time = None
        else:
            head_misalignment_start_time = None

        # Check for eye misalignment and save screenshot if misaligned for 3+ seconds
        if gaze_direction != "Looking Center":
            if eye_misalignment_start_time is None:
                eye_misalignment_start_time = time.time()
            elif time.time() - eye_misalignment_start_time >= 3:
                filename = os.path.join(log_dir, f"eye_{gaze_direction}_{int(time.time())}.png")
                cv2.imwrite(filename, display_frame)
                print(f"Screenshot saved: {filename}")
                eye_misalignment_start_time = None
        else:
            eye_misalignment_start_time = None

        # Check for mobile detection and save screenshot if detected for 3+ seconds
        if mobile_detected:
            if mobile_detection_start_time is None:
                mobile_detection_start_time = time.time()
            elif time.time() - mobile_detection_start_time >= 3:
                filename = os.path.join(log_dir, f"mobile_detected_{int(time.time())}.png")
                cv2.imwrite(filename, display_frame)
                print(f"Screenshot saved: {filename}")
                mobile_detection_start_time = None
        else:
            mobile_detection_start_time = None

        cv2.imshow("Combined Detection", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    vs.stop()
    executor.shutdown()
    cv2.destroyAllWindows()
    
    # Print final metrics to terminal
    print("\nFinal Metrics:")
    print(f"Mobile Detections: {mobile_detection_counter}")
    print("Head Pose Events:")
    for direction, count in head_pose_counter.items():
        print(f"  {direction}: {count}")
    print("Eye Movement Events:")
    for direction, count in eye_movement_counter.items():
        print(f"  {direction}: {count}")