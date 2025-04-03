import cv2
import threading
import numpy as np
import time
import platform
import os

# Log errors to a file for debugging
def log_error(message):
    try:
        with open("camera_error.log", "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except:
        pass  # If logging fails, silently continue

# Threaded video capture class
class VideoStream:
    def __init__(self, src=0):
        # Create a dummy frame as fallback
        self.frame = self._create_dummy_frame()
        self.camera_initialized = False
        self.stopped = False
        
        # Track OS and OpenCV version for debugging
        self.system_info = f"OS: {platform.system()} {platform.release()}, OpenCV: {cv2.__version__}"
        print(f"Initializing camera on {self.system_info}")
        
        # Try Windows-specific initialization first if on Windows
        if platform.system() == 'Windows':
            success = self._try_windows_camera_init()
            if success:
                self.camera_initialized = True
                print("Successfully initialized camera using Windows-specific method")
            else:
                print("Windows-specific camera initialization failed, trying standard methods")
        
        # If not initialized yet, try multiple camera indices
        if not self.camera_initialized:
            # Try to initialize with provided camera index
            success = self._try_camera_init(src)
            
            # If failed, try other common indices (0, 1, 2)
            if not success and src != 0:
                success = self._try_camera_init(0)
            if not success and src != 1:
                success = self._try_camera_init(1)
            if not success and src != 2:
                success = self._try_camera_init(2)
        
        # Start update thread only if camera was initialized
        if self.camera_initialized:
            self.stopped = False
            threading.Thread(target=self.update, daemon=True).start()
        else:
            self.stopped = True
            error_msg = "WARNING: Could not initialize any camera. Using dummy frames."
            print(error_msg)
            log_error(error_msg)
    
    def _try_windows_camera_init(self):
        """Windows-specific camera initialization"""
        try:
            # Windows may need different DirectShow settings
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if self.cap.isOpened():
                # Try to read a frame to confirm it works
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.frame = frame
                    return True
                else:
                    self.cap.release()
            return False
        except Exception as e:
            log_error(f"Windows camera initialization error: {str(e)}")
            return False
    
    def _try_camera_init(self, camera_index):
        """Try to initialize camera with given index"""
        try:
            print(f"Trying to initialize camera with index {camera_index}...")
            self.cap = cv2.VideoCapture(camera_index)
            if self.cap.isOpened():
                # Reduce internal buffer for lower latency
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
                # Set resolution for speed
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                # Read first frame to confirm it works
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.frame = frame
                    self.camera_initialized = True
                    print(f"Successfully initialized camera with index {camera_index}")
                    return True
                else:
                    self.cap.release()
                    log_error(f"Camera {camera_index} opened but couldn't read frame")
            else:
                log_error(f"Failed to open camera {camera_index}")
            return False
        except Exception as e:
            error_msg = f"Error initializing camera with index {camera_index}: {str(e)}"
            print(error_msg)
            log_error(error_msg)
            return False
    
    def _create_dummy_frame(self):
        """Create a blank dummy frame with 'No Camera' text"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Gray background instead of black
        frame[:] = (80, 80, 80)
        
        # Add text and styling
        cv2.putText(frame, "Camera Not Available", (120, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "Interview continues without monitoring", (80, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        cv2.putText(frame, "Please proceed with your answers", (100, 280), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
        
        # Add a border
        cv2.rectangle(frame, (40, 120), (600, 360), (120, 120, 120), 2)
        
        return frame

    def update(self):
        """Update thread that continuously reads frames from the camera"""
        restart_attempts = 0
        max_restart_attempts = 3
        last_restart_time = 0
        
        while not self.stopped:
            if not self.camera_initialized:
                time.sleep(0.1)
                continue
                
            try:
                ret, frame = self.cap.read()
                if ret:
                    self.frame = frame
                    # Reset restart counter after successful reads
                    if restart_attempts > 0 and time.time() - last_restart_time > 10:
                        restart_attempts = 0
                else:
                    print("Warning: Failed to read frame from camera")
                    
                    # Only attempt restart if we haven't reached max attempts
                    current_time = time.time()
                    if restart_attempts < max_restart_attempts and current_time - last_restart_time > 5:
                        restart_attempts += 1
                        last_restart_time = current_time
                        
                        print(f"Attempting to restart camera (attempt {restart_attempts}/{max_restart_attempts})")
                        # If we can't read frame, try to re-open camera
                        self.cap.release()
                        time.sleep(1.0)
                        
                        # Try Windows-specific method first on Windows
                        if platform.system() == 'Windows':
                            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                        else:
                            self.cap = cv2.VideoCapture(0)
                            
                        if not self.cap.isOpened():
                            # If reopening fails, switch to dummy frames
                            error_msg = "Failed to reopen camera - using dummy frames"
                            print(error_msg)
                            log_error(error_msg)
                            self.camera_initialized = False
                            self.frame = self._create_dummy_frame()
                    elif restart_attempts >= max_restart_attempts:
                        # We've reached max restart attempts, use dummy frame
                        error_msg = f"Exceeded maximum camera restart attempts ({max_restart_attempts})"
                        print(error_msg)
                        log_error(error_msg)
                        self.camera_initialized = False
                        self.frame = self._create_dummy_frame()
            except Exception as e:
                error_msg = f"Error in video capture: {str(e)}"
                print(error_msg)
                log_error(error_msg)
                self.camera_initialized = False
                self.frame = self._create_dummy_frame()
                
            # Small sleep to prevent excessive CPU usage
            time.sleep(0.03)  

    def read(self):
        """Return the current frame"""
        return self.frame

    def stop(self):
        """Stop the video capture thread"""
        self.stopped = True
        if hasattr(self, 'cap') and self.camera_initialized:
            self.cap.release() 