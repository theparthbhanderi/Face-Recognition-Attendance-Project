import threading
import time
from face_recognition_manager import FaceRecognitionManager

try:
    import cv2
    import face_recognition
    import numpy as np
    CV2_AVAILABLE = True
except Exception as _err:
    CV2_AVAILABLE = False
    print(f"Warning: camera dependencies not available ({_err}). Camera endpoints will be disabled.")

class Camera:
    def __init__(self, device_index=0):
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV or face_recognition not available")

        # Initialize camera with DSHOW backend for Windows
        # Allow passing a device index so callers can switch cameras
        self.device_index = int(device_index)
        self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            raise Exception("Failed to open camera")

        # Set optimal camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        # Some backends may not support these properties; ignore failures
        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        except Exception:
            pass

        # Frame storage
        self.frame = None
        self.processed_frame = None
        self.face_locations = []
        self.face_names = []
        self.lock = threading.Lock()
        self.running = True

        # Initialize face recognition manager
        self.face_manager = FaceRecognitionManager()

        # Face recognition timing
        self.last_recognition_time = 0
        self.recognition_interval = 1.0  # Process every 1 second
        self.frame_count = 0

        print("Camera initialized successfully")

        # Start camera thread
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        print("Camera thread started")
    
    def update(self):
        """Continuously capture frames in separate thread"""
        consecutive_failures = 0
        max_failures = 10
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.lock:
                        self.frame = frame.copy()
                        self.frame_count += 1
                    
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Process face recognition on intervals
                    current_time = time.time()
                    if current_time - self.last_recognition_time > self.recognition_interval:
                        try:
                            self._process_face_recognition(frame)
                            self.last_recognition_time = current_time
                        except Exception as e:
                            print(f"Face recognition error: {e}")
                else:
                    consecutive_failures += 1
                    print(f"Failed to read frame (attempt {consecutive_failures}/{max_failures})")
                    
                    if consecutive_failures >= max_failures:
                        print("Too many consecutive failures, reinitializing camera...")
                        try:
                            self.cap.release()
                            time.sleep(1)
                            # Re-open using the configured device_index
                            self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
                            if self.cap.isOpened():
                                # Reset camera properties
                                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                self.cap.set(cv2.CAP_PROP_FPS, 30)
                                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                                consecutive_failures = 0
                                print("Camera reinitialized successfully")
                            else:
                                print("Failed to reinitialize camera")
                        except Exception as e:
                            print(f"Error reinitializing camera: {e}")
                    
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Camera thread error: {e}")
                consecutive_failures += 1
                time.sleep(0.1)
    
    def _process_face_recognition(self, frame):
        """Process face recognition on frame"""
        try:
            # Resize for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Use manager for recognition
            results = self.face_manager.recognize_faces_in_frame(frame)
            
            face_names = []
            face_locations = []
            
            for result in results:
                face_names.append(result['name'])
                face_locations.append(result['location'])
            
            # Locations are already scaled by the manager
            
            # Create processed frame with annotations
            processed_frame = frame.copy()
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                # Draw green rectangle around face
                cv2.rectangle(processed_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Draw label background
                cv2.rectangle(processed_frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
                
                # Draw name
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(processed_frame, name, (left + 6, bottom - 6), font, 0.5, (0, 0, 0), 1)
            
            # Store results
            with self.lock:
                self.face_locations = face_locations.tolist() if isinstance(face_locations, np.ndarray) else face_locations
                self.face_names = face_names
                self.processed_frame = processed_frame
                
        except Exception as e:
            print(f"Error in face recognition: {e}")
    
    def get_frame(self):
        """Get latest processed frame with face boxes"""
        try:
            with self.lock:
                if self.processed_frame is not None:
                    frame = self.processed_frame.copy()
                    # Check if frame is black
                    if frame.max() == 0:
                        # Return raw frame if processed is black
                        if self.frame is not None:
                            return self.frame.copy()
                        else:
                            return frame
                    else:
                        return frame
                elif self.frame is not None:
                    frame = self.frame.copy()
                    # Check if raw frame is black
                    if frame.max() == 0:
                        # Create a test pattern if black
                        frame[:] = 50  # Gray color
                        cv2.putText(frame, 'Camera Initializing...', (100, 240), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    return frame
                else:
                    # Create a test frame if no frame available
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    frame[:] = 30  # Dark gray
                    cv2.putText(frame, 'No Camera Signal', (100, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    return frame
        except Exception as e:
            print(f"Error getting frame: {e}")
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = 20  # Very dark gray
            cv2.putText(frame, 'Camera Error', (150, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            return frame
    
    def get_raw_frame(self):
        """Get raw frame without processing"""
        try:
            with self.lock:
                if self.frame is not None:
                    return self.frame.copy()
                else:
                    return None
        except Exception as e:
            print(f"Error getting raw frame: {e}")
            return None
    
    def get_recognition_data(self):
        """Get current recognition data"""
        try:
            with self.lock:
                return {
                    'face_locations': self.face_locations.copy(),
                    'face_names': self.face_names.copy(),
                    'frame_count': self.frame_count
                }
        except Exception as e:
            print(f"Error getting recognition data: {e}")
            return {'face_locations': [], 'face_names': [], 'frame_count': 0}
    
    def release(self):
        """Release camera resources"""
        print("Releasing camera...")
        self.running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        print("Camera released")

# Global camera instance
if CV2_AVAILABLE:
    try:
        camera = Camera()
        print("Camera created successfully")
    except Exception as e:
        print(f"Failed to create camera: {e}")
        camera = None
else:
    # Provide a minimal dummy camera implementation so the server stays up
    class DummyCamera:
        def __init__(self):
            self.device_index = None

        def get_frame(self):
            return None

        def get_raw_frame(self):
            return None

        def get_recognition_data(self):
            return {'face_locations': [], 'face_names': [], 'frame_count': 0}

        def release(self):
            pass

    camera = DummyCamera()
