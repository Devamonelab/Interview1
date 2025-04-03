import cv2
import dlib
import numpy as np
import os

# Check if model file exists and handle gracefully
MODEL_PATH = "models/shape_predictor_68_face_landmarks.dat"
if not os.path.exists(MODEL_PATH):
    print(f"WARNING: Eye movement detection model file not found at {MODEL_PATH}")
    print(f"Eye movement detection will be disabled")
    detector = None
    predictor = None
else:
    # Load dlib's face detector and 68 landmarks model
    try:
        detector = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor(MODEL_PATH)
        print("Eye movement detection initialized successfully")
    except Exception as e:
        print(f"Error loading eye movement detection models: {str(e)}")
        detector = None
        predictor = None

def detect_pupil(eye_region):
    if eye_region is None or eye_region.size == 0:
        return None, None
        
    try:
        gray_eye = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
        blurred_eye = cv2.GaussianBlur(gray_eye, (7, 7), 0)
        _, threshold_eye = cv2.threshold(blurred_eye, 50, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(threshold_eye, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            pupil_contour = max(contours, key=cv2.contourArea)
            px, py, pw, ph = cv2.boundingRect(pupil_contour)
            return (px + pw // 2, py + ph // 2), (px, py, pw, ph)
    except Exception as e:
        pass
    return None, None

def process_eye_movement(frame):
    """
    Processes a single frame to detect eye movement/gaze direction.
    
    Returns:
      frame: The output frame with overlaid markings.
      gaze_direction (str): "Looking Left", "Looking Right", "Looking Up", "Looking Down", or "Looking Center"
    """
    # Check if models are loaded
    if detector is None or predictor is None:
        # Draw text on frame to indicate eye detection is disabled
        cv2.putText(frame, "Eye Movement Detection Disabled", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame, "Looking Center"  # Default to center as fallback
    
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray)

        for face in faces:
            try:
                landmarks = predictor(gray, face)
                
                left_eye_points = np.array([(landmarks.part(n).x, landmarks.part(n).y) for n in range(36, 42)])
                right_eye_points = np.array([(landmarks.part(n).x, landmarks.part(n).y) for n in range(42, 48)])
                
                left_eye_rect = cv2.boundingRect(left_eye_points)
                right_eye_rect = cv2.boundingRect(right_eye_points)
                
                # Make sure the boundaries are within the frame
                left_x1 = max(0, left_eye_rect[0])
                left_y1 = max(0, left_eye_rect[1])
                left_x2 = min(frame.shape[1], left_eye_rect[0] + left_eye_rect[2])
                left_y2 = min(frame.shape[0], left_eye_rect[1] + left_eye_rect[3])
                
                right_x1 = max(0, right_eye_rect[0])
                right_y1 = max(0, right_eye_rect[1])
                right_x2 = min(frame.shape[1], right_eye_rect[0] + right_eye_rect[2])
                right_y2 = min(frame.shape[0], right_eye_rect[1] + right_eye_rect[3])
                
                # Extract eye regions with boundary checking
                if left_x2 > left_x1 and left_y2 > left_y1:
                    left_eye = frame[left_y1:left_y2, left_x1:left_x2]
                else:
                    left_eye = None
                
                if right_x2 > right_x1 and right_y2 > right_y1:
                    right_eye = frame[right_y1:right_y2, right_x1:right_x2]
                else:
                    right_eye = None
                
                left_pupil, left_bbox = detect_pupil(left_eye)
                right_pupil, right_bbox = detect_pupil(right_eye)
                
                # Draw rectangles around eyes
                cv2.rectangle(frame, (left_x1, left_y1), (left_x2, left_y2), (0, 255, 0), 2)
                cv2.rectangle(frame, (right_x1, right_y1), (right_x2, right_y2), (0, 255, 0), 2)
                
                if left_pupil and left_eye is not None:
                    cv2.circle(frame, (left_x1 + left_pupil[0], left_y1 + left_pupil[1]), 5, (0, 0, 255), -1)
                if right_pupil and right_eye is not None:
                    cv2.circle(frame, (right_x1 + right_pupil[0], right_y1 + right_pupil[1]), 5, (0, 0, 255), -1)
                
                if left_pupil and right_pupil and left_eye is not None and right_eye is not None:
                    lx, ly = left_pupil
                    rx, ry = right_pupil
                    
                    eye_width = left_eye_rect[2]
                    eye_height = left_eye_rect[3]
                    norm_ly, norm_ry = ly / eye_height if eye_height > 0 else 0, ry / eye_height if eye_height > 0 else 0
                    
                    if lx < eye_width // 3 and rx < eye_width // 3:
                        gaze_direction = "Looking Left"
                    elif lx > 2 * eye_width // 3 and rx > 2 * eye_width // 3:
                        gaze_direction = "Looking Right"
                    elif norm_ly < 0.3 and norm_ry < 0.3:
                        gaze_direction = "Looking Up"
                    elif norm_ly > 0.5 and norm_ry > 0.5:
                        gaze_direction = "Looking Down"
                    else:
                        gaze_direction = "Looking Center"
            except Exception as landmark_error:
                # Just continue to next face if error with landmarks
                continue
        
        # Draw the gaze direction on the frame
        return frame, gaze_direction
        
    except Exception as e:
        # On error, return original frame with error text
        cv2.putText(frame, "Eye Detection Error", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame, "Looking Center"  # Default to center as fallback

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam!")
        exit()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        processed_frame, gaze_direction = process_eye_movement(frame)
        cv2.putText(processed_frame, gaze_direction, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        cv2.imshow("Eye Tracker", processed_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()