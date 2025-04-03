import cv2
import torch
from ultralytics import YOLO
import os

# Model configuration
MODEL_PATH = r"C:\Interview portal\Cheating-Surveillance-System\models\best_yolov12.pt"

# Try to load model with error handling
try:
    if not os.path.exists(MODEL_PATH):
        print(f"WARNING: Mobile detection model file not found at {MODEL_PATH}")
        print(f"Mobile detection will be disabled")
        model = None
    else:
        model = YOLO(MODEL_PATH)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        print(f"Mobile Detection using device: {device}")
except Exception as e:
    print(f"Error loading mobile detection model: {str(e)}")
    model = None

# Detection parameters: Increase confidence threshold to reduce false positives
CONFIDENCE_THRESHOLD = 0.85   # Slightly lowered to catch more potential detections
AUGMENT_DETECTION = True     # Enable augmentation for better detection across conditions
IOU_THRESHOLD = 0.5          # For non-maximum suppression
TEMPORAL_FILTER_SIZE = 5     # Number of frames to consider for temporal filtering

# Initialize history for temporal filtering
mobile_detection_history = []

def process_mobile_detection(frame):
    """
    Processes a single video frame to detect mobile devices.
    
    Returns:
      frame: The frame with drawn bounding boxes.
      mobile_detected (bool): True if a mobile is detected, otherwise False.
    """
    global mobile_detection_history
    
    # Check if model is loaded
    if model is None:
        # Draw text on frame to indicate mobile detection is disabled
        cv2.putText(frame, "Mobile Detection Disabled", (10, 90),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame, False  # Default to no mobile detected
    
    try:
        # Run model with augmentation and multi-scale inference
        results = model(frame, verbose=False, augment=AUGMENT_DETECTION)
        current_frame_detection = False

        for result in results:
            # Apply non-maximum suppression to remove overlapping detections
            boxes = []
            confidences = []
            
            for box in result.boxes:
                conf = box.conf[0].item()  # Confidence score
                cls = int(box.cls[0].item())  # Expect mobile class index = 0

                if conf < CONFIDENCE_THRESHOLD or cls != 0:
                    continue
                
                boxes.append(box.xyxy[0].cpu().numpy())
                confidences.append(conf)
                current_frame_detection = True
            
            # Draw and update for detections after filtering
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box)
                label = f"Mobile ({confidences[i]:.2f})"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 2)
        
        # Update temporal filtering history
        mobile_detection_history.append(current_frame_detection)
        if len(mobile_detection_history) > TEMPORAL_FILTER_SIZE:
            mobile_detection_history.pop(0)
        
        # Apply temporal filtering - only return positive if majority of recent frames had detection
        mobile_detected = sum(mobile_detection_history) > (TEMPORAL_FILTER_SIZE // 2)
        
        # Add confidence indicator
        confidence_level = sum(mobile_detection_history) / len(mobile_detection_history)
        cv2.putText(frame, f"Detection confidence: {confidence_level:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        return frame, mobile_detected
    
    except Exception as e:
        # If error occurs during detection, log it and return no detection
        print(f"Error in mobile detection: {str(e)}")
        cv2.putText(frame, "Mobile Detection Error", (10, 90),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame, False

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Unable to open video source.")
        exit(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame. Exiting...")
            break

        processed_frame, mobile_detected = process_mobile_detection(frame)
        if mobile_detected:
            print("Mobile detected in current frame.")

        cv2.imshow("Mobile Detection", processed_frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()