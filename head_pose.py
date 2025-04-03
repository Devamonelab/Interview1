import cv2
import dlib
import numpy as np
import math
from collections import deque
import time
import os

# Check if model file exists and handle gracefully
MODEL_PATH = "models/shape_predictor_68_face_landmarks.dat"
if not os.path.exists(MODEL_PATH):
    print(f"WARNING: Head pose detection model file not found at {MODEL_PATH}")
    print(f"Head pose detection will be disabled")
    detector = None
    predictor = None
else:
    # Load face detector & landmarks predictor
    try:
        detector = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor(MODEL_PATH)
        print("Head pose detection initialized successfully")
    except Exception as e:
        print(f"Error loading head pose detection models: {str(e)}")
        detector = None
        predictor = None

# 3D Model Points (Mapped to Facial Landmarks)
model_points = np.array([
    (0.0, 0.0, 0.0),        # Nose tip
    (0.0, -50.0, -10.0),    # Chin
    (-30.0, 40.0, -10.0),   # Left eye
    (30.0, 40.0, -10.0),    # Right eye
    (-25.0, -30.0, -10.0),  # Left mouth corner
    (25.0, -30.0, -10.0)    # Right mouth corner
], dtype=np.float64)

# Camera Calibration (Assuming 640x480)
focal_length = 640
center = (320, 240)
camera_matrix = np.array([
    [focal_length, 0, center[0]],
    [0, focal_length, center[1]],
    [0, 0, 1]
], dtype=np.float64)

dist_coeffs = np.zeros((4, 1))  # Assuming no lens distortion

# Define thresholds and smoothing parameters
CALIBRATION_TIME = 5  # Time to set neutral position

ANGLE_HISTORY_SIZE = 10
yaw_history = deque(maxlen=ANGLE_HISTORY_SIZE)
pitch_history = deque(maxlen=ANGLE_HISTORY_SIZE)
roll_history = deque(maxlen=ANGLE_HISTORY_SIZE)

# Global variables for state management
previous_state = "Looking at Screen"
# calibrated_angles will be set during calibration phase

# ... (existing imports, global variables, and function definitions) ...

def get_head_pose_angles(image_points):
    try:
        success, rotation_vector, translation_vector = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )
        if not success:
            return None

        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        sy = math.sqrt(rotation_matrix[0, 0]**2 + rotation_matrix[1, 0]**2)
        singular = sy < 1e-6

        if not singular:
            pitch = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            yaw = math.atan2(-rotation_matrix[2, 0], sy)
            roll = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
        else:
            pitch = math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
            yaw = math.atan2(-rotation_matrix[2, 0], sy)
            roll = 0

        return np.degrees(pitch), np.degrees(yaw), np.degrees(roll)
    except Exception as e:
        return None

def smooth_angle(angle_history, new_angle):
    angle_history.append(new_angle)
    return np.mean(angle_history)

def process_head_pose(frame, calibrated_angles=None):
    global previous_state

    # Check if models are loaded
    if detector is None or predictor is None:
        # Draw text on frame to indicate head pose detection is disabled
        cv2.putText(frame, "Head Pose Detection Disabled", (10, 60),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame, "Looking at Screen"  # Default to looking at screen as fallback
    
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)
        
        # If no face is detected, return early.
        if len(faces) == 0:
            cv2.putText(frame, "No face detected", (10, 60),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            if calibrated_angles is None:
                return frame, None  # Do not update calibration if no face.
            else:
                return frame, "Looking at Screen"

        head_direction = "Looking at Screen"

        for face in faces:
            try:
                landmarks = predictor(gray, face)
                image_points = np.array([
                    (landmarks.part(30).x, landmarks.part(30).y),  # Nose tip
                    (landmarks.part(8).x, landmarks.part(8).y),    # Chin
                    (landmarks.part(36).x, landmarks.part(36).y),   # Left eye corner
                    (landmarks.part(45).x, landmarks.part(45).y),   # Right eye corner
                    (landmarks.part(48).x, landmarks.part(48).y),   # Left mouth corner
                    (landmarks.part(54).x, landmarks.part(54).y)    # Right mouth corner
                ], dtype=np.float64)

                angles = get_head_pose_angles(image_points)
                if angles is None:
                    continue

                pitch = smooth_angle(pitch_history, angles[0])
                yaw = smooth_angle(yaw_history, angles[1])
                roll = smooth_angle(roll_history, angles[2])

                # If calibrating, return the current angles for calibration.
                if calibrated_angles is None:
                    # Visualize the current angles on frame during calibration
                    cv2.putText(frame, f"Calibrating... P:{pitch:.1f} Y:{yaw:.1f} R:{roll:.1f}", (10, 60),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    return frame, (pitch, yaw, roll)

                pitch_offset, yaw_offset, roll_offset = calibrated_angles
                PITCH_THRESHOLD = 10    
                YAW_THRESHOLD = 15
                ROLL_THRESHOLD = 7

                if (abs(yaw - yaw_offset) <= YAW_THRESHOLD and 
                    abs(pitch - pitch_offset) <= PITCH_THRESHOLD and 
                    abs(roll - roll_offset) <= ROLL_THRESHOLD):
                    current_state = "Looking at Screen"
                elif yaw < yaw_offset - 20:
                    current_state = "Looking Left"
                elif yaw > yaw_offset + 20:
                    current_state = "Looking Right"
                elif pitch > pitch_offset + 15:
                    current_state = "Looking Up"
                elif pitch < pitch_offset - 15:
                    current_state = "Looking Down"
                elif abs(roll - roll_offset) > 10:
                    current_state = "Tilted"
                else:
                    current_state = previous_state

                previous_state = current_state
                head_direction = current_state
                
                # Visualize the current head direction on frame
                cv2.putText(frame, f"Head: {head_direction}", (10, 60),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"P:{pitch-pitch_offset:.1f} Y:{yaw-yaw_offset:.1f} R:{roll-roll_offset:.1f}", 
                          (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Process only one detected face and return.
                return frame, head_direction
            except Exception as landmark_error:
                # Just continue to next face if error with landmarks
                print(f"Error processing landmarks: {str(landmark_error)}")
                continue

        # Fallback in case no valid face was processed.
        return frame, "Looking at Screen"
    
    except Exception as e:
        # On error, return original frame with error text
        cv2.putText(frame, "Head Pose Detection Error", (10, 60),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame, "Looking at Screen"  # Default to looking at screen as fallback

if __name__ == '__main__':
    # This main block will start the webcam and display a window with head pose feedback.
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open webcam")
        exit(1)
        
    calibrated_angles = None
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # During calibration phase (no calibrated_angles yet), try to get calibration data.
        if calibrated_angles is None:
            processed_frame, output = process_head_pose(frame, None)
            # If valid calibration angles are obtained (tuple with 3 values)
            if output is not None and isinstance(output, tuple) and len(output) == 3:
                calibrated_angles = output
                print("Calibration complete:", calibrated_angles)
            else:
                cv2.putText(processed_frame, "Calibrating... keep head straight", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            # Use the calibrated angles to detect head pose.
            processed_frame, head_direction = process_head_pose(frame, calibrated_angles)
            cv2.putText(processed_frame, head_direction, (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow("Head Pose", processed_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()